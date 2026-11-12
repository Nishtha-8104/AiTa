# Endpoints, under /api/v1/profile:
#   GET /mastery  measured mastery for every topic, in the study language

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.accounts.schemas import MasteryResponse
from app.features.learner_model.service import mastery_snapshot

router = APIRouter(prefix="/profile", tags=["Learner profile"])


@router.get(
    "/mastery",
    response_model=MasteryResponse,
    summary="Measured mastery for all 12 topics",
)
def get_mastery(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Every topic, including ones never attempted (prior 0.3, evidence 0), plus the
    misconceptions and hint reliance behind the numbers."""
    return mastery_snapshot(db, current_user.id)
