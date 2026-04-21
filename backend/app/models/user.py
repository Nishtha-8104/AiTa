from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    Float, Enum, JSON, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    TA = "ta"
    ADMIN = "admin"


class SkillLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class User(Base):
    __tablename__ = "users"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Basic profile
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Personal info
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    institution = Column(String(255), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)

    # Programming background
    skill_level = Column(Enum(SkillLevel), default=SkillLevel.BEGINNER)
    years_of_experience = Column(Float, default=0.0)
    preferred_languages = Column(JSON, default=list)
    interested_topics = Column(JSON, default=list)
    learning_goals = Column(JSON, default=list)
    interests = Column(JSON, default=list)

    # Learning behavior
    total_sessions = Column(Integer, default=0)
    total_time_spent_mins = Column(Float, default=0.0)
    avg_session_duration_mins = Column(Float, default=0.0)
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    # Gamification
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    badges = Column(JSON, default=list)

    # Data sharing consent (like ChatGPT's data controls)
    data_sharing_consent = Column(Boolean, default=False)  # allow anonymous data in CF/comparison
    consent_updated_at   = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    content_player_sessions = relationship(
        "ContentPlayerSession",
        back_populates="user",
        foreign_keys="ContentPlayerSession.user_id",
    )
    learning_profile = relationship("LearningProfile", back_populates="user", uselist=False)
    sessions = relationship("UserSession", back_populates="user")
    otp_records = relationship("OTPRecord", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} role={self.role}>"


class OTPRecord(Base):
    """
    Stores a bcrypt-hashed OTP for 2-step login verification.
    One active record per user at a time — old ones are deleted on new OTP issue.
    The raw OTP is NEVER stored; only the bcrypt hash.
    """
    __tablename__ = "otp_records"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hashed_otp = Column(String(255), nullable=False)   # bcrypt hash of the 6-digit OTP
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used    = Column(Boolean, default=False)        # consumed after first successful verify
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="otp_records")


class LearningProfile(Base):
    """Detailed profiling data managed by the User Profiling Agent."""
    __tablename__ = "learning_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    topic_scores = Column(JSON, default=dict)
    error_patterns = Column(JSON, default=list)
    strong_areas = Column(JSON, default=list)
    weak_areas = Column(JSON, default=list)
    recommended_next = Column(JSON, default=list)
    preferred_content_types = Column(JSON, default=list)
    study_time_preference = Column(String(50), nullable=True)
    avg_problems_per_session = Column(Float, default=0.0)
    accuracy_rate = Column(Float, default=0.0)
    improvement_rate = Column(Float, default=0.0)
    profile_completeness = Column(Float, default=0.0)
    last_updated_by_agent = Column(DateTime(timezone=True), nullable=True)
    agent_version = Column(String(20), default="1.0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="learning_profile")


class UserSession(Base):
    """Tracks individual login/study sessions for behavioral analysis."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    token_jti = Column(String(255), unique=True, index=True)

    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")