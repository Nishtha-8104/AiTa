from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.models.recommendation import Recommendation, AgentRunLog
from app.schemas.recommendation import (
    RecommendationItem, LogInteractionRequest, LogInteractionResponse,
    AgentRunStatus, CreateContentRequest, ContentResponse
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Content Recommendation Agent"])


# ─── Trigger the AI Agent ────────────────────────────────────────────────────

@router.post(
    "/generate",
    summary="🤖 Run the Content Recommendation Agent",
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_recommendations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Triggers the full agentic pipeline:
    1. Collaborative Filtering
    2. Content-Based Filtering
    3. RL exploration bonus
    4. Claude LLM reasoning & ranking

    Returns batch_id + agent thought steps.
    """
    result = RecommendationService.run_agent(db, current_user.id)
    return result


# ─── Get stored recommendations ──────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[RecommendationItem],
    summary="Get my current recommendations",
)
def get_my_recommendations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Returns the last agent-generated recommendations for the current user."""
    recs = RecommendationService.get_recommendations(db, current_user.id)
    return recs


# ─── Get agent run log ───────────────────────────────────────────────────────

@router.get(
    "/agent-log",
    response_model=AgentRunStatus,
    summary="Get last agent run metadata & thought log",
)
def get_agent_log(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Returns metadata and step-by-step thought log from the last agent run."""
    log = RecommendationService.get_latest_run_log(db, current_user.id)
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No agent run found. Call /generate first.")
    return log


# ─── Log interaction ─────────────────────────────────────────────────────────

@router.post(
    "/interact",
    response_model=LogInteractionResponse,
    summary="Log user interaction with a content item",
)
def log_interaction(
    req: LogInteractionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Records a user interaction (view, complete, like, dislike, skip, bookmark).
    Updates the implicit rating used by Collaborative Filtering next run.
    """
    result = RecommendationService.log_interaction(db, current_user.id, req)
    return result


# ─── Dismiss a recommendation ────────────────────────────────────────────────

@router.patch(
    "/{rec_id}/dismiss",
    summary="Dismiss a recommendation",
)
def dismiss_recommendation(
    rec_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    RecommendationService.dismiss_recommendation(db, current_user.id, rec_id)
    return {"success": True, "message": "Recommendation dismissed."}


# ─── Content Catalog ─────────────────────────────────────────────────────────

@router.get(
    "/content",
    response_model=List[ContentResponse],
    summary="Browse content catalog",
)
def list_content(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return RecommendationService.list_content(db, skip=skip, limit=limit)


@router.post(
    "/content/seed",
    summary="Seed starter content catalog",
)
def seed_content(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Seeds 20 starter content items if DB is empty. Safe to call multiple times."""
    count = RecommendationService.bulk_seed_content(db)
    return {"message": f"Content catalog has {count} items.", "count": count}


@router.post(
    "/content",
    response_model=ContentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Add content item",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.INSTRUCTOR))],
)
def create_content(
    req: CreateContentRequest,
    db: Session = Depends(get_db),
):
    return RecommendationService.seed_content(db, req)