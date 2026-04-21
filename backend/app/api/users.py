from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.schemas.user import (
    UserProfileResponse, UpdateProfileRequest,
    ChangePasswordRequest, MessageResponse
)
from app.services.user_service import UserService
from app.models.user import User, UserRole, LearningProfile
from app.models.code_eval import CodeSubmission, CodeEvaluation

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


@router.patch(
    "/consent",
    response_model=MessageResponse,
    summary="Update data sharing consent",
)
def update_consent(
    consent: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Toggle whether the user's anonymized data is used for peer comparison
    and collaborative filtering. Off = excluded from all comparisons.
    """
    current_user.data_sharing_consent = consent
    current_user.consent_updated_at   = datetime.now(timezone.utc)
    db.commit()
    state = "enabled" if consent else "disabled"
    return MessageResponse(message=f"Data sharing {state}.")


@router.get(
    "/peer-comparison",
    summary="Compare your progress against all consenting users",
)
def peer_comparison(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Returns anonymized comparison stats:
    - Your rank by points among all consenting users
    - Your avg code score vs platform average
    - Your sessions vs platform average
    - Your accuracy vs platform average
    - Percentile position
    Only users who have given data_sharing_consent=True are included.
    """
    # Pool: only consenting users (anonymized)
    pool = db.query(User).filter(
        User.data_sharing_consent == True,
        User.is_active == True,
    ).all()

    total_users = len(pool)
    if total_users == 0:
        return {
            "consent_required": not current_user.data_sharing_consent,
            "total_peers": 0,
            "message": "No comparison data yet. Be the first to enable data sharing.",
        }

    # ── Points rank ───────────────────────────────────────────────────────────
    points_list  = sorted([u.points for u in pool], reverse=True)
    user_points  = current_user.points
    points_rank  = next((i + 1 for i, p in enumerate(points_list) if p <= user_points), total_users)
    points_pct   = round((1 - (points_rank - 1) / total_users) * 100, 1)

    # ── Sessions comparison ───────────────────────────────────────────────────
    sessions_list = [u.total_sessions for u in pool]
    avg_sessions  = round(sum(sessions_list) / total_users, 1)

    # ── Accuracy comparison (from LearningProfile) ────────────────────────────
    profiles      = db.query(LearningProfile).filter(
        LearningProfile.user_id.in_([u.id for u in pool])
    ).all()
    accuracy_list = [p.accuracy_rate for p in profiles if p.accuracy_rate > 0]
    avg_accuracy  = round(sum(accuracy_list) / len(accuracy_list) * 100, 1) if accuracy_list else 0

    my_profile    = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id
    ).first()
    my_accuracy   = round((my_profile.accuracy_rate if my_profile else 0) * 100, 1)

    # ── Avg code score comparison ─────────────────────────────────────────────
    from sqlalchemy import func as sqlfunc
    platform_avg_score = db.query(sqlfunc.avg(CodeEvaluation.overall_score)).scalar() or 0

    my_avg_score_row = db.query(sqlfunc.avg(CodeEvaluation.overall_score)).filter(
        CodeEvaluation.user_id == current_user.id
    ).scalar()
    my_avg_score = round(my_avg_score_row or 0, 1)

    # ── Skill level distribution ──────────────────────────────────────────────
    skill_dist = {}
    for u in pool:
        lvl = u.skill_level.value if u.skill_level else "beginner"
        skill_dist[lvl] = skill_dist.get(lvl, 0) + 1

    return {
        "consent_required": not current_user.data_sharing_consent,
        "total_peers": total_users,
        "your_stats": {
            "points":       user_points,
            "sessions":     current_user.total_sessions,
            "accuracy_pct": my_accuracy,
            "avg_code_score": my_avg_score,
        },
        "platform_averages": {
            "points":         round(sum(points_list) / total_users, 1),
            "sessions":       avg_sessions,
            "accuracy_pct":   avg_accuracy,
            "avg_code_score": round(platform_avg_score, 1),
        },
        "your_rank": {
            "points_rank":      points_rank,
            "out_of":           total_users,
            "top_percentile":   points_pct,
        },
        "skill_distribution": skill_dist,
    }
