# from sqlalchemy import (
#     Column, Integer, String, Boolean, DateTime, Text,
#     Float, Enum, JSON, ForeignKey
# )
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func
# from app.core.database import Base
# import enum


# class SessionMode(str, enum.Enum):
#     QA          = "qa"           # General Q&A / concept explanation
#     CODE_HELP   = "code_help"    # Debug / explain / fix code
#     BRAINSTORM  = "brainstorm"   # Brainstorming ideas / approaches
#     QUIZ        = "quiz"         # Agent quizzes the student
#     WALKTHROUGH = "walkthrough"  # Step-by-step concept walkthrough


# class MessageRole(str, enum.Enum):
#     USER      = "user"
#     ASSISTANT = "assistant"
#     SYSTEM    = "system"


# class ContentPlayerSession(Base):
#     """One learning session between a student and the Content Player Agent."""
#     __tablename__ = "content_player_sessions"

#     id            = Column(Integer, primary_key=True, index=True)
#     user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     title         = Column(String(500), nullable=True)       # auto-generated from first msg
#     mode          = Column(Enum(SessionMode), default=SessionMode.QA)
#     language      = Column(String(50), nullable=True)        # programming language context
#     topic         = Column(String(255), nullable=True)       # detected topic
#     is_active     = Column(Boolean, default=True)
#     is_archived   = Column(Boolean, default=False)

#     # Agent metadata
#     total_messages      = Column(Integer, default=0)
#     total_tokens_used   = Column(Integer, default=0)
#     concepts_covered    = Column(JSON, default=list)         # extracted concepts from session
#     agent_model         = Column(String(100), default="llama-3.3-70b-versatile")

#     # Learning signals (used by User Profiling Agent)
#     confusion_detected  = Column(Boolean, default=False)     # agent flagged confusion
#     mastery_signals     = Column(JSON, default=list)         # topics student understood well
#     weak_signals        = Column(JSON, default=list)         # topics student struggled with

#     created_at    = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at    = Column(DateTime(timezone=True), onupdate=func.now())
#     last_message_at = Column(DateTime(timezone=True), nullable=True)

#     user     = relationship("User")
#     messages = relationship("ContentPlayerMessage", back_populates="session",
#                             order_by="ContentPlayerMessage.created_at",
#                             cascade="all, delete-orphan")


# class ContentPlayerMessage(Base):
#     """Individual message in a Content Player session."""
#     __tablename__ = "content_player_messages"

#     id           = Column(Integer, primary_key=True, index=True)
#     session_id   = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"))
#     user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
#     role         = Column(Enum(MessageRole), nullable=False)
#     content      = Column(Text, nullable=False)

#     # Code context (if user submitted code)
#     has_code     = Column(Boolean, default=False)
#     code_snippet = Column(Text, nullable=True)
#     code_language= Column(String(50), nullable=True)
#     error_message= Column(Text, nullable=True)      # compiler/runtime error attached

#     # Agent analysis metadata
#     tokens_used  = Column(Integer, default=0)
#     latency_ms   = Column(Integer, default=0)
#     model_used   = Column(String(100), nullable=True)

#     # Feedback
#     was_helpful  = Column(Boolean, nullable=True)   # thumbs up/down from user

#     created_at   = Column(DateTime(timezone=True), server_default=func.now())

#     session = relationship("ContentPlayerSession", back_populates="messages")
#     user    = relationship("User")


# class CodeSnapshot(Base):
#     """Stores code submitted during a session for later analysis."""
#     __tablename__ = "code_snapshots"

#     id           = Column(Integer, primary_key=True, index=True)
#     session_id   = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"))
#     user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
#     language     = Column(String(50), nullable=False)
#     code         = Column(Text, nullable=False)
#     error        = Column(Text, nullable=True)
#     agent_feedback = Column(Text, nullable=True)    # last agent response about this code
#     created_at   = Column(DateTime(timezone=True), server_default=func.now())

#     session = relationship("ContentPlayerSession")
#     user    = relationship("User")


"""
models/content_player.py — UPDATED with difficulty column in ContentPlayerSession
Copy to: backend/app/models/content_player.py

MIGRATION SQL (run in pgAdmin):
    ALTER TABLE content_player_sessions ADD COLUMN IF NOT EXISTS difficulty VARCHAR(20) DEFAULT 'medium';
"""

# from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
# from sqlalchemy.orm import relationship
# from datetime import datetime
# from app.core.database import Base


# class ContentPlayerSession(Base):
#     __tablename__ = "content_player_sessions"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#     mode = Column(String(30), nullable=False)
#     topic = Column(String(255), nullable=False)
#     language = Column(String(50), default="python")
#     difficulty = Column(String(20), default="medium")  # ← NEW: easy | medium | hard | expert

#     concepts_covered = Column(JSON, default=list)
#     mastery_signals = Column(JSON, default=list)
#     weak_signals = Column(JSON, default=list)
#     confusion_detected = Column(Boolean, default=False)
#     total_tokens_used = Column(Integer, default=0)
#     is_archived = Column(Boolean, default=False)

#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     user = relationship("User", back_populates="content_player_sessions")
#     messages = relationship("ContentPlayerMessage", back_populates="session", cascade="all, delete-orphan")
#     content_player_sessions = relationship("ContentPlayerSession", back_populates="user")


# class ContentPlayerMessage(Base):
#     __tablename__ = "content_player_messages"

#     id = Column(Integer, primary_key=True, index=True)
#     session_id = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"), nullable=False)
#     role = Column(String(20), nullable=False)  # user | assistant | system
#     content = Column(Text, nullable=False)
#     code_snippet = Column(Text, nullable=True)
#     agent_metadata = Column(Text, nullable=True)  # JSON string of hidden metadata
#     was_helpful = Column(Boolean, nullable=True)  # thumb feedback

#     created_at = Column(DateTime, default=datetime.utcnow)

#     session = relationship("ContentPlayerSession", back_populates="messages")


# class CodeSnapshot(Base):
#     __tablename__ = "code_snapshots"

#     id = Column(Integer, primary_key=True, index=True)
#     session_id = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"))
#     code = Column(Text, nullable=False)
#     error = Column(Text, nullable=True)
#     agent_feedback = Column(Text, nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow)




from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, Enum, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class SessionMode(str, enum.Enum):
    QA          = "qa"
    CODE_HELP   = "code_help"
    BRAINSTORM  = "brainstorm"
    QUIZ        = "quiz"
    WALKTHROUGH = "walkthrough"


class MessageRole(str, enum.Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"


class ContentPlayerSession(Base):
    """One learning session between a student and the Content Player Agent."""
    __tablename__ = "content_player_sessions"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title           = Column(String(500), nullable=True)
    mode            = Column(String(30), default="qa")
    language        = Column(String(50),  nullable=True)
    topic           = Column(String(255), nullable=True)
    difficulty      = Column(String(20),  default="medium")   # easy / medium / hard
    is_active       = Column(Boolean, default=True)
    is_archived     = Column(Boolean, default=False)

    # Agent metadata
    total_messages    = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    concepts_covered  = Column(JSON, default=list)
    agent_model       = Column(String(100), default="llama-3.3-70b-versatile")

    # Learning signals
    confusion_detected = Column(Boolean, default=False)
    mastery_signals    = Column(JSON, default=list)
    weak_signals       = Column(JSON, default=list)

    # Question mastery tracking
    solved_questions       = Column(JSON, default=list)   # list of question title hashes marked solved
    consecutive_easy_solves = Column(Integer, default=0)  # streak of easy solves → triggers difficulty bump

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user     = relationship("User", back_populates="content_player_sessions")
    # messages → points to ContentPlayerMessage (different table, has FK back here)
    messages = relationship(
        "ContentPlayerMessage",
        back_populates="session",
        order_by="ContentPlayerMessage.created_at",
        cascade="all, delete-orphan",
    )


class ContentPlayerMessage(Base):
    """Individual message in a Content Player session."""
    __tablename__ = "content_player_messages"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),                   nullable=False)
    role         = Column(String(20), nullable=False)
    content      = Column(Text, nullable=False)

    has_code      = Column(Boolean, default=False)
    code_snippet  = Column(Text,    nullable=True)
    code_language = Column(String(50), nullable=True)
    error_message = Column(Text,    nullable=True)

    tokens_used = Column(Integer, default=0)
    latency_ms  = Column(Integer, default=0)
    model_used  = Column(String(100), nullable=True)
    was_helpful = Column(Boolean, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # session → points back to ContentPlayerSession (correct — FK exists above)
    session = relationship("ContentPlayerSession", back_populates="messages")
    user    = relationship("User")


class CodeSnapshot(Base):
    """Stores code submitted during a session for later analysis."""
    __tablename__ = "code_snapshots"

    id             = Column(Integer, primary_key=True, index=True)
    session_id     = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id        = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),                   nullable=False)
    language       = Column(String(50), nullable=False)
    code           = Column(Text, nullable=False)
    error          = Column(Text, nullable=True)
    agent_feedback = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # session → points to ContentPlayerSession (FK exists above — this is valid)
    session = relationship("ContentPlayerSession")
    user    = relationship("User")