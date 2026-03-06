from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, Enum, JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ContentType(str, enum.Enum):
    VIDEO      = "video"
    ARTICLE    = "article"
    EXERCISE   = "exercise"
    QUIZ       = "quiz"
    PROJECT    = "project"
    TUTORIAL   = "tutorial"


class DifficultyLevel(str, enum.Enum):
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED     = "advanced"


class InteractionType(str, enum.Enum):
    VIEW      = "view"        # user opened the content
    COMPLETE  = "complete"    # user finished it
    LIKE      = "like"
    DISLIKE   = "dislike"
    SKIP      = "skip"
    BOOKMARK  = "bookmark"


# ─── Content Catalog ─────────────────────────────────────────────────────────

class Content(Base):
    """Master catalog of all learning content items."""
    __tablename__ = "contents"

    id              = Column(Integer, primary_key=True, index=True)
    title           = Column(String(500), nullable=False)
    description     = Column(Text, nullable=True)
    content_type    = Column(Enum(ContentType), nullable=False)
    difficulty      = Column(Enum(DifficultyLevel), nullable=False)
    url             = Column(String(1000), nullable=True)
    thumbnail_url   = Column(String(1000), nullable=True)
    duration_mins   = Column(Float, nullable=True)       # estimated time
    language        = Column(String(50), nullable=True)   # programming language
    topics          = Column(JSON, default=list)          # ["loops", "functions", ...]
    skills_gained   = Column(JSON, default=list)          # ["debugging", "OOP", ...]
    prerequisites   = Column(JSON, default=list)          # content ids or topic names
    author          = Column(String(255), nullable=True)
    source          = Column(String(255), nullable=True)  # "YouTube", "GeeksForGeeks" …
    avg_rating      = Column(Float, default=0.0)
    total_ratings   = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)          # across all users (0-1)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    interactions    = relationship("UserContentInteraction", back_populates="content")
    recommendations = relationship("Recommendation", back_populates="content")


# ─── User × Content Interactions (Ratings Matrix) ────────────────────────────

class UserContentInteraction(Base):
    """Tracks every interaction a user has with a content item — the CF matrix."""
    __tablename__ = "user_content_interactions"
    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_user_content"),)

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_id      = Column(Integer, ForeignKey("contents.id", ondelete="CASCADE"), nullable=False)
    interaction     = Column(Enum(InteractionType), default=InteractionType.VIEW)
    rating          = Column(Float, nullable=True)        # explicit 1-5 rating
    implicit_score  = Column(Float, default=0.0)          # computed: time × completion
    time_spent_mins = Column(Float, default=0.0)
    completion_pct  = Column(Float, default=0.0)          # 0-100
    is_completed    = Column(Boolean, default=False)
    is_bookmarked   = Column(Boolean, default=False)
    interacted_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    user    = relationship("User")
    content = relationship("Content", back_populates="interactions")


# ─── AI-Generated Recommendations ────────────────────────────────────────────

class Recommendation(Base):
    """Stores the agent's output — one row per recommended content per user."""
    __tablename__ = "recommendations"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_id      = Column(Integer, ForeignKey("contents.id", ondelete="CASCADE"), nullable=False)

    # Scoring
    score           = Column(Float, default=0.0)          # final blended score 0-1
    cf_score        = Column(Float, default=0.0)          # collaborative filtering score
    cbf_score       = Column(Float, default=0.0)          # content-based filtering score
    rl_bonus        = Column(Float, default=0.0)          # RL exploration bonus

    # Agent metadata
    agent_reasoning = Column(Text, nullable=True)         # LLM explanation text
    rank            = Column(Integer, nullable=True)       # 1 = top pick
    batch_id        = Column(String(64), nullable=True)   # groups one agent run
    is_dismissed    = Column(Boolean, default=False)       # user dismissed it
    is_clicked      = Column(Boolean, default=False)
    generated_at    = Column(DateTime(timezone=True), server_default=func.now())

    user    = relationship("User")
    content = relationship("Content", back_populates="recommendations")


# ─── Agent Run Log ────────────────────────────────────────────────────────────

class AgentRunLog(Base):
    """Audit log of every Content Recommendation Agent invocation."""
    __tablename__ = "agent_run_logs"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    batch_id        = Column(String(64), unique=True, nullable=False)
    status          = Column(String(30), default="pending")  # pending/running/done/failed
    step_log        = Column(JSON, default=list)              # list of agent thought steps
    cf_candidates   = Column(Integer, default=0)
    cbf_candidates  = Column(Integer, default=0)
    final_count     = Column(Integer, default=0)
    llm_tokens_used = Column(Integer, default=0)
    duration_ms     = Column(Integer, default=0)
    error_message   = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")