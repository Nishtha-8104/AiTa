"""One row per hint shown (or blocked by the Guardrail), from practice or from chat."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class HintEvent(Base):
    __tablename__ = "hint_events"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    problem_id    = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    evaluation_id = Column(Integer, ForeignKey("code_evaluations.id", ondelete="SET NULL"),
                           nullable=True)
    level         = Column(Integer, nullable=False)
    was_blocked   = Column(Boolean, nullable=False, default=False)
    source        = Column(String(16), nullable=False, server_default="practice")
    session_id    = Column(Integer, ForeignKey("practice_sessions.id", ondelete="SET NULL"),
                           nullable=True, index=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
