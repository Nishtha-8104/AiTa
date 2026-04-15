from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, Enum, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class FeedbackType(str, enum.Enum):
    CODE_REVIEW    = "code_review"
    LEARNING_RECAP = "learning_recap"
    COMBINED       = "combined"


class FeedbackTone(str, enum.Enum):
    ENCOURAGING  = "encouraging"
    CONSTRUCTIVE = "constructive"
    CHALLENGING  = "challenging"


class FeedbackReport(Base):
    """
    One Feedback Agent report synthesised from Code Eval and/or Content Player.
    Persisted per user so they can review their full feedback history.

    ForeignKey strategy:
      - user_id         CASCADE  — delete user → delete all their feedback
      - evaluation_id   SET NULL — delete a code eval → keep feedback, lose the link
      - cp_session_id   SET NULL — delete a session  → keep feedback, lose the link
    """
    __tablename__ = "feedback_reports"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id",                   ondelete="CASCADE"),  nullable=False)
    evaluation_id = Column(Integer, ForeignKey("code_evaluations.id",        ondelete="SET NULL"), nullable=True)
    cp_session_id = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="SET NULL"), nullable=True)

    # values_callable ensures SQLAlchemy writes lowercase values ("code_review")
    # not the Python member name ("CODE_REVIEW") — prevents the ENUM mismatch bug
    feedback_type = Column(
        Enum(FeedbackType, values_callable=lambda x: [e.value for e in x]),
        default=FeedbackType.CODE_REVIEW,
        nullable=False,
    )
    tone = Column(
        Enum(FeedbackTone, values_callable=lambda x: [e.value for e in x]),
        default=FeedbackTone.ENCOURAGING,
        nullable=False,
    )

    # ── LLM-synthesised feedback sections ─────────────────────────────────────
    headline        = Column(String(300), nullable=True)   # one-line verdict
    summary         = Column(Text,        nullable=True)   # 3-4 sentence narrative
    strengths       = Column(JSON, default=list)           # ["Good use of recursion", ...]
    errors          = Column(JSON, default=list)           # specific mistakes found
    misconceptions  = Column(JSON, default=list)           # conceptual misunderstandings
    action_items    = Column(JSON, default=list)           # prioritised "do this next" list
    concept_map     = Column(JSON, default=dict)           # {"recursion": 0.4, "loops": 0.8}
    next_topics     = Column(JSON, default=list)           # recommended topics to study next
    motivational    = Column(Text, nullable=True)          # personalised encouragement line

    # ── What was written back to LearningProfile ──────────────────────────────
    profile_updates = Column(JSON, default=dict)           # {"weak_areas": [...], ...}

    # ── Agent run metadata ─────────────────────────────────────────────────────
    agent_steps   = Column(JSON,    default=list)          # thought log from pipeline
    tokens_used   = Column(Integer, default=0)
    latency_ms    = Column(Integer, default=0)
    is_read       = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")