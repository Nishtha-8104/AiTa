from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    Float, Enum, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class SessionMode(str, enum.Enum):
    QA          = "qa"           # General Q&A / concept explanation
    CODE_HELP   = "code_help"    # Debug / explain / fix code
    BRAINSTORM  = "brainstorm"   # Brainstorming ideas / approaches
    QUIZ        = "quiz"         # Agent quizzes the student
    WALKTHROUGH = "walkthrough"  # Step-by-step concept walkthrough


class MessageRole(str, enum.Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"


class ContentPlayerSession(Base):
    """One learning session between a student and the Content Player Agent."""
    __tablename__ = "content_player_sessions"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title         = Column(String(500), nullable=True)       # auto-generated from first msg
    mode          = Column(Enum(SessionMode), default=SessionMode.QA)
    language      = Column(String(50), nullable=True)        # programming language context
    topic         = Column(String(255), nullable=True)       # detected topic
    is_active     = Column(Boolean, default=True)
    is_archived   = Column(Boolean, default=False)

    # Agent metadata
    total_messages      = Column(Integer, default=0)
    total_tokens_used   = Column(Integer, default=0)
    concepts_covered    = Column(JSON, default=list)         # extracted concepts from session
    agent_model         = Column(String(100), default="llama-3.3-70b-versatile")

    # Learning signals (used by User Profiling Agent)
    confusion_detected  = Column(Boolean, default=False)     # agent flagged confusion
    mastery_signals     = Column(JSON, default=list)         # topics student understood well
    weak_signals        = Column(JSON, default=list)         # topics student struggled with

    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    user     = relationship("User")
    messages = relationship("ContentPlayerMessage", back_populates="session",
                            order_by="ContentPlayerMessage.created_at",
                            cascade="all, delete-orphan")


class ContentPlayerMessage(Base):
    """Individual message in a Content Player session."""
    __tablename__ = "content_player_messages"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"))
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    role         = Column(Enum(MessageRole), nullable=False)
    content      = Column(Text, nullable=False)

    # Code context (if user submitted code)
    has_code     = Column(Boolean, default=False)
    code_snippet = Column(Text, nullable=True)
    code_language= Column(String(50), nullable=True)
    error_message= Column(Text, nullable=True)      # compiler/runtime error attached

    # Agent analysis metadata
    tokens_used  = Column(Integer, default=0)
    latency_ms   = Column(Integer, default=0)
    model_used   = Column(String(100), nullable=True)

    # Feedback
    was_helpful  = Column(Boolean, nullable=True)   # thumbs up/down from user

    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ContentPlayerSession", back_populates="messages")
    user    = relationship("User")


class CodeSnapshot(Base):
    """Stores code submitted during a session for later analysis."""
    __tablename__ = "code_snapshots"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(Integer, ForeignKey("content_player_sessions.id", ondelete="CASCADE"))
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    language     = Column(String(50), nullable=False)
    code         = Column(Text, nullable=False)
    error        = Column(Text, nullable=True)
    agent_feedback = Column(Text, nullable=True)    # last agent response about this code
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ContentPlayerSession")
    user    = relationship("User")