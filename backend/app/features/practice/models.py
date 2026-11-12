"""A bounded Practice session: what was served, what was graded, and the wrap-up
feedback generated once when it closes. A topic run is a session with `topic` and `plan`
set: a fixed list of item types on one topic the student chose.

Also the assessment banks (MCQ, debug, theory) and each student's attempts on them."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    language         = Column(String(10), nullable=False)
    started_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(),
                              nullable=False)
    ended_at         = Column(DateTime(timezone=True), nullable=True)
    # finished, idle, language_switch or mode_switch.
    end_reason       = Column(String(16), nullable=True)
    graded_count     = Column(Integer, nullable=False, default=0, server_default="0")
    # [{"type": "mcq"|"debug"|"coding"|"theory", "id": int, "solved": bool,
    #   "graded": bool}, ...]
    served           = Column(JSON, nullable=False, default=list)
    topic            = Column(String(40), nullable=True)
    # ["theory", "coding", "mcq", ...]: the item type of each slot in a topic run.
    plan             = Column(JSON, nullable=True)
    wrap_up_seen_at  = Column(DateTime(timezone=True), nullable=True)
    # {"summary": str, "work_on_next": [str]}
    feedback         = Column(JSON, nullable=True)
    # none, ready, unavailable or blocked.
    feedback_status  = Column(String(12), nullable=False, default="none",
                              server_default="none")


class McqQuestion(Base):
    __tablename__ = "mcq_questions"

    id            = Column(Integer, primary_key=True, index=True)
    external_id   = Column(String(60), unique=True, nullable=False)
    topic         = Column(String(40), nullable=False, index=True)
    difficulty    = Column(String(10), nullable=False)
    # c, cpp or python for a question about code; any for a concept question with none.
    language      = Column(String(10), nullable=False, default="python", server_default="python")
    stem          = Column(Text, nullable=False)
    # [{"text": ..., "misconception": tag | None}, ...]
    options       = Column(JSON, nullable=False)
    answer_index  = Column(Integer, nullable=False)
    # ≤ 2 lines of Python whose output is exactly the correct option's text, for a Python
    # question whose stem prints nothing; empty otherwise. Never serialised.
    verify_code   = Column(Text, nullable=False)
    explanations  = Column(JSON, default=list)
    is_diagnostic = Column(Boolean, nullable=False, default=False)
    reviewed      = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class McqAttempt(Base):
    __tablename__ = "mcq_attempts"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    question_id  = Column(Integer, ForeignKey("mcq_questions.id", ondelete="CASCADE"),
                          nullable=False)
    chosen_index = Column(Integer, nullable=False)
    correct      = Column(Boolean, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class DebugChallenge(Base):
    __tablename__ = "debug_challenges"

    id          = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(60), unique=True, nullable=False)
    problem_id  = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"),
                         nullable=False)
    topic       = Column(String(40), nullable=False, index=True)
    difficulty  = Column(String(10), nullable=False)
    language    = Column(String(20), nullable=False)
    statement   = Column(Text, nullable=False)
    buggy_code  = Column(Text, nullable=False)
    # Kept only to re-verify the challenge; never serialised to a client.
    fixed_code  = Column(Text, nullable=False)
    bug_type    = Column(String(40), nullable=False)
    reviewed    = Column(Boolean, nullable=False, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class DebugAttempt(Base):
    __tablename__ = "debug_attempts"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    challenge_id   = Column(Integer, ForeignKey("debug_challenges.id", ondelete="CASCADE"),
                            nullable=False)
    submitted_code = Column(Text, nullable=False)
    tests_passed   = Column(Integer, nullable=False, default=0)
    tests_total    = Column(Integer, nullable=False, default=0)
    fixed          = Column(Boolean, nullable=False, default=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())


class TheoryQuestion(Base):
    __tablename__ = "theory_questions"

    id           = Column(Integer, primary_key=True, index=True)
    external_id  = Column(String(60), unique=True, nullable=False)
    topic        = Column(String(40), nullable=False, index=True)
    difficulty   = Column(String(10), nullable=False)
    language     = Column(String(10), nullable=False)
    question     = Column(Text, nullable=False)
    # Never serialised before the student has answered.
    model_answer = Column(Text, nullable=False)
    key_points   = Column(JSON, nullable=False)
    reviewed     = Column(Boolean, nullable=False, default=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class TheoryAttempt(Base):
    __tablename__ = "theory_attempts"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    question_id    = Column(Integer, ForeignKey("theory_questions.id", ondelete="CASCADE"),
                            nullable=False)
    answer         = Column(Text, nullable=False)
    points_present = Column(JSON, nullable=False)
    score          = Column(Float, nullable=False)
    feedback       = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
