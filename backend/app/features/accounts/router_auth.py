# Endpoints, under /api/v1/auth:
#   POST /session   open the student's session (PET runs locally, so no sign-in)
#   GET  /me        the student

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.accounts.schemas import TokenResponse, UserProfileResponse
from app.features.accounts.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/session",
    response_model=TokenResponse,
    summary="Open the student's session",
)
def open_session(request: Request, db: Session = Depends(get_db)):
    return AuthService.open_session(
        db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
