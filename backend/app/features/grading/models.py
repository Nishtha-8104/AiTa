"""Grading tables: code submissions, their evaluations and each student's evaluation
history."""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, Enum, Index, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import false
from app.core.database import Base
import enum


class Language(str, enum.Enum):
    PYTHON     = "python"
    JAVASCRIPT = "javascript"
    JAVA       = "java"
    CPP        = "cpp"
    C          = "c"
    TYPESCRIPT = "typescript"
    GO         = "go"
    RUST       = "rust"
    SQL        = "sql"


class EvalStatus(str, enum.Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"


class SeverityLevel(str, enum.Enum):
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


class CodeSubmission(Base):
    """A single code submission from a student for evaluation."""
    __tablename__ = "code_submissions"
    __table_args__ = (
        Index("ix_code_submissions_user_created", "user_id", "created_at"),
        Index("ix_code_submissions_problem", "problem_id"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title           = Column(String(300), nullable=True)        # e.g. "Fibonacci function"
    language        = Column(Enum(Language, values_callable=lambda x: [e.value for e in x]), nullable=False)
    code            = Column(Text, nullable=False)
    problem_context = Column(Text, nullable=True)              # optional problem statement
    expected_output = Column(Text, nullable=True)              # a bare output string, no paired stdin

    problem_id      = Column(Integer, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True)
    from_bank       = Column(Boolean, nullable=False, default=False, server_default=false())

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    user            = relationship("User")
    evaluations     = relationship("CodeEvaluation", back_populates="submission",
                                   order_by="CodeEvaluation.created_at.desc()",
                                   cascade="all, delete-orphan")


class CodeEvaluation(Base):
    """
    One full evaluation result produced by the Code Evaluation Agent.
    Multiple evaluations can exist per submission (re-evaluate after fix).
    """
    __tablename__ = "code_evaluations"
    __table_args__ = (
        Index("ix_code_evaluations_user_created", "user_id", "created_at"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    submission_id   = Column(Integer, ForeignKey("code_submissions.id", ondelete="CASCADE"))
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    # ── Scores (0-100). correctness is NULL when it could not be measured. ────
    overall_score       = Column(Float, default=0.0)
    correctness_score   = Column(Float, nullable=True)  # measured pass rate, never guessed
    complexity_score    = Column(Float, default=0.0)    # lizard: CCN, length, params
    efficiency_score    = Column(Float, default=0.0)    # Big-O band + measured wall time
    style_score         = Column(Float, default=0.0)    # formatting, conventions

    # ── Verification ──────────────────────────────────────────────────────────
    mode                = Column(String(20), default="verified")
    verification_status = Column(String(20), default="unverified")
    unverified_reason   = Column(String(60), nullable=True)
    tests_total         = Column(Integer, default=0)
    tests_passed        = Column(Integer, default=0)
    status              = Column(String(20), default="pending")
    attempt_number      = Column(Integer, default=1)

    # ── Static analysis output ─────────────────────────────────────────────────
    issues              = Column(JSON, default=list)   # list of Issue dicts
    # Issue shape: {id, line, severity, category, message, suggestion}

    # ── Complexity analysis ────────────────────────────────────────────────────
    # Models write prose here ("O(n) per test case, where n is..."), not just a
    # band, and a 30-char column turned that into a 500 after a full evaluation.
    time_complexity     = Column(String(120), nullable=True)
    space_complexity    = Column(String(120), nullable=True)
    cyclomatic_complexity = Column(Integer, nullable=True)    # # of independent paths
    lines_of_code       = Column(Integer, nullable=True)
    comment_ratio       = Column(Float, nullable=True)        # 0.0 – 1.0

    # ── LLM-generated deep analysis ───────────────────────────────────────────
    summary             = Column(Text, nullable=True)         # 2-3 sentence overall verdict
    detailed_feedback   = Column(Text, nullable=True)         # full markdown feedback
    key_improvements    = Column(JSON, default=list)          # ["Use list comprehension", ...]
    learning_points     = Column(JSON, default=list)          # concepts student should revisit
    best_practices_used = Column(JSON, default=list)          # good things the student did
    anti_patterns       = Column(JSON, default=list)          # patterns to avoid
    suggested_resources = Column(JSON, default=list)          # topic links to learn more

    # ── Agent metadata ─────────────────────────────────────────────────────────
    agent_steps         = Column(JSON, default=list)          # thought log
    tokens_used         = Column(Integer, default=0)
    latency_ms          = Column(Integer, default=0)
    model_used          = Column(String(100), nullable=True)
    static_tool_used    = Column(String(100), nullable=True)  # "regex_heuristics"

    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    submission  = relationship("CodeSubmission", back_populates="evaluations")
    user        = relationship("User")


class EvalHistoryEntry(Base):
    """Tracks score progression across re-evaluations for a user's code."""
    __tablename__ = "eval_history"
    __table_args__ = (
        Index("ix_eval_history_user_created", "user_id", "created_at"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    submission_id   = Column(Integer, ForeignKey("code_submissions.id", ondelete="CASCADE"))
    evaluation_id   = Column(Integer, ForeignKey("code_evaluations.id", ondelete="CASCADE"))
    overall_score   = Column(Float, default=0.0)
    language        = Column(Enum(Language, values_callable=lambda x: [e.value for e in x]), nullable=False)
    eval_number     = Column(Integer, default=1)              # 1st, 2nd, 3rd eval
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")