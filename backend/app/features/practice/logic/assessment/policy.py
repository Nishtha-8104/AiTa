"""The Assessment Agent's policy. Deterministic, explained back to the student in one
line, and it never serves an answer key: payloads are built field by field."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.exceptions import LLMUnavailable, PetError
from app.core.topics import PREREQUISITES, TOPIC_LABELS, TOPICS
from app.features.grading.models import CodeEvaluation, CodeSubmission
from app.features.learner_model.logic.mastery import (
    MASTERED_FROM,
    MISS_BELOW,
    PRIOR,
    SEED_KINDS,
    WEAK_BELOW,
)
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.learner_model.service import current_language
from app.features.practice.logic.assessment.verify import CONCEPT
from app.features.practice.models import (
    DebugAttempt,
    DebugChallenge,
    McqAttempt,
    McqQuestion,
)
from app.features.problems.logic.generation import generate_problem
from app.features.problems.logic.listing import CURATED_SOURCES, to_summary
from app.features.problems.models import Difficulty, Problem

DIFFICULTY_ORDER = ("easy", "medium", "hard")
TYPE_LABELS = {"mcq": "multiple-choice question", "diagnostic": "diagnostic question",
               "coding": "coding problem", "debug": "debugging challenge"}


class NothingToServe(PetError):
    status_code = 503


@dataclass
class TopicState:
    topic: str
    mastery: float
    evidence: int
    last_event_at: object = None


@dataclass
class Plan:
    user_id: int
    language: str = "c"
    topics: dict[str, TopicState] = field(default_factory=dict)
    topic: str | None = None
    item_type: str | None = None
    difficulty: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class NextItem:
    item_type: str
    topic: str
    difficulty: str
    item: dict
    reason: str


def load_profile(db: Session, user_id: int) -> Plan:
    language = current_language(db, user_id)
    rows = {r.topic: r for r in db.query(TopicMastery)
            .filter(TopicMastery.user_id == user_id, TopicMastery.language == language)}
    plan = Plan(user_id=user_id, language=language)
    for topic in TOPICS:
        row = rows.get(topic)
        plan.topics[topic] = TopicState(topic, row.mastery if row else PRIOR,
                                        row.evidence_count if row else 0,
                                        row.last_event_at if row else None)
    return plan


def unlocked(plan: Plan, topic: str) -> bool:
    return all(plan.topics[p].mastery >= WEAK_BELOW for p in PREREQUISITES[topic])


def ranked_topics(plan: Plan) -> list[str]:
    """Lowest mastery among unlocked topics; ties go to the least recently practised,
    then to curriculum order."""
    open_topics = [t for t in TOPICS if unlocked(plan, t)]
    order = {t: i for i, t in enumerate(TOPICS)}

    def key(topic):
        state = plan.topics[topic]
        recency = state.last_event_at.timestamp() if state.last_event_at else float("-inf")
        return (round(state.mastery, 6), recency, order[topic])

    return sorted(open_topics, key=key)


STUCK_AFTER = 3


def stuck_topic(db: Session, user_id: int) -> str | None:
    """The topic of the last STUCK_AFTER events when every one of them was a miss.
    Serving it again would only dig the hole deeper; one item elsewhere breaks the run."""
    recent = (db.query(LearningEvent.topic, LearningEvent.score)
              .filter(LearningEvent.user_id == user_id, LearningEvent.kind.notin_(SEED_KINDS),
                      LearningEvent.language == current_language(db, user_id))
              .order_by(LearningEvent.id.desc()).limit(STUCK_AFTER).all())
    if len(recent) < STUCK_AFTER:
        return None
    topics = {topic for topic, _ in recent}
    if len(topics) == 1 and None not in topics and all(s < MISS_BELOW for _, s in recent):
        return topics.pop()
    return None


def choose_type(db: Session, plan: Plan, topic: str) -> str:
    mastery = plan.topics[topic].mastery
    if mastery < WEAK_BELOW:
        return "mcq"
    if mastery < MASTERED_FROM:
        last = (db.query(LearningEvent.kind)
                .filter(LearningEvent.user_id == plan.user_id, LearningEvent.topic == topic,
                        LearningEvent.language == plan.language,
                        LearningEvent.kind.in_(("code", "debug")))
                .order_by(LearningEvent.id.desc()).first())
        return "debug" if last and last[0] == "code" else "coding"
    return "coding"


def choose_difficulty(mastery: float) -> str:
    if mastery < WEAK_BELOW:
        return "easy"
    if mastery < MASTERED_FROM:
        return "medium"
    return "hard"


def difficulty_steps(difficulty: str) -> list[str]:
    """The requested level, then one step easier, then anything."""
    index = DIFFICULTY_ORDER.index(difficulty)
    ordered = [difficulty]
    if index > 0:
        ordered.append(DIFFICULTY_ORDER[index - 1])
    ordered += [d for d in DIFFICULTY_ORDER if d not in ordered]
    return ordered


def mcq_payload(q: McqQuestion) -> dict:
    return {"id": q.id, "stem": q.stem, "options": [o["text"] for o in q.options],
            "topic": q.topic, "difficulty": q.difficulty, "language": q.language,
            "is_diagnostic": q.is_diagnostic}


def debug_payload(c: DebugChallenge) -> dict:
    return {"id": c.id, "statement": c.statement, "language": c.language,
            "buggy_code": c.buggy_code, "topic": c.topic, "difficulty": c.difficulty}


def coding_payload(problem: Problem) -> dict:
    return to_summary(problem).model_dump()


def _pick_mcq(db, user_id, topic, difficulty, language):
    solved = {qid for (qid,) in db.query(McqAttempt.question_id)
              .filter(McqAttempt.user_id == user_id, McqAttempt.correct.is_(True))}
    tried = {qid for (qid,) in db.query(McqAttempt.question_id)
             .filter(McqAttempt.user_id == user_id)}
    for level in difficulty_steps(difficulty):
        pool = [q for q in db.query(McqQuestion)
                .filter(McqQuestion.topic == topic, McqQuestion.difficulty == level,
                        McqQuestion.language.in_((language, CONCEPT)),
                        McqQuestion.reviewed.is_(True), McqQuestion.is_diagnostic.is_(False))
                .order_by(McqQuestion.id)
                if q.id not in solved]
        if pool:
            fresh = [q for q in pool if q.id not in tried]
            return (fresh or pool)[0], level
    return None, None


def _pick_debug(db, user_id, topic, difficulty, language):
    fixed = {cid for (cid,) in db.query(DebugAttempt.challenge_id)
             .filter(DebugAttempt.user_id == user_id, DebugAttempt.fixed.is_(True))}
    for level in difficulty_steps(difficulty):
        pool = [c for c in db.query(DebugChallenge)
                .filter(DebugChallenge.topic == topic, DebugChallenge.difficulty == level,
                        DebugChallenge.language == language,
                        DebugChallenge.reviewed.is_(True))
                .order_by(DebugChallenge.id)
                if c.id not in fixed]
        if pool:
            return pool[0], level
    return None, None


def _passed_problem_ids(db, user_id) -> set[int]:
    rows = (db.query(CodeSubmission.problem_id)
            .join(CodeEvaluation, CodeEvaluation.submission_id == CodeSubmission.id)
            .filter(CodeEvaluation.user_id == user_id, CodeEvaluation.tests_total > 0,
                    CodeEvaluation.tests_passed == CodeEvaluation.tests_total))
    return {pid for (pid,) in rows if pid is not None}


def pick_coding(db, user_id, topic, difficulty):
    passed = _passed_problem_ids(db, user_id)
    for level in difficulty_steps(difficulty)[:2]:
        problem = (db.query(Problem)
                   .filter(Problem.source.in_(CURATED_SOURCES), Problem.topic == topic,
                           Problem.difficulty == Difficulty(level), Problem.test_cases.any(),
                           Problem.id.notin_(passed or {-1}))
                   .order_by(Problem.id).first())
        if problem is not None:
            return problem, level
    return None, None


def generate_coding(db, topic, difficulty):
    try:
        generated = generate_problem(db, TOPIC_LABELS[topic], difficulty)
    except LLMUnavailable:
        return None, None
    if generated.ungradeable_reason:
        return None, None
    level = getattr(generated.problem.difficulty, "value", difficulty)
    return generated.problem, level


_FALLBACKS = {"mcq": ("mcq", "debug", "coding"), "debug": ("debug", "coding", "mcq"),
              "coding": ("coding", "debug", "mcq")}


def pick_item(db: Session, plan: Plan) -> NextItem | None:
    for item_type in _FALLBACKS[plan.item_type]:
        if item_type == "mcq":
            found, level = _pick_mcq(db, plan.user_id, plan.topic, plan.difficulty,
                                     plan.language)
            payload = mcq_payload if found else None
        elif item_type == "debug":
            found, level = _pick_debug(db, plan.user_id, plan.topic, plan.difficulty,
                                       plan.language)
            payload = debug_payload if found else None
        else:
            found, level = pick_coding(db, plan.user_id, plan.topic, plan.difficulty)
            if found is None:
                found, level = generate_coding(db, plan.topic, plan.difficulty)
                if found is not None:
                    plan.notes.append("none of the saved problems fitted, so a new one was generated")
            payload = coding_payload if found else None
        if found is None:
            continue
        if item_type != plan.item_type:
            plan.notes.append(f"no {TYPE_LABELS[plan.item_type]} was left")
        if level != plan.difficulty:
            plan.notes.append(f"no {plan.difficulty} one was left")
        return NextItem(item_type, plan.topic, level, payload(found),
                        _reason(plan, item_type, level))
    return None


def _reason(plan: Plan, item_type: str, difficulty: str) -> str:
    state = plan.topics[plan.topic]
    label = TOPIC_LABELS[plan.topic]
    if state.evidence == 0:
        why = f"{label} is the next open topic you haven't practised yet"
    else:
        answers = "graded answer" if state.evidence == 1 else "graded answers"
        why = (f"{label} is your weakest open topic "
               f"(topic level {round(state.mastery * 100)}% after {state.evidence} {answers})")
    article = "an" if difficulty[0] in "aeiou" else "a"
    reason = f"{why}, so here is {article} {difficulty} {TYPE_LABELS[item_type]}"
    if plan.notes:
        reason += f" ({'; '.join(plan.notes)})"
    return reason + "."


def start_topic(db: Session, user_id: int) -> str:
    """The topic Practice opens with, from the same ranking, without picking an item."""
    return ranked_topics(load_profile(db, user_id))[0]
