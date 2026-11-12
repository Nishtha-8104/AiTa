# Endpoints, under /api/v1/feedback:
#   POST  /hint              next rung of the hint ladder for a problem
#   POST  /generate          write a feedback report from a code evaluation and recent practice
#   GET   /                  all my feedback reports
#   GET   /unread-count      how many reports I have not opened
#   GET   /{report_id}       one report
#   PATCH /{report_id}/read  mark a report as read
#   POST  /auto-generate     write a report from my latest activity, no input needed

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.grading.models import CodeEvaluation, CodeSubmission
from app.features.feedback.schemas import (
    GenerateFeedbackRequest, FeedbackReportResponse,
    HintRequest, HintResponse,
)
from app.features.feedback.service import FeedbackService
from app.features.hints.service import request_hint

router = APIRouter(prefix="/feedback", tags=["Feedback and hints"])


@router.post(
    "/hint",
    response_model=HintResponse,
    summary="Next rung of the hint ladder for a problem",
)
def hint(
    req: HintRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """One level up per request (L2 concept → L3 steps → L4 line pointer, capped at 4),
    grounded in the latest failing attempt. Every reply passes the leak guardrail."""
    result = request_hint(db, current_user.id, req.problem_id)
    return HintResponse(
        problem_id=result.problem_id, evaluation_id=result.evaluation_id,
        level=result.level, text=result.text, source=result.source,
    )


@router.post(
    "/generate",
    response_model=FeedbackReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Write a feedback report from a code evaluation and recent practice",
)
def generate(
    req: GenerateFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Steps:
    1. Pulls Code Evaluation result (if evaluation_id given)
    2. Pulls recent learning events (last 14 days, at most 30, seeds excluded)
    3. Analyses error patterns + misconceptions
    4. Synthesises a personalised narrative from those findings
    5. Updates User Profile (weak_areas, error_patterns, topic_scores)
    6. Returns rich FeedbackReport

    If the language model is unavailable the report is still returned, built from
    the pattern analysis alone and flagged with `pattern_only`.
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
    Automatically reads the user's most recent code evaluation and recent
    learning events and generates personalised feedback. No input required.
    422 when there is neither.
    """
    from app.features.feedback.models import FeedbackTone

    latest_eval = (
        db.query(CodeEvaluation)
        .join(CodeSubmission, CodeEvaluation.submission_id == CodeSubmission.id)
        .filter(CodeSubmission.user_id == current_user.id)
        .order_by(CodeEvaluation.created_at.desc())
        .first()
    )

    req = GenerateFeedbackRequest(
        evaluation_id=latest_eval.id if latest_eval else None,
        tone=FeedbackTone.ENCOURAGING,
    )
    return FeedbackService.generate(db, current_user.id, req)
