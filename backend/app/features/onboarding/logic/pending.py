"""Theory answers the judge has not graded yet: retried in the background right after the
answer and by a periodic sweep, then folded into concept level and mastery."""

import asyncio
import logging
import time
from collections.abc import Iterable
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.llm_choice import has_server_model, pet_default
from app.features.accounts.models import SkillLevel, User
from app.features.learner_model.service import apply_theory_adjustment
from app.features.onboarding.logic import profile_card, seeding
from app.features.onboarding.logic.graders import theory
from app.features.onboarding.logic.types import ItemRef, Resp, Seed
from app.features.onboarding.models import DiagnosticItem, DiagnosticResponse, OnboardingRecord

logger = logging.getLogger(__name__)

PENDING = "pending"
SAVED = "saved"
SKIPPED = "skipped"
MAX_ATTEMPTS = 5
SWEEP_INTERVAL_S = 120
RETRY_DELAYS = (2, 4, 8)
ABANDONED_AFTER = timedelta(hours=24)


def responses_for(db: Session, user_id: int, language: str | None) -> list[Resp]:
    """One check's responses: the onboarding check's or a re-check's."""
    rows = (db.query(DiagnosticResponse, DiagnosticItem)
            .join(DiagnosticItem, DiagnosticItem.id == DiagnosticResponse.item_id)
            .filter(DiagnosticResponse.user_id == user_id,
                    DiagnosticResponse.language == language)
            .order_by(DiagnosticResponse.order)
            .all())
    return [Resp(ItemRef(item.topic, item.kind, item.difficulty, resp.phase),
                 resp.score, resp.graded_by)
            for resp, item in rows]


def _pending(db: Session):
    return (db.query(DiagnosticResponse, DiagnosticItem)
            .join(DiagnosticItem, DiagnosticItem.id == DiagnosticResponse.item_id)
            .filter(DiagnosticResponse.graded_by == PENDING, DiagnosticItem.kind == "theory"))


def has_pending(db: Session, user_id: int) -> bool:
    return _pending(db).filter(DiagnosticResponse.user_id == user_id).first() is not None


def _count_attempt(resp: DiagnosticResponse) -> None:
    """The judge answered but left this row ungraded; after MAX_ATTEMPTS it is given up."""
    attempts = (resp.reveal or {}).get("attempts", 0) + 1
    resp.reveal = {"attempts": attempts}
    if attempts >= MAX_ATTEMPTS:
        resp.score, resp.graded_by = None, SKIPPED


def grade_pending_for_user(db: Session, user_id: int) -> int:
    rows = (_pending(db)
            .filter(DiagnosticResponse.user_id == user_id)
            .order_by(DiagnosticResponse.order)
            .with_for_update(skip_locked=True, of=DiagnosticResponse)
            .all())
    grades, attempted = theory.grade_batch(user_id, rows) if rows else ({}, False)
    topics = []
    for resp, item in rows:
        grade = grades.get(resp.id)
        if grade is None:
            if attempted:
                _count_attempt(resp)
            continue
        resp.score, resp.graded_by = grade.score, grade.graded_by
        resp.reveal, resp.feedback = grade.reveal, grade.feedback
        topics.append(item.topic)
    db.commit()
    if topics:
        after_regrade(db, user_id, topics)
    return len(topics)


def after_regrade(db: Session, user_id: int, topics: Iterable[str] | None = None) -> None:
    record = db.get(OnboardingRecord, user_id)
    if record is None:
        return
    responses = responses_for(db, user_id, record.language)
    theory_scores = [r.score for r in responses if r.ref.phase == "theory"]
    record.concept_level = seeding.concept_level(theory_scores)
    db.commit()
    if record.finished_at is None:
        return
    if topics is None:
        topics = [r.ref.topic for r in responses
                  if r.ref.phase == "theory" and r.score is not None]
    current = seeding.seeds(responses)
    adjusted = {}
    for topic in dict.fromkeys(topics):
        if topic in current and apply_theory_adjustment(db, user_id, topic, current[topic].value,
                                                         record.language):
            adjusted[topic] = [current[topic].value, current[topic].source]
    if adjusted:
        record.seeds = {**(record.seeds or {}), **adjusted}
        merged = {topic: Seed(value, source) for topic, (value, source) in record.seeds.items()}
        record.title = profile_card.title_for(merged)
        db.get(User, user_id).skill_level = SkillLevel(seeding.skill_level(merged))
        db.commit()


def queue_abandoned(db: Session, now: datetime | None = None) -> int:
    """Saved answers of a check the student walked away from would otherwise never reach
    the judge."""
    cutoff = (now or datetime.now(timezone.utc)) - ABANDONED_AFTER
    count = (db.query(DiagnosticResponse)
             .filter(DiagnosticResponse.graded_by == SAVED,
                     DiagnosticResponse.created_at < cutoff)
             .update({DiagnosticResponse.graded_by: PENDING}, synchronize_session=False))
    db.commit()
    return count


def sweep_once(db: Session) -> int:
    queue_abandoned(db)
    user_ids = [uid for (uid,) in (_pending(db)
                                   .with_entities(DiagnosticResponse.user_id)
                                   .distinct().all())]
    db.commit()
    graded = 0
    for user_id in user_ids:
        try:
            graded += grade_pending_for_user(db, user_id)
        except Exception:
            logger.exception("theory sweep failed for user %s", user_id)
            db.rollback()
    return graded


def _sweep_in_new_session() -> int:
    if not has_server_model():
        return 0
    with SessionLocal() as db:
        return sweep_once(db)


async def run_sweep_loop(stop: asyncio.Event, interval_s: float = SWEEP_INTERVAL_S) -> None:
    while not stop.is_set():
        try:
            await asyncio.to_thread(_sweep_in_new_session)
        except Exception:
            logger.exception("theory sweep failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        except asyncio.TimeoutError:
            pass


def retry_with_backoff(user_id: int, delays: tuple[float, ...] = RETRY_DELAYS) -> None:
    """Runs after the response, when nobody would see a key error: PET default when the
    server has one, else the student's own model."""
    try:
        with pet_default() if has_server_model() else nullcontext(), SessionLocal() as db:
            for delay in delays:
                time.sleep(delay)
                grade_pending_for_user(db, user_id)
                if not has_pending(db, user_id):
                    return
    except Exception:
        logger.exception("theory retry failed for user %s", user_id)
