"""The award ledger. Only the Gamification Engine writes it, and every row points at
the verified learning event that earned it."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class GamificationAward(Base):
    __tablename__ = "gamification_awards"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_award_user_key"),)

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                               nullable=False, index=True)
    learning_event_id = Column(Integer, ForeignKey("learning_events.id", ondelete="CASCADE"),
                               nullable=False)
    kind              = Column(String(12), nullable=False)
    code              = Column(String(40), nullable=False)
    dedupe_key        = Column(String(80), nullable=False)
    points            = Column(Integer, nullable=False, default=0)
    message           = Column(String(200), nullable=False)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
