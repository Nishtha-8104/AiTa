from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, Enum, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
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

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title           = Column(String(300), nullable=True)        # e.g. "Fibonacci function"
    language        = Column(Enum(Language, values_callable=lambda x: [e.value for e in x]), nullable=False)
    code            = Column(Text, nullable=False)
    problem_context = Column(Text, nullable=True)              # optional problem statement
    expected_output = Column(Text, nullable=True)              # optional expected output

    # Eval status
    status          = Column(Enum(EvalStatus, values_callable=lambda x: [e.value for e in x]), default=EvalStatus.PENDING)
    eval_count      = Column(Integer, default=0)               # how many times re-evaluated

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

    id              = Column(Integer, primary_key=True, index=True)
    submission_id   = Column(Integer, ForeignKey("code_submissions.id", ondelete="CASCADE"))
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    # ── Overall scores (0-100) ────────────────────────────────────────────────
    overall_score       = Column(Float, default=0.0)
    correctness_score   = Column(Float, default=0.0)   # logic / output correctness
    quality_score       = Column(Float, default=0.0)   # naming, structure, DRY
    efficiency_score    = Column(Float, default=0.0)   # time/space complexity
    security_score      = Column(Float, default=0.0)   # injection, edge cases
    style_score         = Column(Float, default=0.0)   # formatting, conventions
    documentation_score = Column(Float, default=0.0)   # comments, docstrings

    # ── Static analysis output ─────────────────────────────────────────────────
    issues              = Column(JSON, default=list)   # list of Issue dicts
    # Issue shape: {id, line, severity, category, message, suggestion}

    # ── Complexity analysis ────────────────────────────────────────────────────
    time_complexity     = Column(String(30), nullable=True)   # "O(n)", "O(n log n)"
    space_complexity    = Column(String(30), nullable=True)
    cyclomatic_complexity = Column(Integer, nullable=True)    # # of independent paths
    lines_of_code       = Column(Integer, nullable=True)
    comment_ratio       = Column(Float, nullable=True)        # 0.0 – 1.0

    # ── LLM-generated deep analysis ───────────────────────────────────────────
    summary             = Column(Text, nullable=True)         # 2-3 sentence overall verdict
    detailed_feedback   = Column(Text, nullable=True)         # full markdown feedback
    corrected_code      = Column(Text, nullable=True)         # improved version
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

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    submission_id   = Column(Integer, ForeignKey("code_submissions.id", ondelete="CASCADE"))
    evaluation_id   = Column(Integer, ForeignKey("code_evaluations.id", ondelete="CASCADE"))
    overall_score   = Column(Float, default=0.0)
    language        = Column(Enum(Language, values_callable=lambda x: [e.value for e in x]), nullable=False)
    eval_number     = Column(Integer, default=1)              # 1st, 2nd, 3rd eval
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")