from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.schemas.user import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshTokenRequest, MessageResponse, UserProfileResponse,
    OTPChallengeResponse, VerifyOTPRequest,
)
from app.services.auth_service import AuthService
from app.models.user import User

import logging

logger=logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return AuthService.register(db, data)
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        raise


@router.post(
    "/login",
    response_model=OTPChallengeResponse,
    summary="Step 1 — verify password, receive OTP via email",
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Verifies email + password.
    On success: generates a 6-digit OTP, bcrypt-hashes it, stores the hash,
    emails the raw OTP to the user, and returns an otp_token (10-min JWT).
    The client must call /auth/verify-otp with that token + the OTP to get
    real access tokens.
    """
    return AuthService.login_step1(db, data)


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Step 2 — submit OTP, receive access + refresh tokens",
)
def verify_otp(data: VerifyOTPRequest, request: Request, db: Session = Depends(get_db)):
    """
    Verifies the 6-digit OTP against its bcrypt hash.
    On success: marks OTP as used and returns real JWT access + refresh tokens.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AuthService.login_step2(
        db,
        otp_token  = data.otp_token,
        otp        = data.otp,
        ip_address = ip_address,
        user_agent = user_agent,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
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
    AuthService.logout(db, current_user.id, jti="")
    return MessageResponse(message="Successfully logged out.")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
