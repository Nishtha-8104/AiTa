"""Switching the study language. A language never used before needs a code-only check in
it; its mastery comes from that check alone, and topics it doesn't reach stay at the
prior. Switching back to a used language is free: its mastery is still there."""

import logging
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.exceptions import LanguageCheckRequired, OnboardingConflict
from app.core.topics import TOPICS
from app.features.accounts.models import User
from app.features.learner_model.service import current_language, record_diagnostic_seed
from app.features.onboarding.logic import pending, profile_card, seeding
from app.features.onboarding.models import LanguageCheck, OnboardingRecord
from app.features.onboarding.schemas import AnswerIn, AnswerOut, DiagOut, RecheckOut, SwitchOut
from app.features.onboarding.service import Run, answer_in, now, serve, walk_done
from app.features.practice import service as lifecycle

logger = logging.getLogger(__name__)


def _finished_record(db: Session, user: User) -> OnboardingRecord:
    record = db.get(OnboardingRecord, user.id)
    if record is None or record.finished_at is None:
        raise OnboardingConflict("Finish onboarding before switching language.")
    return record


def _open_check(db: Session, user: User) -> LanguageCheck | None:
    check = db.get(LanguageCheck, (user.id, user.preferred_language))
    return check if check is not None and check.finished_at is None else None


def switch_language(db: Session, user: User, language: str) -> SwitchOut:
    record = _finished_record(db, user)
    user_id = user.id
    if language != current_language(db, user_id):
        try:
            lifecycle.close_for_language_switch(db, user_id, datetime.now(timezone.utc))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("practice session close failed for user %s", user_id)
    user.preferred_language = language
    used = language == record.language or db.get(LanguageCheck, (user.id, language))
    if not used:
        db.add(LanguageCheck(user_id=user.id, language=language, seeds={}))
    db.commit()
    return SwitchOut(language=language, needs_check=_open_check(db, user) is not None)


def require_no_open_check(db: Session, user: User) -> None:
    if _open_check(db, user) is not None:
        raise LanguageCheckRequired(
            "Take the short check in your new language before practising in it.")


def _run(db: Session, user: User) -> Run:
    check = _open_check(db, user)
    if check is None:
        raise OnboardingConflict("There is no language check to take.")
    return Run(check, check.language, theory=False)


def next_item(db: Session, user: User) -> DiagOut:
    run = _run(db, user)
    if run.record.diagnostic_started_at is None:
        run.record.diagnostic_started_at = now()
        db.commit()
    return serve(db, run)


def answer(db: Session, user: User, data: AnswerIn,
           background_tasks: BackgroundTasks) -> AnswerOut:
    return answer_in(db, _run(db, user), data, background_tasks)


def finish(db: Session, user: User) -> RecheckOut:
    run = _run(db, user)
    check = run.record
    if check.diagnostic_started_at is None or not walk_done(db, run):
        raise OnboardingConflict("Finish the language check first.")
    found = seeding.seeds(pending.responses_for(db, user.id, check.language))
    check.seeds = {topic: [seed.value, seed.source] for topic, seed in found.items()}
    check.title = profile_card.title_for(found)
    check.finished_at = now()
    check.current_item_id = None
    record_diagnostic_seed(db, user.id, {topic: seed.value for topic, seed in found.items()},
                           check.language)
    db.commit()
    return RecheckOut(language=check.language, title=check.title,
                      bands={topic: profile_card.band_of(found.get(topic)) for topic in TOPICS})
