"""Onboarding state: background preferences, the resumable onboarding record, the
diagnostic item bank and each student's graded diagnostic responses."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class LearnerPreferences(Base):
    __tablename__ = "learner_preferences"

    user_id           = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                               primary_key=True)
    program           = Column(String(100), nullable=True)
    goal              = Column(String(40), nullable=False)
    explanation_style = Column(String(20), nullable=False)
    example_order     = Column(String(20), nullable=False)
    chat_language     = Column(String(20), nullable=False)
    hours_per_week    = Column(String(20), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(),
                               onupdate=func.now())


class OnboardingRecord(Base):
    __tablename__ = "onboarding_records"

    user_id               = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                                   primary_key=True)
    current_step          = Column(String(12), nullable=False, default="welcome")
    started_at            = Column(DateTime(timezone=True), server_default=func.now())
    last_step_at          = Column(DateTime(timezone=True), nullable=True)
    finished_at           = Column(DateTime(timezone=True), nullable=True)
    diagnostic_started_at = Column(DateTime(timezone=True), nullable=True)
    current_item_id       = Column(Integer,
                                   ForeignKey("diagnostic_items.id", ondelete="SET NULL"),
                                   nullable=True)
    step_durations        = Column(JSON, default=dict)
    self_rating           = Column(Integer, nullable=True)
    title                 = Column(String(80), nullable=True)
    concept_level         = Column(String(10), nullable=False, default="unknown")
    language_locked_at    = Column(DateTime(timezone=True), nullable=True)
    # The language the onboarding check ran in; preferred_language can change later.
    language              = Column(String(10), nullable=True)
    seeds                 = Column(JSON, default=dict)


class LanguageCheck(Base):
    """The code-only check taken on switching to a language never used before. Its
    fields mirror the matching OnboardingRecord ones so the same walk drives both."""
    __tablename__ = "language_checks"

    user_id               = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                                   primary_key=True)
    language              = Column(String(10), primary_key=True)
    started_at            = Column(DateTime(timezone=True), server_default=func.now())
    diagnostic_started_at = Column(DateTime(timezone=True), nullable=True)
    current_item_id       = Column(Integer,
                                   ForeignKey("diagnostic_items.id", ondelete="SET NULL"),
                                   nullable=True)
    finished_at           = Column(DateTime(timezone=True), nullable=True)
    seeds                 = Column(JSON, default=dict)
    title                 = Column(String(80), nullable=True)


class DiagnosticItem(Base):
    __tablename__ = "diagnostic_items"
    __table_args__ = (
        Index("ix_diagnostic_items_lookup", "topic", "kind", "difficulty", "language", "reviewed"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(80), unique=True, nullable=False)
    kind        = Column(String(20), nullable=False)
    topic       = Column(String(40), nullable=False)
    tier        = Column(Integer, nullable=False)
    difficulty  = Column(String(10), nullable=False)
    language    = Column(String(10), nullable=False)
    concept_key = Column(String(60), nullable=False)
    body        = Column(JSON, nullable=False)
    # The answer key; never serialised to a client.
    key         = Column(JSON, nullable=False)
    reviewed    = Column(Boolean, nullable=False, default=False)


class DiagnosticResponse(Base):
    __tablename__ = "diagnostic_responses"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_diagnostic_response_user_item"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    item_id    = Column(Integer, ForeignKey("diagnostic_items.id", ondelete="CASCADE"),
                        nullable=False)
    order      = Column(Integer, nullable=False)
    phase      = Column(String(12), nullable=False)
    # The check this answer belongs to: the onboarding language or a re-check's.
    language   = Column(String(10), nullable=False)
    answer     = Column(JSON, nullable=False)
    score      = Column(Float, nullable=True)
    graded_by  = Column(String(10), nullable=False)
    feedback   = Column(Text, nullable=True)
    reveal     = Column(JSON, nullable=True)
    ms_taken   = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
