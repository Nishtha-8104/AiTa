"""Practice session lifecycle: when a session opens, what joins it, and how it closes.
Nothing here commits; callers do. `served` is plain JSON, so every change assigns a new list."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import SessionNotFound
from app.features.hints.models import HintEvent
from app.features.learner_model.logic.mastery import is_solved
from app.features.learner_model.models import LearningEvent
from app.features.practice.models import PracticeSession

IDLE_MINUTES = 30
CARRIED_TYPES = ("coding", "debug")
WRAP_UP_WAITS = ("idle", "language_switch", "mode_switch")
_ITEM_TYPES = {"mcq": "mcq", "diagnostic": "mcq", "debug": "debug", "coding": "coding",
               "theory": "theory"}


def item_type_of(assessment_type: str) -> str:
    return _ITEM_TYPES[assessment_type]


def _utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _current(db: Session, user_id: int) -> PracticeSession | None:
    return (db.query(PracticeSession)
            .filter(PracticeSession.user_id == user_id, PracticeSession.ended_at.is_(None))
            .order_by(PracticeSession.id.desc()).first())


def _latest_closed(db: Session, user_id: int) -> PracticeSession | None:
    return (db.query(PracticeSession)
            .filter(PracticeSession.user_id == user_id, PracticeSession.ended_at.isnot(None))
            .order_by(PracticeSession.id.desc()).first())


def _carry(closed: PracticeSession | None, language: str) -> list[dict]:
    """One hop only: an entry carried in and never touched again does not carry on."""
    if closed is None or closed.language != language:
        return []
    return [{**e, "carried": True} for e in closed.served
            if e["type"] in CARRIED_TYPES and not e["solved"] and not e.get("carried")]


def _is(entry: dict, item_type: str, item_id: int) -> bool:
    return entry["type"] == item_type and entry["id"] == item_id


def _settled(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k != "carried"}


def _serves(s: PracticeSession, item_type: str, item_id: int) -> bool:
    return any(_is(e, item_type, item_id) for e in s.served)


def _idle(s: PracticeSession, now: datetime) -> bool:
    return _utc(now) - _utc(s.last_activity_at) >= timedelta(minutes=IDLE_MINUTES)


def _close(db: Session, s: PracticeSession, reason: str, ended_at: datetime) -> PracticeSession | None:
    if not s.graded_count:
        db.delete(s)
        db.flush()
        return None
    s.ended_at, s.end_reason = ended_at, reason
    db.flush()
    return s


def close_if_idle(db: Session, user_id: int, now: datetime) -> PracticeSession | None:
    s = _current(db, user_id)
    if s is None or not _idle(s, now):
        return None
    return _close(db, s, "idle", _utc(s.last_activity_at))


def open_session(db: Session, user_id: int,
                 now: datetime | None = None) -> PracticeSession | None:
    close_if_idle(db, user_id, now or datetime.now(timezone.utc))
    return _current(db, user_id)


def record_served(db: Session, user_id: int, item_type: str, item_id: int, language: str,
                  now: datetime) -> PracticeSession:
    s = open_session(db, user_id, now)
    if s is not None and s.language != language:
        _close(db, s, "language_switch", now)
        s = None
    if s is not None and s.topic is not None:
        _close(db, s, "mode_switch", now)
        s = None
    if s is None:
        s = PracticeSession(user_id=user_id, language=language, started_at=now,
                            last_activity_at=now, graded_count=0,
                            served=_carry(_latest_closed(db, user_id), language))
        db.add(s)
    if _serves(s, item_type, item_id):
        s.served = [_settled(e) if _is(e, item_type, item_id) else dict(e) for e in s.served]
    else:
        s.served = [*(dict(e) for e in s.served),
                    {"type": item_type, "id": item_id, "solved": False}]
    s.last_activity_at = now
    db.flush()
    return s


def touch(db: Session, user_id: int, item_type: str, item_id: int, now: datetime) -> bool:
    s = open_session(db, user_id, now)
    if s is None or not _serves(s, item_type, item_id):
        return False
    s.last_activity_at = now
    db.flush()
    return True


def _joinable(db: Session, user_id: int, item_type: str, item_id: int, language: str,
              now: datetime) -> PracticeSession | None:
    s = open_session(db, user_id, now)
    if s is not None:
        return s if _serves(s, item_type, item_id) else None
    carried = _carry(_latest_closed(db, user_id), language)
    if not any(_is(e, item_type, item_id) for e in carried):
        return None
    return record_served(db, user_id, item_type, item_id, language, now)


def attach_event(db: Session, event: LearningEvent, item_type: str,
                 now: datetime) -> PracticeSession | None:
    s = _joinable(db, event.user_id, item_type, event.item_id, event.language, now)
    if s is None:
        return None
    solved = is_solved(event.score, event.hint_level_used or 0)
    event.session_id = s.id
    s.graded_count = (s.graded_count or 0) + 1
    s.served = [{**_settled(e), "solved": e["solved"] or solved, "graded": True}
                if _is(e, item_type, event.item_id) else dict(e) for e in s.served]
    s.last_activity_at = now
    db.flush()
    return s


def attach_hint(db: Session, hint: HintEvent, now: datetime) -> None:
    """Never opens a session: a hint follows a submit, and the submit already carried."""
    if hint.source != "practice":
        return
    s = open_session(db, hint.user_id, now)
    if s is None or not _serves(s, "coding", hint.problem_id):
        return
    hint.session_id = s.id
    s.last_activity_at = now
    db.flush()


def finish(db: Session, user_id: int, session_id: int, now: datetime) -> PracticeSession:
    s = db.get(PracticeSession, session_id)
    if s is None or s.user_id != user_id or s.ended_at is not None or not s.graded_count:
        raise SessionNotFound("No open practice session with that id.")
    return _close(db, s, "finished", _utc(s.last_activity_at) if _idle(s, now) else now)


def open_run(db: Session, user_id: int, now: datetime) -> PracticeSession | None:
    s = open_session(db, user_id, now)
    return s if s is not None and s.topic is not None else None


def start_run(db: Session, user_id: int, topic: str, language: str, plan: list[str],
              now: datetime) -> PracticeSession:
    """Resumes an unfinished run on the same topic; anything else open is closed first.
    A run starts empty: nothing carries into a set the student chose."""
    s = open_session(db, user_id, now)
    if s is not None and s.topic == topic and s.language == language and not run_done(s):
        return s
    if s is not None:
        _close(db, s, "mode_switch", now)
    s = PracticeSession(user_id=user_id, language=language, started_at=now,
                        last_activity_at=now, graded_count=0, served=[], topic=topic,
                        plan=plan)
    db.add(s)
    db.flush()
    return s


def run_done(s: PracticeSession) -> bool:
    return len(s.served) >= len(s.plan or []) and all(e.get("graded") for e in s.served)


def serve_in_run(db: Session, s: PracticeSession, item_type: str, item_id: int,
                 now: datetime) -> None:
    s.served = [*(dict(e) for e in s.served),
                {"type": item_type, "id": item_id, "solved": False}]
    s.last_activity_at = now
    db.flush()


def close_for_language_switch(db: Session, user_id: int, now: datetime) -> None:
    s = open_session(db, user_id, now)
    if s is not None:
        _close(db, s, "language_switch", now)


def pending_wrap_up(db: Session, user_id: int) -> PracticeSession | None:
    s = _latest_closed(db, user_id)
    if (s is None or s.end_reason not in WRAP_UP_WAITS or not s.graded_count
            or s.wrap_up_seen_at is not None):
        return None
    return s
