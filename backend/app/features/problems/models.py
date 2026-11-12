import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.features.grading.models import Language


def _enum(cls):
    return Enum(cls, values_callable=lambda x: [e.value for e in x])


class ProblemSource(str, enum.Enum):
    STUDENT = "student"
    MBPP = "mbpp"
    DSA = "dsa"
    GENERATED = "generated"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class IOMode(str, enum.Enum):
    STDIN_STDOUT = "stdin_stdout"


class TestCaseKind(str, enum.Enum):
    SAMPLE = "sample"
    NORMAL = "normal"
    EDGE = "edge"


class TestCaseOrigin(str, enum.Enum):
    PROBLEM_SAMPLE = "problem_sample"
    CROSS_CHECKED = "cross_checked"
    REFERENCE_ONLY = "reference_only"


class ReferenceStatus(str, enum.Enum):
    VALIDATED = "validated"
    FAILED = "failed"


class EvalMode(str, enum.Enum):
    VERIFIED = "verified"
    REVIEW = "review"


class VerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class ExecRole(str, enum.Enum):
    STUDENT = "student"
    REFERENCE = "reference"


class Problem(Base):
    """A problem statement, shared across every student who submits against it."""
    __tablename__ = "problems"

    id                 = Column(Integer, primary_key=True, index=True)
    source             = Column(_enum(ProblemSource), nullable=False)
    external_id        = Column(String(100), nullable=True)
    title              = Column(String(120), nullable=True)
    statement          = Column(Text, nullable=False)
    statement_hash     = Column(String(64), nullable=False, unique=True, index=True)
    constraints        = Column(Text, nullable=True)
    topic              = Column(String(100), nullable=True)
    difficulty         = Column(_enum(Difficulty), nullable=True)
    io_mode            = Column(_enum(IOMode), nullable=False, default=IOMode.STDIN_STDOUT)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                                nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())

    test_cases = relationship("TestCase", back_populates="problem",
                              cascade="all, delete-orphan", order_by="TestCase.ordinal")
    references = relationship("ProblemReference", back_populates="problem",
                              cascade="all, delete-orphan",
                              order_by="ProblemReference.id")


class ProblemReference(Base):
    """A generated reference solution and whether it survived validation."""
    __tablename__ = "problem_references"

    id         = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    language   = Column(_enum(Language), nullable=False)
    source     = Column(Text, nullable=False)
    status     = Column(_enum(ReferenceStatus), nullable=False)
    attempts   = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    problem = relationship("Problem", back_populates="references")


class TestCase(Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        Index("ix_test_cases_problem_stdin", "problem_id", "stdin_hash", unique=True),
    )

    id              = Column(Integer, primary_key=True, index=True)
    problem_id      = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    kind            = Column(_enum(TestCaseKind), nullable=False)
    stdin           = Column(Text, nullable=False, default="")
    expected_stdout = Column(Text, nullable=False, default="")
    stdin_hash      = Column(String(64), nullable=False)
    origin          = Column(_enum(TestCaseOrigin), nullable=False)
    rationale       = Column(Text, nullable=True)
    ordinal         = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    problem = relationship("Problem", back_populates="test_cases")


class ExecutionResult(Base):
    __tablename__ = "execution_results"

    id            = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("code_evaluations.id", ondelete="CASCADE"),
                           nullable=True, index=True)
    test_case_id  = Column(Integer, ForeignKey("test_cases.id", ondelete="SET NULL"),
                           nullable=True)
    role          = Column(_enum(ExecRole), nullable=False)
    status        = Column(String(30), nullable=False)
    stdout        = Column(Text, default="")
    stderr        = Column(Text, default="")
    truncated     = Column(Boolean, default=False)
    time_ms       = Column(Integer, default=0)
    memory_kb     = Column(Integer, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
