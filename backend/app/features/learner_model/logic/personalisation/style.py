"""How a student likes to learn, from onboarding, as one line for the agents' prompts."""

from sqlalchemy.orm import Session

from app.features.onboarding.models import LearnerPreferences, OnboardingRecord

DEFAULT_CHAT_LANGUAGE = "auto"
STYLE = {"step_by_step": "step-by-step", "short": "short"}
ORDER = {"examples_first": "examples first", "concept_first": "concept first"}
GOAL = {"course": "college course/exams", "placements": "placements",
        "competitive": "competitive programming", "hobby": "learning for fun"}
HOURS = {"lt2": "under 2 hours", "2to5": "2–5 hours", "5to10": "5–10 hours",
         "10plus": "10+ hours"}
CONCEPT = {"low": "Concept understanding: low, so explain ideas from the basics.",
           "medium": "Concept understanding: medium.",
           "high": "Concept understanding: high, so keep explanations brief."}


def style_line(db: Session, user_id: int) -> str:
    prefs = db.get(LearnerPreferences, user_id)
    record = db.get(OnboardingRecord, user_id)
    parts = []
    if prefs is not None:
        hinglish = ", Hinglish OK." if prefs.chat_language == "hinglish" else "."
        parts.append(f"Prefers {STYLE.get(prefs.explanation_style, prefs.explanation_style)} "
                     f"explanations, {ORDER.get(prefs.example_order, prefs.example_order)}"
                     f"{hinglish}")
    if record is not None and record.concept_level in CONCEPT:
        parts.append(CONCEPT[record.concept_level])
    if prefs is not None:
        parts += [f"Goal: {GOAL.get(prefs.goal, prefs.goal)}.",
                  f"About {HOURS.get(prefs.hours_per_week, prefs.hours_per_week)} a week."]
    return " ".join(parts)


def chat_language(db: Session, user_id: int) -> str:
    prefs = db.get(LearnerPreferences, user_id)
    return prefs.chat_language if prefs is not None else DEFAULT_CHAT_LANGUAGE
