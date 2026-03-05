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
    year_of_study = Column(Integer, nullable=True)  # 1-4 for undergrad, etc.
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)

    # Programming background
    skill_level = Column(Enum(SkillLevel), default=SkillLevel.BEGINNER)
    years_of_experience = Column(Float, default=0.0)
    preferred_languages = Column(JSON, default=list)   # ["Python", "Java", ...]
    learning_goals = Column(JSON, default=list)        # ["Web Dev", "ML", ...]
    interests = Column(JSON, default=list)             # ["Algorithms", "AI", ...]

    # Learning behavior (updated by User Profiling Agent)
    total_sessions = Column(Integer, default=0)
    total_time_spent_mins = Column(Float, default=0.0)
    avg_session_duration_mins = Column(Float, default=0.0)
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    # Gamification
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    badges = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    learning_profile = relationship("LearningProfile", back_populates="user", uselist=False)
    sessions = relationship("UserSession", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} role={self.role}>"


class LearningProfile(Base):
    """Detailed profiling data managed by the User Profiling Agent."""
    __tablename__ = "learning_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Knowledge areas & confidence scores (0.0 - 1.0)
    topic_scores = Column(JSON, default=dict)        # {"loops": 0.8, "recursion": 0.3, ...}
    error_patterns = Column(JSON, default=list)      # common errors the student makes
    strong_areas = Column(JSON, default=list)        # inferred strong topics
    weak_areas = Column(JSON, default=list)          # inferred weak topics
    recommended_next = Column(JSON, default=list)    # next topics to study

    # Behavioral patterns
    preferred_content_types = Column(JSON, default=list)  # ["video", "text", "exercises"]
    study_time_preference = Column(String(50), nullable=True)  # "morning", "evening", etc.
    avg_problems_per_session = Column(Float, default=0.0)
    accuracy_rate = Column(Float, default=0.0)       # % correct answers overall
    improvement_rate = Column(Float, default=0.0)    # rate of improvement over time

    # Profiling metadata
    profile_completeness = Column(Float, default=0.0)  # 0-100%
    last_updated_by_agent = Column(DateTime(timezone=True), nullable=True)
    agent_version = Column(String(20), default="1.0")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="learning_profile")


class UserSession(Base):
    """Tracks individual login/study sessions for behavioral analysis."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    token_jti = Column(String(255), unique=True, index=True)  # JWT ID for revocation

    # Session metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    user = relationship("User", back_populates="sessions")