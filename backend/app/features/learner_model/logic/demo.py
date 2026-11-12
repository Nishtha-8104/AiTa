"""Rehearsal support: reset one demo account, and the three numbers for the report.
Never touches any account other than the one named."""

from collections import defaultdict

from sqlalchemy import delete, func
from sqlalchemy.orm import Session

from app.features.accounts.models import LearningProfile, User
from app.features.accounts.service import AuthService
from app.features.gamification.models import GamificationAward
from app.features.grading.models import CodeEvaluation
from app.features.hints.models import HintEvent
from app.features.hints.service import leak_rate
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.practice.models import DebugAttempt, McqAttempt

_LEARNER_TABLES = (GamificationAward, LearningEvent, TopicMastery, HintEvent, McqAttempt,
                   DebugAttempt, LearningProfile)


def reset_account(db: Session, email: str, username: str,
                  full_name: str = "Demo Student") -> User:
    """Delete the account and everything it owns, then create it again from scratch.
    The learner-model tables are cleared explicitly; the rest follow the user row
    through ON DELETE CASCADE."""
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        for model in _LEARNER_TABLES:
            db.execute(delete(model).where(model.user_id == existing.id))
        db.execute(delete(User).where(User.id == existing.id))
        db.commit()
        db.expire_all()
    return AuthService.create_user(db, email, username, full_name)


def mastery_trace(db: Session, user_id: int) -> dict[str, list[dict]]:
    trace = defaultdict(list)
    events = (db.query(LearningEvent)
              .filter(LearningEvent.user_id == user_id, LearningEvent.topic.isnot(None))
              .order_by(LearningEvent.id))
    for e in events:
        trace[e.topic].append({"kind": e.kind, "score": round(e.score, 3),
                               "hint": e.hint_level_used,
                               "before": round(e.mastery_before, 3),
                               "after": round(e.mastery_after, 3)})
    return dict(trace)


def verification_counts(db: Session) -> dict[str, int]:
    rows = (db.query(CodeEvaluation.verification_status, func.count())
            .group_by(CodeEvaluation.verification_status).all())
    return {status or "unknown": count for status, count in rows}


def report(db: Session, user_id: int | None = None) -> dict:
    blocked, total = leak_rate(db)
    return {
        "hint_leak_rate": {"blocked": blocked, "llm_hints": total,
                           "rate": round(blocked / total, 3) if total else 0.0},
        "correctness": verification_counts(db),
        "mastery_trace": mastery_trace(db, user_id) if user_id else {},
    }
