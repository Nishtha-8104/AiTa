from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.security import decode_token
from app.schemas.user import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, MessageResponse, UserProfileResponse
)
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account. Roles: student, instructor, ta, admin.
    - Email and username must be unique.
    - Password must be min 8 chars, with at least one uppercase and one digit.
    """
    user = AuthService.register(db, data)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access tokens",
)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate with email & password. Returns JWT access + refresh tokens.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AuthService.login(db, data, ip_address=ip_address, user_agent=user_agent)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Use a valid refresh token to get a new access token."""
    return AuthService.refresh_tokens(db, data.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current session",
)
def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Invalidate the current session token."""
    # In a real app, extract jti from token - simplified here
    AuthService.logout(db, current_user.id, jti="")
    return MessageResponse(message="Successfully logged out.")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Returns the profile of the currently authenticated user."""
    return current_user