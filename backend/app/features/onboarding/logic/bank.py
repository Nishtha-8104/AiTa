"""Reviewed diagnostic items for a student's language, and the key-free payload sent
to the browser."""

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.features.grading.models import Language
from app.features.onboarding.logic.types import BankIndex, ItemRef
from app.features.onboarding.models import DiagnosticItem

LANGUAGES = {"c": Language.C, "cpp": Language.CPP, "python": Language.PYTHON}
SHARED = "any"


def language_of(value: str) -> Language:
    if value not in LANGUAGES:
        raise ValueError(f"unsupported diagnostic language: {value!r}")
    return LANGUAGES[value]


def _for_language(language: str):
    language_of(language)
    return or_(DiagnosticItem.language == language,
               and_(DiagnosticItem.kind == "theory", DiagnosticItem.language == SHARED))


def bank_index(db: Session, language: str) -> BankIndex:
    rows = (db.query(DiagnosticItem.topic, DiagnosticItem.kind, DiagnosticItem.difficulty)
            .filter(DiagnosticItem.reviewed.is_(True), _for_language(language))
            .distinct().all())
    return frozenset((topic, kind, difficulty) for topic, kind, difficulty in rows)


def fetch(db: Session, ref: ItemRef, language: str,
          exclude_ids: set[int]) -> DiagnosticItem | None:
    query = db.query(DiagnosticItem).filter(
        DiagnosticItem.reviewed.is_(True),
        DiagnosticItem.topic == ref.topic,
        DiagnosticItem.kind == ref.kind,
        DiagnosticItem.difficulty == ref.difficulty,
        _for_language(language),
    )
    if exclude_ids:
        query = query.filter(DiagnosticItem.id.notin_(exclude_ids))
    candidates = query.order_by(DiagnosticItem.id).all()
    return next((item for item in candidates if item.language == language),
                candidates[0] if candidates else None)


def payload(item: DiagnosticItem) -> dict:
    return {"id": item.id, "kind": item.kind, "topic": item.topic,
            "difficulty": item.difficulty, "language": item.language, "body": item.body}
