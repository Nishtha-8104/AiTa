from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.schemas.user import (
    UserProfileResponse, UpdateProfileRequest,
    ChangePasswordRequest, MessageResponse
)
from app.services.user_service import UserService
from app.models.user import User, UserRole

router = APIRouter(prefix="/users", tags=["User Profile"])


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Get my full profile with learning data",
)
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Returns the full profile including learning profile agent data."""
    return UserService.get_user_by_id(db, current_user.id)


@router.patch(
    "/profile",
    response_model=UserProfileResponse,
    summary="Update my profile",
)
def update_my_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update personal info, skill level, interests, and learning goals."""
    return UserService.update_profile(db, current_user.id, data)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    UserService.change_password(db, current_user.id, data)
    return MessageResponse(message="Password changed successfully.")


@router.get(
    "/",
    response_model=List[UserProfileResponse],
    summary="[Admin] List all users",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Admin only: list all registered users."""
    return UserService.get_all_users(db, skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserProfileResponse,
    summary="[Admin] Get user by ID",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """Admin only: get any user's profile by ID."""
    return UserService.get_user_by_id(db, user_id)