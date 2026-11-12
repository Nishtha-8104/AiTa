from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.features.feedback.agent.graph import generate_feedback
from app.features.feedback.agent.nodes.gather_context import NO_ACTIVITY
from app.features.feedback.logic import reports
from app.features.feedback.logic.activity import recent_events
from app.features.feedback.models import FeedbackTone
from app.features.feedback.schemas import GenerateFeedbackRequest


class FeedbackService:

    @staticmethod
    def generate(db: Session, user_id: int, req: GenerateFeedbackRequest, *,
                 synthesise_runnable=None):
        if not req.evaluation_id and not recent_events(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=NO_ACTIVITY
            )
        try:
            tone = FeedbackTone(req.tone) if isinstance(req.tone, str) else req.tone
            return generate_feedback(
                db, user_id, req.evaluation_id, tone,
                synthesise_runnable=synthesise_runnable,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    @staticmethod
    def get_reports(db: Session, user_id: int):
        return reports.get_reports(db, user_id)

    @staticmethod
    def get_report(db: Session, report_id: int, user_id: int):
        try:
            return reports.get_report(db, report_id, user_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @staticmethod
    def mark_read(db: Session, report_id: int, user_id: int):
        reports.mark_read(db, report_id, user_id)

    @staticmethod
    def unread_count(db: Session, user_id: int) -> int:
        return reports.unread_count(db, user_id)
