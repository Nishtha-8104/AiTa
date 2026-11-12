"""The learner model: evidence events and per-topic mastery.
Only the Profiling Agent writes `learning_events` and `topic_mastery`."""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.core.database import Base


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    kind            = Column(String(20), nullable=False)
    item_id         = Column(Integer, nullable=True)
    topic           = Column(String(40), nullable=True, index=True)
    raw_topic       = Column(String(100), nullable=True)
    score           = Column(Float, nullable=False)
    weight          = Column(Float, nullable=False)
    hint_level_used = Column(Integer, nullable=False, default=0)
    misconceptions  = Column(JSON, default=list)
    mastery_before  = Column(Float, nullable=True)
    mastery_after   = Column(Float, nullable=True)
    source_ref      = Column(String(60), nullable=True)
    # The language the evidence happened in: c, cpp or python.
    language        = Column(String(10), nullable=False)
    session_id      = Column(Integer, ForeignKey("practice_sessions.id", ondelete="SET NULL"),
                             nullable=True, index=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    user_id        = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                            primary_key=True)
    topic          = Column(String(40), primary_key=True)
    language       = Column(String(10), primary_key=True)
    mastery        = Column(Float, nullable=False)
    evidence_count = Column(Integer, nullable=False, default=0)
    last_event_at  = Column(DateTime(timezone=True), nullable=True)
