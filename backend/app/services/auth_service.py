from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
import uuid

from app.models.user import User, LearningProfile, UserSession
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from app.core.config import settings


class AuthService:

    @staticmethod
    def register(db: Session, data: RegisterRequest) -> User:
        """Register a new user and create their learning profile."""

        # Check email uniqueness
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists."
            )

        # Check username uniqueness
        if db.query(User).filter(User.username == data.username).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This username is already taken. Please choose another."
            )

        # Create user
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            preferred_languages=[],
            learning_goals=[],
            interests=[],
            badges=[],
        )
        db.add(user)
        db.flush()  # get user.id before commit

        # Auto-create empty learning profile
        profile = LearningProfile(
            user_id=user.id,
            topic_scores={},
            error_patterns=[],
            strong_areas=[],
            weak_areas=[],
            recommended_next=[],
            preferred_content_types=[],
        )
        db.add(profile)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(db: Session, data: LoginRequest, ip_address: str = None, user_agent: str = None) -> TokenResponse:
        """Authenticate user and return JWT tokens."""

        user = db.query(User).filter(User.email == data.email).first()

        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact support."
            )

        # Create tokens
        jti = str(uuid.uuid4())
        token_data = {"sub": str(user.id), "username": user.username, "role": user.role, "jti": jti}

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Record session
        session = UserSession(
            user_id=user.id,
            token_jti=jti,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(session)

        # Update stats
        user.total_sessions += 1
        from datetime import datetime, timezone
        user.last_active_at = datetime.now(timezone.utc)
        db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
        """Issue new access token from a valid refresh token."""

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token."
            )

        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        jti = str(uuid.uuid4())
        token_data = {"sub": str(user.id), "username": user.username, "role": user.role, "jti": jti}
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def logout(db: Session, user_id: int, jti: str):
        """Invalidate the current session."""
        session = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.token_jti == jti,
        ).first()
        if session:
            from datetime import datetime, timezone
            session.is_active = False
            session.ended_at = datetime.now(timezone.utc)
            db.commit()