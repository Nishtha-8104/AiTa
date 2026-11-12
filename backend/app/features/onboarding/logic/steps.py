"""The background steps of onboarding: which fields each step writes, the step order, and
the saved answers read back for resume and the profile card."""

from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.features.accounts.models import User
from app.features.onboarding.models import LearnerPreferences, OnboardingRecord

ORDER = ("welcome", "language", "about", "learning", "diagnostic", "done")
BACKGROUND = ("language", "about", "learning")
EXPERIENCE_YEARS = {"none": 0.0, "lt6m": 0.25, "6to12m": 0.75, "1to2y": 1.5, "2yplus": 2.5}
LEARNING_FIELDS = ("explanation_style", "example_order", "chat_language", "hours_per_week")
# The preferences row is created by whichever of about / learning comes first and its
# columns are NOT NULL; answers() only reports a step once it has been saved.
PREF_DEFAULTS = {"goal": "course", "explanation_style": "step_by_step",
                 "example_order": "examples_first", "chat_language": "english",
                 "hours_per_week": "2to5"}


def utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _prefs(db: Session, user: User) -> LearnerPreferences:
    prefs = db.get(LearnerPreferences, user.id)
    if prefs is None:
        prefs = LearnerPreferences(user_id=user.id, **PREF_DEFAULTS)
        db.add(prefs)
    return prefs


def apply(db: Session, user: User, record: OnboardingRecord, step: str,
          data: BaseModel) -> None:
    if step == "language":
        user.preferred_language = data.language
    elif step == "about":
        user.year_of_study, user.institution = data.year_of_study, data.institution
        user.years_of_experience = EXPERIENCE_YEARS[data.experience]
        prefs = _prefs(db, user)
        prefs.goal, prefs.program = data.goal, data.program
    elif step == "learning":
        prefs = _prefs(db, user)
        for name in LEARNING_FIELDS:
            setattr(prefs, name, getattr(data, name))
        record.self_rating = data.self_rating


def move_to(record: OnboardingRecord, step: str) -> None:
    if ORDER.index(step) > ORDER.index(record.current_step or ORDER[0]):
        record.current_step = step


def advance(record: OnboardingRecord, step: str, at: datetime) -> None:
    since = utc(record.last_step_at or record.started_at or at)
    durations = dict(record.step_durations or {})
    durations.setdefault(step, round((at - since).total_seconds(), 1))
    record.step_durations = durations
    record.last_step_at = at
    move_to(record, ORDER[ORDER.index(step) + 1])


def background_saved(record: OnboardingRecord) -> bool:
    return set(BACKGROUND) <= set(record.step_durations or {})


def answers(db: Session, user: User, record: OnboardingRecord) -> dict:
    saved = record.step_durations or {}
    prefs = db.get(LearnerPreferences, user.id)
    about = learning = None
    if "about" in saved and prefs is not None:
        experience = next((bucket for bucket, years in EXPERIENCE_YEARS.items()
                           if years == user.years_of_experience), None)
        about = {"year_of_study": user.year_of_study, "program": prefs.program,
                 "institution": user.institution, "experience": experience,
                 "goal": prefs.goal}
    if "learning" in saved and prefs is not None:
        learning = {name: getattr(prefs, name) for name in LEARNING_FIELDS}
        learning["self_rating"] = record.self_rating
    return {"language": user.preferred_language if "language" in saved else None,
            "about": about, "learning": learning}
