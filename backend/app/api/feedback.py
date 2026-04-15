from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.code_eval import CodeEvaluation, CodeSubmission
from app.models.content_player import ContentPlayerSession
from app.schemas.feedback import (
    GenerateFeedbackRequest, FeedbackReportResponse, MarkReadRequest
)
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["Feedback Agent"])


@router.post(
    "/generate",
    response_model=FeedbackReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="🤖 Run Feedback Agent — synthesise from Code Eval + Content Player",
)
def generate(
    req: GenerateFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Runs the full Feedback Agent pipeline:
    1. Pulls Code Evaluation result (if evaluation_id given)
    2. Pulls Content Player session (if cp_session_id given)
    3. Analyses error patterns + misconceptions
    4. Groq LLM synthesises personalised narrative feedback
    5. Updates User Profile (weak_areas, error_patterns, topic_scores)
    6. Returns rich FeedbackReport
    """
    return FeedbackService.generate(db, current_user.id, req)


@router.get(
    "/",
    response_model=List[FeedbackReportResponse],
    summary="Get all my feedback reports",
)
def list_reports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return FeedbackService.get_reports(db, current_user.id)


@router.get(
    "/unread-count",
    summary="Get count of unread feedback reports",
)
def unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return {"unread": FeedbackService.unread_count(db, current_user.id)}


@router.get(
    "/{report_id}",
    response_model=FeedbackReportResponse,
    summary="Get a specific feedback report",
)
def get_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return FeedbackService.get_report(db, report_id, current_user.id)


@router.patch(
    "/{report_id}/read",
    summary="Mark feedback report as read",
)
def mark_read(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    FeedbackService.mark_read(db, report_id, current_user.id)
    return {"success": True}


@router.post(
    "/auto-generate",
    response_model=FeedbackReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="🤖 Auto-generate feedback from latest activity (no input needed)",
)
def auto_generate(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Automatically finds the user's most recent code evaluation and/or
    content player session and generates personalised feedback.
    No input required from the user.
    """
    from fastapi import HTTPException
    from app.models.feedback import FeedbackTone

    # Find latest code evaluation for this user
    latest_eval = (
        db.query(CodeEvaluation)
        .join(CodeSubmission, CodeEvaluation.submission_id == CodeSubmission.id)
        .filter(CodeSubmission.user_id == current_user.id)
        .order_by(CodeEvaluation.created_at.desc())
        .first()
    )

    # Find latest content player session for this user
    latest_session = (
        db.query(ContentPlayerSession)
        .filter(
            ContentPlayerSession.user_id == current_user.id,
            ContentPlayerSession.is_archived == False,
        )
        .order_by(ContentPlayerSession.created_at.desc())
        .first()
    )

    if not latest_eval and not latest_session:
        raise HTTPException(
            status_code=422,
            detail="No activity found. Complete a code evaluation or learning session first."
        )

    req = GenerateFeedbackRequest(
        evaluation_id=latest_eval.id if latest_eval else None,
        cp_session_id=latest_session.id if latest_session else None,
        tone=FeedbackTone.ENCOURAGING,
    )
    return FeedbackService.generate(db, current_user.id, req)
