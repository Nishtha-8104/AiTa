from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.code_eval import (
    SubmitCodeRequest, SubmissionSummary, SubmissionDetail,
    EvaluationResult, UserEvalStats
)
from app.services.code_eval_service import CodeEvalService

router = APIRouter(prefix="/code-eval", tags=["Code Evaluation Agent"])


# ─── Submit code ──────────────────────────────────────────────────────────────

@router.post(
    "/submit",
    response_model=SubmissionSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for evaluation",
)
def submit_code(
    req: SubmitCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Submit code for multi-dimensional AI evaluation.
    Supports: python | javascript | java | cpp | c | typescript | go | rust | sql
    """
    return CodeEvalService.submit(db, current_user.id, req)


# ─── Trigger evaluation ───────────────────────────────────────────────────────

@router.post(
    "/submit/{submission_id}/evaluate",
    response_model=EvaluationResult,
    summary="🤖 Run Code Evaluation Agent",
)
def evaluate(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Runs the full evaluation pipeline:
    1. Static analyser (heuristic rules — naming, complexity, security, docs)
    2. Groq LLM deep analysis (correctness, Big-O, anti-patterns, improvements)
    3. Blended scoring across 6 dimensions
    4. Personalised learning points + corrected code
    """
    return CodeEvalService.evaluate(db, submission_id, current_user.id)


# ─── Submit + evaluate in one shot ───────────────────────────────────────────

@router.post(
    "/evaluate",
    response_model=EvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="⚡ Submit & evaluate in one request",
)
def submit_and_evaluate(
    req: SubmitCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Submit code and immediately run the full agent pipeline in one call."""
    submission = CodeEvalService.submit(db, current_user.id, req)
    return CodeEvalService.evaluate(db, submission.id, current_user.id)


# ─── List submissions ─────────────────────────────────────────────────────────

@router.get(
    "/submissions",
    response_model=List[SubmissionSummary],
    summary="List my code submissions",
)
def list_submissions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return CodeEvalService.get_submissions(db, current_user.id)


# ─── Get submission detail ────────────────────────────────────────────────────

@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionDetail,
    summary="Get submission with all evaluations",
)
def get_submission(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return CodeEvalService.get_submission(db, submission_id, current_user.id)


# ─── Delete submission ────────────────────────────────────────────────────────

@router.delete(
    "/submissions/{submission_id}",
    summary="Delete a submission",
)
def delete_submission(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    CodeEvalService.delete_submission(db, submission_id, current_user.id)
    return {"success": True, "message": "Submission deleted."}


# ─── User stats ───────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=UserEvalStats,
    summary="My evaluation stats & progress",
)
def get_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Returns score history, improvement trend, most common issues, and language breakdown."""
    return CodeEvalService.get_stats(db, current_user.id)