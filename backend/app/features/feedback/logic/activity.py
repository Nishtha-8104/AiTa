"""What a set of learning events says, shaped for an LLM prompt, and the solutions the
written feedback must not quote. Shared by the session wrap-up and the Feedback page.
Read-only."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.features.learner_model.logic.mastery import SEED_KINDS, is_solved
from app.features.learner_model.models import LearningEvent
from app.features.practice.models import DebugChallenge
from app.features.problems.models import ProblemReference

WINDOW_DAYS = 14
WINDOW_EVENTS = 30
HINT_LEVELS = (1, 2, 3, 4)
TOP_MISTAKES = 3


def _item_ids(events: list[LearningEvent], kind: str) -> set[int]:
    return {e.item_id for e in events if e.kind == kind and e.item_id is not None}


def references_for(db: Session, events: list[LearningEvent]) -> list[str]:
    problems = _item_ids(events, "code")
    challenges = _item_ids(events, "debug")
    sources = [source for (source,) in db.query(ProblemReference.source)
               .filter(ProblemReference.problem_id.in_(problems))] if problems else []
    fixed = [code for (code,) in db.query(DebugChallenge.fixed_code)
             .filter(DebugChallenge.id.in_(challenges))] if challenges else []
    return sources + fixed


def _topics(events: list[LearningEvent]) -> list[dict]:
    first: dict[str, LearningEvent] = {}
    last: dict[str, LearningEvent] = {}
    for e in events:
        if e.topic is None:
            continue
        first.setdefault(e.topic, e)
        last[e.topic] = e
    changes = []
    for topic, start in first.items():
        before = start.mastery_before if start.mastery_before is not None else 0.0
        after = last[topic].mastery_after
        changes.append({"topic": topic, "before": round(before, 2),
                        "after": round(before if after is None else after, 2)})
    return changes


def activity_context(db: Session, user_id: int, events: list[LearningEvent]) -> dict:
    ordered = sorted((e for e in events if e.user_id == user_id), key=lambda e: e.id)
    hints = Counter(e.hint_level_used for e in ordered if e.hint_level_used)
    mistakes = Counter(tag for e in ordered for tag in e.misconceptions or [])
    return {
        "items": [{"kind": e.kind, "topic": e.topic, "score": round(e.score, 2),
                   "solved": is_solved(e.score, e.hint_level_used or 0),
                   "hint_level": e.hint_level_used or 0,
                   "misconceptions": e.misconceptions or []}
                  for e in ordered],
        "topics": _topics(ordered),
        "hints": {level: hints[level] for level in HINT_LEVELS},
        "mistakes": [{"misconception": tag, "count": count}
                     for tag, count in mistakes.most_common(TOP_MISTAKES)],
    }


def recent_events(db: Session, user_id: int) -> list[LearningEvent]:
    since = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    return (db.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.kind.notin_(SEED_KINDS),
                    LearningEvent.created_at >= since)
            .order_by(LearningEvent.created_at.desc(), LearningEvent.id.desc())
            .limit(WINDOW_EVENTS).all())
