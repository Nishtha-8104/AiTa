"""The onboarding orchestrator: the only module that writes the onboarding tables and
calls the Profiling Agent. The walk, seeding and card it drives are pure."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidAnswer, OnboardingConflict
from app.core.topics import TOPICS
from app.features.accounts.models import SkillLevel, User
from app.features.learner_model.service import record_diagnostic_seed
from app.features.onboarding.logic import bank, pending, profile_card, seeding, steps, walk
from app.features.onboarding.logic.graders import GRADERS
from app.features.onboarding.logic.types import Ask, BankIndex, Resp, Seed
from app.features.onboarding.models import (
    DiagnosticItem,
    DiagnosticResponse,
    LanguageCheck,
    OnboardingRecord,
)
from app.features.onboarding.schemas import (
    THEORY_CAP,
    AnswerIn,
    AnswerOut,
    CardOut,
    DiagOut,
    ProfilePatch,
    StateOut,
    TheoryReveal,
)
from app.features.practice.logic.assessment import policy

HOLE_TRIES = 5
# A theory answer inside the block, not yet sent to the judge. Only "pending" rows are
# retried (background, sweep), so the block still goes out in one call.
SAVED = pending.SAVED
_BANDS = {value: band for band, value in seeding.SEED_VALUES.items()}


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Run:
    """One check: the onboarding one, or a code-only re-check in a new language."""
    record: OnboardingRecord | LanguageCheck
    language: str
    theory: bool

    @property
    def user_id(self) -> int:
        return self.record.user_id


def _record(db: Session, user: User) -> OnboardingRecord:
    record = db.get(OnboardingRecord, user.id)
    if record is None:
        record = OnboardingRecord(user_id=user.id, started_at=now(), step_durations={},
                                  seeds={})
        db.add(record)
        db.commit()
    return record


def onboarding_run(user: User, record: OnboardingRecord) -> Run:
    return Run(record, record.language or user.preferred_language, theory=True)


def _answered_ids(db: Session, user_id: int) -> set[int]:
    return {item_id for (item_id,) in db.query(DiagnosticResponse.item_id)
            .filter(DiagnosticResponse.user_id == user_id)}


def _responses(db: Session, run: Run) -> list[Resp]:
    return pending.responses_for(db, run.user_id, run.language)


def _index(db: Session, run: Run) -> BankIndex:
    index = bank.bank_index(db, run.language)
    return index if run.theory else frozenset(k for k in index if k[1] != "theory")


def _plan(db: Session, run: Run, resps: list[Resp],
          exclude: set[int]) -> tuple[tuple[Ask, DiagnosticItem] | None, BankIndex]:
    """The walk's next ask and a bank item for it. A ref the bank cannot serve is a hole:
    it is dropped from the index and the walk asked again."""
    index = _index(db, run)
    for _ in range(HOLE_TRIES):
        step = walk.next_step(resps, index)
        if not isinstance(step, Ask):
            break
        item = bank.fetch(db, step.ref, run.language, exclude)
        if item is not None:
            return (step, item), index
        index = index - {(step.ref.topic, step.ref.kind, step.ref.difficulty)}
    return None, index


def _phase_of(db: Session, run: Run, item: DiagnosticItem, resps: list[Resp],
              exclude: set[int]) -> str:
    """The walk on the same responses replays the ask the item was served for."""
    if item.kind == "theory":
        return "theory"
    found, _ = _plan(db, run, resps, exclude)
    if found and found[1].id == item.id:
        return found[0].ref.phase
    return "write" if item.kind == "write_code" else "code"


def topic_map(resps: list[Resp], asking: str | None = None) -> dict[str, str]:
    preview = seeding.seeds(resps)
    code = [r for r in resps if r.ref.phase in walk.CODE_PHASES]
    unscored = {r.ref.topic for r in code} - {r.ref.topic for r in code if r.score is not None}

    def state(topic: str) -> str:
        if topic == asking:
            return "asking"
        if topic in preview:
            seed = preview[topic]
            return "inferred" if seed.source == "inferred" else _BANDS[seed.value]
        return "skipped" if topic in unscored else "unknown"

    return {topic: state(topic) for topic in TOPICS}


def serve(db: Session, run: Run) -> DiagOut:
    record = run.record
    resps = _responses(db, run)
    if record.finished_at is not None:
        return DiagOut(item=None, order=len(resps), remaining=0, topic_map=topic_map(resps),
                       phase=None, done=True)
    exclude = _answered_ids(db, run.user_id)
    current = record.current_item_id
    if current is not None and current not in exclude:
        item = db.get(DiagnosticItem, current)
        index = _index(db, run)
        phase = _phase_of(db, run, item, resps, exclude)
    else:
        found, index = _plan(db, run, resps, exclude)
        item, phase = (found[1], found[0].ref.phase) if found else (None, None)
        record.current_item_id = item.id if item else None
        db.commit()
    if item is None:
        return DiagOut(item=None, order=len(resps), remaining=0, topic_map=topic_map(resps),
                       phase=None, done=True)
    left = walk.remaining(resps, index)
    return DiagOut(item=bank.payload(item), order=len(resps) + 1, remaining=max(0, left - 1),
                   topic_map=topic_map(resps, item.topic), phase=phase, done=False)


def walk_done(db: Session, run: Run) -> bool:
    found, _ = _plan(db, run, _responses(db, run), _answered_ids(db, run.user_id))
    return found is None


def next_item(db: Session, user: User) -> DiagOut:
    record = _record(db, user)
    if not steps.background_saved(record):
        raise OnboardingConflict("Finish the background steps before the diagnostic.")
    if record.diagnostic_started_at is None and record.finished_at is None:
        record.diagnostic_started_at = record.language_locked_at = now()
        record.language = user.preferred_language
        steps.move_to(record, "diagnostic")
        db.commit()
    return serve(db, onboarding_run(user, record))


def _stored(db: Session, user_id: int, item_id: int) -> DiagnosticResponse | None:
    return (db.query(DiagnosticResponse)
            .filter_by(user_id=user_id, item_id=item_id).one_or_none())


def _theory_reveals(db: Session, user_id: int) -> list[TheoryReveal]:
    rows = (db.query(DiagnosticResponse, DiagnosticItem)
            .join(DiagnosticItem, DiagnosticItem.id == DiagnosticResponse.item_id)
            .filter(DiagnosticResponse.user_id == user_id, DiagnosticResponse.phase == "theory",
                    DiagnosticResponse.graded_by.notin_((pending.PENDING, SAVED)))
            .order_by(DiagnosticResponse.order))
    return [TheoryReveal(item_id=item.id, topic=item.topic, question=item.body["question"],
                         score=resp.score, reveal=resp.reveal, feedback=resp.feedback)
            for resp, item in rows]


def _answer_out(db: Session, run: Run, row: DiagnosticResponse, saved_only: bool,
                theory: list[TheoryReveal] | None = None) -> AnswerOut:
    following = serve(db, run)
    written = row.phase == "theory"
    return AnswerOut(reveal=None if written else row.reveal,
                     score=None if written else row.score, saved_only=saved_only,
                     theory_reveals=theory or [],
                     topic_map=following.topic_map, next=following)


def _replay(db: Session, run: Run, row: DiagnosticResponse) -> AnswerOut:
    saved_only = row.graded_by == SAVED
    block_sent = row.phase == "theory" and not saved_only
    return _answer_out(db, run, row, saved_only,
                       _theory_reveals(db, run.user_id) if block_sent else None)


def _release(db: Session, user_id: int) -> int:
    """Hand the user's saved theory answers to the judge queue."""
    count = (db.query(DiagnosticResponse)
             .filter(DiagnosticResponse.user_id == user_id, DiagnosticResponse.graded_by == SAVED)
             .update({DiagnosticResponse.graded_by: pending.PENDING}))
    db.commit()
    return count


def _grade_theory_block(db: Session, user_id: int,
                        background_tasks: BackgroundTasks) -> list[TheoryReveal]:
    _release(db, user_id)
    pending.grade_pending_for_user(db, user_id)
    if pending.has_pending(db, user_id):
        background_tasks.add_task(pending.retry_with_backoff, user_id)
    return _theory_reveals(db, user_id)


def answer_in(db: Session, run: Run, data: AnswerIn,
              background_tasks: BackgroundTasks) -> AnswerOut:
    record = run.record
    stored = _stored(db, run.user_id, data.item_id)
    if stored is not None:
        return _replay(db, run, stored)
    if record.finished_at is not None or data.item_id != record.current_item_id:
        raise OnboardingConflict("That is not the current diagnostic question.")
    item = db.get(DiagnosticItem, data.item_id)
    given = data.answer.model_dump(exclude_none=True)
    if item.kind == "theory" and len(given.get("text") or "") > THEORY_CAP:
        raise InvalidAnswer(f"A theory answer can be at most {THEORY_CAP} characters.")

    resps = _responses(db, run)
    exclude = _answered_ids(db, run.user_id)
    row = DiagnosticResponse(user_id=run.user_id, item_id=item.id, order=len(resps) + 1,
                             phase=_phase_of(db, run, item, resps, exclude),
                             language=run.language, answer=given, ms_taken=data.ms_taken)
    if item.kind == "theory":
        row.score, row.graded_by = None, SAVED
    else:
        grade = GRADERS[item.kind](item, given, None)
        row.score, row.graded_by = grade.score, grade.graded_by
        row.reveal, row.feedback = grade.reveal, grade.feedback
    db.add(row)
    record.current_item_id = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _replay(db, run, _stored(db, run.user_id, data.item_id))

    if item.kind != "theory":
        return _answer_out(db, run, row, saved_only=False)
    found, _ = _plan(db, run, _responses(db, run), exclude | {item.id})
    if found is not None:
        return _answer_out(db, run, row, saved_only=True)
    graded = _grade_theory_block(db, run.user_id, background_tasks)
    return _answer_out(db, run, row, saved_only=False, theory=graded)


def answer(db: Session, user: User, data: AnswerIn,
           background_tasks: BackgroundTasks) -> AnswerOut:
    return answer_in(db, onboarding_run(user, _record(db, user)), data, background_tasks)


def _seeds_of(record) -> dict[str, Seed]:
    return {topic: Seed(value, source) for topic, (value, source)
            in (record.seeds or {}).items()}


def _card(db: Session, user: User, record: OnboardingRecord) -> CardOut:
    """Bands and title are the current language's check; concept level is shared."""
    seeds_from = record
    if user.preferred_language != (record.language or user.preferred_language):
        check = db.get(LanguageCheck, (user.id, user.preferred_language))
        seeds_from = check if check is not None and check.finished_at else None
    seeds = _seeds_of(seeds_from) if seeds_from is not None else {}
    card = profile_card.build(seeds, record.concept_level, steps.answers(db, user, record),
                              policy.start_topic(db, user.id))
    return CardOut(**asdict(card), theory_pending=pending.has_pending(db, user.id))


def _locked_record(db: Session, user: User) -> OnboardingRecord:
    return (db.query(OnboardingRecord).filter_by(user_id=user.id)
            .populate_existing().with_for_update().one())


def _write_results(db: Session, user: User, record: OnboardingRecord) -> None:
    run = onboarding_run(user, record)
    found = seeding.seeds(_responses(db, run))
    user.skill_level = SkillLevel(seeding.skill_level(found))
    record.seeds = {topic: [seed.value, seed.source] for topic, seed in found.items()}
    record.title = profile_card.title_for(found)
    record.finished_at = now()
    record.current_item_id = None
    steps.move_to(record, "done")
    # Commits the record together with the seeds, which also ends the _locked_record lock.
    record_diagnostic_seed(db, user.id, {topic: seed.value for topic, seed in found.items()},
                           run.language)
    db.commit()
    # Picks up theory the sweep graded meanwhile, and recomputes concept level.
    pending.after_regrade(db, user.id)


def finish(db: Session, user: User, background_tasks: BackgroundTasks) -> CardOut:
    record = _record(db, user)
    if record.finished_at is None:
        if (record.diagnostic_started_at is None
                or not walk_done(db, onboarding_run(user, record))):
            raise OnboardingConflict("Finish the diagnostic first.")
        # Only never-sent answers are graded here; ones the judge already failed on go to
        # the background retry, so the student never waits on a busy judge twice.
        if _release(db, user.id):
            pending.grade_pending_for_user(db, user.id)
        record = _locked_record(db, user)
        if record.finished_at is None:
            _write_results(db, user, record)
            if pending.has_pending(db, user.id):
                background_tasks.add_task(pending.retry_with_backoff, user.id)
    return _card(db, user, record)


def save_step(db: Session, user: User, step: str, data: BaseModel) -> StateOut:
    record = _record(db, user)
    if step == "language" and record.language_locked_at is not None:
        raise OnboardingConflict("The language is locked once the diagnostic starts.")
    steps.apply(db, user, record, step, data)
    steps.advance(record, step, now())
    db.commit()
    return state(db, user)


def edit_profile(db: Session, user: User, patch: ProfilePatch) -> CardOut:
    record = _record(db, user)
    if record.finished_at is None:
        raise OnboardingConflict("The profile can be edited once onboarding is finished.")
    for step in ("about", "learning"):
        data = getattr(patch, step)
        if data is not None:
            steps.apply(db, user, record, step, data)
    db.commit()
    return _card(db, user, record)


def state(db: Session, user: User) -> StateOut:
    record = _record(db, user)
    diagnostic = card = None
    if record.finished_at is not None:
        card = _card(db, user, record)
    elif record.diagnostic_started_at is not None:
        diagnostic = serve(db, onboarding_run(user, record))
    return StateOut(current_step=record.current_step, answers=steps.answers(db, user, record),
                    diagnostic=diagnostic, card=card)
