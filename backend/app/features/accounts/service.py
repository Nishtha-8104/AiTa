import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.features.accounts.models import LearningProfile, User, UserSession
from app.features.accounts.schemas import TokenResponse


class AuthService:
    """PET runs on the student's own computer: one student, no sign-in screen. The
    browser still carries a token so every endpoint knows whose data it serves."""

    LOCAL_EMAIL = "student@pet.local"

    @staticmethod
    def create_user(db: Session, email: str, username: str, full_name: str | None = None) -> User:
        user = User(email=email, username=username, full_name=full_name, is_verified=True,
                    preferred_languages=[], learning_goals=[], interests=[], badges=[])
        db.add(user)
        db.flush()
        db.add(LearningProfile(user_id=user.id, topic_scores={}, error_patterns=[],
                               strong_areas=[], weak_areas=[], recommended_next=[],
                               preferred_content_types=[]))
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def open_session(db: Session, ip_address: str = None,
                     user_agent: str = None) -> TokenResponse:
        user = db.query(User).filter(User.email == AuthService.LOCAL_EMAIL).first()
        if user is None:
            user = AuthService.create_user(db, AuthService.LOCAL_EMAIL, "student")

        jti = str(uuid.uuid4())
        db.add(UserSession(user_id=user.id, token_jti=jti, ip_address=ip_address,
                           user_agent=user_agent))
        user.total_sessions += 1
        user.last_active_at = datetime.now(timezone.utc)
        db.commit()

        token = create_access_token({"sub": str(user.id), "username": user.username,
                                     "role": user.role, "jti": jti})
        return TokenResponse(access_token=token,
                             expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
