# Endpoints, under /api/v1/practice-sessions:
#   GET  /current                 the open practice session, once it has a graded answer
#   GET  /pending                 the last session that closed on its own, wrap-up unseen
#   POST /{session_id}/finish     finish the open session and return its wrap-up
#   GET  /{session_id}            the wrap-up of one of my closed sessions
#   POST /{session_id}/feedback   write the short feedback for a closed session

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import SessionNotFound
from app.features.accounts.models import User
from app.features.practice import service as lifecycle
from app.features.practice.logic.practice_session.facts import session_facts
from app.features.practice.logic.practice_session.feedback import generate_session_feedback
from app.features.practice.models import PracticeSession
from app.features.practice.schemas import (
    CurrentOut,
    FeedbackRequest,
    MistakeOut,
    PendingOut,
    SessionFeedbackOut,
    TopicChangeOut,
    TypeCountOut,
    WrapUpOut,
)

router = APIRouter(prefix="/practice-sessions", tags=["Practice Sessions"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _closed(db: Session, user_id: int, session_id: int) -> PracticeSession:
    s = db.get(PracticeSession, session_id)
    if s is None or s.user_id != user_id or s.ended_at is None:
        raise SessionNotFound("No finished practice session with that id.")
    return s


def _wrap_up(db: Session, s: PracticeSession) -> WrapUpOut:
    facts = session_facts(db, s)
    return WrapUpOut(
        id=s.id, language=facts.language, started_at=facts.started_at,
        ended_at=facts.ended_at, end_reason=s.end_reason, topic=s.topic,
        duration_s=facts.duration_s,
        by_type={t: TypeCountOut(tried=c.tried, solved=c.solved)
                 for t, c in facts.by_type.items()},
        topics=[TopicChangeOut(topic=t.topic, before=t.before, after=t.after,
                               band_after=t.band_after) for t in facts.topics],
        hints=facts.hints,
        mistakes=[MistakeOut(misconception=tag, count=n) for tag, n in facts.mistakes],
        stuck_topics=facts.stuck_topics,
        awards=facts.awards,
        feedback=SessionFeedbackOut(**s.feedback) if s.feedback else None,
        feedback_status=s.feedback_status,
    )


@router.get("/current", response_model=CurrentOut,
            summary="The open Practice session, if it has a graded answer")
def get_current(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    s = lifecycle.open_session(db, current_user.id, _now())
    db.commit()
    if s is None:
        return CurrentOut()
    return CurrentOut(id=s.id if s.graded_count else None, graded_count=s.graded_count or 0)


@router.get("/pending", response_model=Optional[PendingOut],
            summary="The last session that closed on its own and whose wrap-up is unseen")
def get_pending(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    lifecycle.close_if_idle(db, current_user.id, _now())
    db.commit()
    s = lifecycle.pending_wrap_up(db, current_user.id)
    if s is None:
        return None
    facts = session_facts(db, s)
    return PendingOut(id=s.id, ended_at=s.ended_at, end_reason=s.end_reason,
                      solved=sum(c.solved for c in facts.by_type.values()),
                      topics=[t.topic for t in facts.topics])


@router.post("/{session_id}/finish", response_model=WrapUpOut,
             summary="Finish the open Practice session and return its wrap-up")
def finish(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    s = lifecycle.finish(db, current_user.id, session_id, _now())
    db.commit()
    return _wrap_up(db, s)


@router.get("/{session_id}", response_model=WrapUpOut,
            summary="The wrap-up of one of your closed Practice sessions")
def get_wrap_up(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    s = _closed(db, current_user.id, session_id)
    if s.wrap_up_seen_at is None:
        s.wrap_up_seen_at = _now()
        db.commit()
    return _wrap_up(db, s)


@router.post("/{session_id}/feedback", response_model=WrapUpOut,
             summary="Write the short feedback for a closed session (once; retry regenerates)")
def feedback(
    session_id: int,
    req: FeedbackRequest = FeedbackRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    s = _closed(db, current_user.id, session_id)
    retry = req.retry and s.feedback_status in ("unavailable", "blocked")
    if s.feedback_status == "none" or retry:
        generate_session_feedback(db, s, retry=retry)
        db.commit()
    return _wrap_up(db, s)
