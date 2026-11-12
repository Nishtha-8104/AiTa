# Endpoints, under /api/v1/assessment:
#   GET  /next                          what to practise next, and why
#   POST /mcq/{question_id}/answer      answer a multiple-choice question
#   POST /debug/{challenge_id}/submit   submit a fix for a debugging challenge

import logging
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.learner_model.service import current_language
from app.features.onboarding.logic.recheck import require_no_open_check
from app.features.practice import service as lifecycle
from app.features.practice.agent.graph import next_item
from app.features.practice.logic.assessment.grading import grade_debug, grade_mcq
from app.features.practice.schemas import (
    DebugSubmitRequest,
    DebugSubmitResponse,
    McqAnswerRequest,
    McqAnswerResponse,
    NextItemResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessment", tags=["Practice"])


@router.get("/next", response_model=NextItemResponse, summary="What to practise next, and why")
def get_next(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """The weakest unlocked topic, with the item type and difficulty set by its measured
    mastery. Coding problems are submitted through
    `/code-eval/evaluate` with their `id` as `problem_id`. A 428 means the student
    switched to a new language and must take its short check first."""
    require_no_open_check(db, current_user)
    now = datetime.now(timezone.utc)
    _lifecycle(db, lifecycle.close_if_idle, current_user.id, now)
    served = next_item(db, current_user.id)
    _lifecycle(db, lifecycle.record_served, current_user.id,
               lifecycle.item_type_of(served.item_type), served.item["id"],
               current_language(db, current_user.id), now)
    return asdict(served)


def _lifecycle(db: Session, step, *args) -> None:
    """Session bookkeeping must never cost the student their next item."""
    try:
        step(db, *args)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("practice session %s failed", step.__name__)


@router.post("/mcq/{question_id}/answer", response_model=McqAnswerResponse,
             summary="Answer a multiple-choice question")
def answer_mcq(
    question_id: int,
    req: McqAnswerRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return asdict(grade_mcq(db, current_user.id, question_id, req.chosen_index))


@router.post("/debug/{challenge_id}/submit", response_model=DebugSubmitResponse,
             summary="Submit a fix for a debugging challenge")
def submit_debug(
    challenge_id: int,
    req: DebugSubmitRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return asdict(grade_debug(db, current_user.id, challenge_id, req.code))
