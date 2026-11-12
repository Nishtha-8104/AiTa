# Endpoints, under /api/v1/code-eval:
#   GET    /problems                          list the problem bank
#   GET    /problems/{problem_id}             one problem from the bank
#   POST   /run                               run code against the problem's shown example
#   POST   /submit                            save code for evaluation
#   POST   /submit/{submission_id}/evaluate   grade saved code against the tests and explain
#   POST   /evaluate                          save and evaluate in one request
#   GET    /submissions                       my code submissions
#   GET    /submissions/{submission_id}       one submission with all its evaluations
#   DELETE /submissions/{submission_id}       delete a submission
#   GET    /stats                             my evaluation stats and progress

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.core.exceptions import ProblemNotFound
from app.features.grading.schemas import (
    SubmitCodeRequest, SubmissionSummary, SubmissionDetail,
    EvaluationResult, UserEvalStats, RunCodeRequest, RunCodeResult
)
from app.features.problems.schemas import ProblemSummary
from app.features.grading.service import CodeEvalService
from app.features.practice import service as lifecycle
from app.features.problems.logic.listing import get_bank_problem, list_bank_problems
from app.features.problems.logic.sample_run import run_sample

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/code-eval", tags=["Code evaluation"])


# ─── Problem bank ─────────────────────────────────────────────────────────────

@router.get(
    "/problems",
    response_model=List[ProblemSummary],
    summary="List the problem bank",
)
def list_problems(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Every problem that has test cases, so every one listed can be graded."""
    return list_bank_problems(db)


@router.get(
    "/problems/{problem_id}",
    response_model=ProblemSummary,
    summary="Get one problem from the bank",
)
def get_problem(
    problem_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    problem = get_bank_problem(db, problem_id)
    if problem is None:
        raise ProblemNotFound(f"problem {problem_id} not found")
    return problem


# ─── Run against the shown example ───────────────────────────────────────────

@router.post(
    "/run",
    response_model=RunCodeResult,
    summary="Run code against the problem's shown example",
)
def run(
    req: RunCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Executes the code in the sandbox on the visible example only. Not scored, not saved."""
    if req.problem_id is not None:
        try:
            lifecycle.touch(db, current_user.id, "coding", req.problem_id,
                            datetime.now(timezone.utc))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("practice session touch failed for problem %s", req.problem_id)
    return run_sample(db, req.problem_id, req.language, req.code)


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
    Supports: c | cpp | python
    """
    return CodeEvalService.submit(db, current_user.id, req)


# ─── Trigger evaluation ───────────────────────────────────────────────────────

@router.post(
    "/submit/{submission_id}/evaluate",
    response_model=EvaluationResult,
    summary="Grade code against the problem's tests and explain the result",
)
def evaluate(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Runs the verified evaluation pipeline:
    1. Static metrics via lizard
    2. Test cases generated and cross-checked against a reference solution
    3. The student's code executed in a sandbox against every case
    4. Correctness measured as a pass rate — never estimated
    5. A hint about the first failing case, which never states the fix
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