"""Topic practice: a written explanation, then a fixed run of items on one topic the
student chose. A run is a practice session with a plan of item types; which item fills
each slot is decided when the slot is reached, unseen items first."""

import random
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core import content
from app.core.exceptions import PetError, SessionNotFound
from app.core.topics import TOPIC_LABELS, TOPICS
from app.features.learner_model.logic.mastery import PRIOR
from app.features.learner_model.models import TopicMastery
from app.features.learner_model.service import current_language
from app.features.practice import service as lifecycle
from app.features.practice.logic.assessment.policy import (
    choose_difficulty,
    coding_payload,
    debug_payload,
    difficulty_steps,
    generate_coding,
    mcq_payload,
    pick_coding,
)
from app.features.practice.logic.assessment.verify import CONCEPT
from app.features.practice.models import (
    DebugAttempt,
    DebugChallenge,
    McqAttempt,
    McqQuestion,
    PracticeSession,
    TheoryAttempt,
    TheoryQuestion,
)
from app.features.problems.models import Problem

PER_TYPE = 3
NON_CODING = ("theory", "mcq", "debug")
FALLBACKS = {"theory": ("theory", "mcq", "debug"), "mcq": ("mcq", "theory", "debug"),
             "debug": ("debug", "mcq", "theory"), "coding": ("coding", "debug", "mcq", "theory")}
NEW, WRONG, RIGHT = 0, 1, 2


class UnknownTopic(PetError):
    status_code = 404


@dataclass
class Explanation:
    topic: str
    language: str
    markdown: str


@dataclass
class RunStep:
    session_id: int
    position: int
    total: int
    done: bool
    item_type: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    item: dict | None = None


def _topic(topic: str) -> str:
    if topic not in TOPICS:
        raise UnknownTopic(f"Unknown topic: {topic}")
    return topic


@lru_cache(maxsize=64)
def _read(language: str, topic: str) -> str | None:
    if not content.topic_path(topic, "explanation").exists():
        return None
    for item in content.items(topic, "explanation"):
        if item["language"] == language:
            return content.text([f"# {item['title']}", *item["markdown"]])
    return None


def explanation(db: Session, user_id: int, topic: str) -> Explanation:
    language = current_language(db, user_id)
    markdown = _read(language, _topic(topic))
    if markdown is None:
        raise UnknownTopic(f"No explanation of {TOPIC_LABELS[topic]} is written yet.")
    return Explanation(topic, language, markdown)


def make_plan(rng: random.Random) -> list[str]:
    """PER_TYPE of each non-coding type, shuffled, and one coding problem anywhere but first."""
    rest = [t for t in NON_CODING for _ in range(PER_TYPE)]
    rng.shuffle(rest)
    at = rng.randint(1, len(rest))
    return rest[:at] + ["coding"] + rest[at:]


def start(db: Session, user_id: int, topic: str, now: datetime,
          rng: random.Random | None = None) -> PracticeSession:
    return lifecycle.start_run(db, user_id, _topic(topic), current_language(db, user_id),
                               make_plan(rng or random.Random()), now)


def theory_payload(q: TheoryQuestion) -> dict:
    return {"id": q.id, "question": q.question, "topic": q.topic,
            "difficulty": q.difficulty, "language": q.language}


def _difficulty(db: Session, user_id: int, topic: str, language: str) -> str:
    row = db.get(TopicMastery, (user_id, topic, language))
    return choose_difficulty(row.mastery if row else PRIOR)


def _status(item_id: int, tried: set[int], right: set[int]) -> int:
    if item_id not in tried:
        return NEW
    return RIGHT if item_id in right else WRONG


def _choose(rows, tried, right, difficulty, exclude):
    """Unseen first, then ones answered wrong, then the rest; within each, the target
    difficulty, then one step easier, then anything."""
    for rank in (NEW, WRONG, RIGHT):
        for level in difficulty_steps(difficulty):
            for row in rows:
                if (row.difficulty == level and row.id not in exclude
                        and _status(row.id, tried, right) == rank):
                    return row
    return None


def _ids(db, column, *criteria) -> set[int]:
    return {i for (i,) in db.query(column).filter(*criteria)}


def _pick(db: Session, user_id: int, s: PracticeSession, item_type: str,
          difficulty: str) -> tuple[object, dict] | None:
    exclude = {e["id"] for e in s.served if e["type"] == item_type}
    if item_type == "mcq":
        rows = (db.query(McqQuestion)
                .filter(McqQuestion.topic == s.topic, McqQuestion.reviewed.is_(True),
                        McqQuestion.is_diagnostic.is_(False),
                        McqQuestion.language.in_((s.language, CONCEPT)))
                .order_by(McqQuestion.id).all())
        tried = _ids(db, McqAttempt.question_id, McqAttempt.user_id == user_id)
        right = _ids(db, McqAttempt.question_id, McqAttempt.user_id == user_id,
                     McqAttempt.correct.is_(True))
        found = _choose(rows, tried, right, difficulty, exclude)
        return (found, mcq_payload(found)) if found else None
    if item_type == "debug":
        rows = (db.query(DebugChallenge)
                .filter(DebugChallenge.topic == s.topic, DebugChallenge.reviewed.is_(True),
                        DebugChallenge.language == s.language)
                .order_by(DebugChallenge.id).all())
        tried = _ids(db, DebugAttempt.challenge_id, DebugAttempt.user_id == user_id)
        right = _ids(db, DebugAttempt.challenge_id, DebugAttempt.user_id == user_id,
                     DebugAttempt.fixed.is_(True))
        found = _choose(rows, tried, right, difficulty, exclude)
        return (found, debug_payload(found)) if found else None
    if item_type == "theory":
        rows = (db.query(TheoryQuestion)
                .filter(TheoryQuestion.topic == s.topic, TheoryQuestion.reviewed.is_(True),
                        TheoryQuestion.language == s.language)
                .order_by(TheoryQuestion.id).all())
        tried = _ids(db, TheoryAttempt.question_id, TheoryAttempt.user_id == user_id)
        right = _ids(db, TheoryAttempt.question_id, TheoryAttempt.user_id == user_id,
                     TheoryAttempt.score >= 1.0)
        found = _choose(rows, tried, right, difficulty, exclude)
        return (found, theory_payload(found)) if found else None
    found, _ = pick_coding(db, user_id, s.topic, difficulty)
    if found is None:
        found, _ = generate_coding(db, s.topic, difficulty)
    return (found, coding_payload(found)) if found else None


_MODELS = {"mcq": McqQuestion, "debug": DebugChallenge, "theory": TheoryQuestion,
           "coding": Problem}
_PAYLOADS = {"mcq": mcq_payload, "debug": debug_payload, "theory": theory_payload,
             "coding": coding_payload}


def _level(obj) -> str:
    return getattr(obj.difficulty, "value", obj.difficulty) or "easy"


def _step(s: PracticeSession, item_type: str, obj, payload: dict) -> RunStep:
    return RunStep(s.id, len(s.served), len(s.plan), False, item_type, s.topic, _level(obj),
                   payload)


def next_step(db: Session, user_id: int, now: datetime) -> RunStep:
    """The open run's current item: the last one served until it is graded, then the
    next slot's. A slot whose type has nothing left takes the next type that has; when
    none has, the run ends where it is."""
    s = lifecycle.open_run(db, user_id, now)
    if s is None:
        raise SessionNotFound("No topic practice is in progress.")
    db.refresh(s, with_for_update=True)
    if s.served and not s.served[-1].get("graded"):
        last = s.served[-1]
        obj = db.get(_MODELS[last["type"]], last["id"])
        if obj is not None:
            return _step(s, last["type"], obj, _PAYLOADS[last["type"]](obj))
    if len(s.served) < len(s.plan):
        difficulty = _difficulty(db, user_id, s.topic, s.language)
        for item_type in FALLBACKS[s.plan[len(s.served)]]:
            picked = _pick(db, user_id, s, item_type, difficulty)
            if picked is not None:
                lifecycle.serve_in_run(db, s, item_type, picked[0].id, now)
                return _step(s, item_type, *picked)
        s.plan = list(s.plan[:len(s.served)])
        db.flush()
    return RunStep(s.id, len(s.served), len(s.plan), True)
