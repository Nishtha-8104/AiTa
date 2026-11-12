# Endpoints, under /api/v1/topic-practice:
#   GET  /next                           the current item of my topic run
#   POST /theory/{question_id}/answer    answer a written theory question
#   GET  /{topic}/explanation            the written explanation of a topic in my language
#   POST /{topic}/start                  start, or resume, a practice run on one topic

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.onboarding.logic.recheck import require_no_open_check
from app.features.practice.logic.assessment.theory import grade_theory
from app.features.practice.logic.topic_practice import runs
from app.features.practice.schemas import (
    ExplanationOut,
    RunOut,
    RunStepOut,
    TheoryAnswerOut,
    TheoryAnswerRequest,
)

router = APIRouter(prefix="/topic-practice", tags=["Topic practice"])


@router.get("/next", response_model=RunStepOut, summary="The current item of your topic run")
def get_next(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """The item stays the same until it is graded. `done` means every slot is graded:
    finish the run with `/practice-sessions/{session_id}/finish` to see its wrap-up."""
    step = runs.next_step(db, current_user.id, datetime.now(timezone.utc))
    db.commit()
    return asdict(step)


@router.post("/theory/{question_id}/answer", response_model=TheoryAnswerOut,
             summary="Answer a written theory question")
def answer_theory(
    question_id: int,
    req: TheoryAnswerRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """A 503 means the grader could not be reached; nothing was recorded, so send the
    same answer again."""
    return asdict(grade_theory(db, current_user.id, question_id, req.answer))


@router.get("/{topic}/explanation", response_model=ExplanationOut,
            summary="The written explanation of a topic in your language")
def get_explanation(
    topic: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return asdict(runs.explanation(db, current_user.id, topic))


@router.post("/{topic}/start", response_model=RunOut,
             summary="Start, or resume, a run of practice on one topic")
def start(
    topic: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """A 428 means the student switched to a new language and must take its short check
    first. Any other open session is closed, and its wrap-up waits on Home."""
    require_no_open_check(db, current_user)
    s = runs.start(db, current_user.id, topic, datetime.now(timezone.utc))
    db.commit()
    return RunOut(session_id=s.id, total=len(s.plan))
