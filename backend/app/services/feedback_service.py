from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.agents.feedback_agent import FeedbackAgent
from app.models.feedback import FeedbackTone
from app.schemas.feedback import GenerateFeedbackRequest
from typing import Optional


class FeedbackService:

    @staticmethod
    def generate(db: Session, user_id: int, req: GenerateFeedbackRequest):
        if not req.evaluation_id and not req.cp_session_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide at least one of evaluation_id or cp_session_id."
            )
        agent = FeedbackAgent(db)
        try:
            tone = FeedbackTone(req.tone) if isinstance(req.tone, str) else req.tone
            return agent.generate(user_id, req.evaluation_id, req.cp_session_id, tone)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    @staticmethod
    def get_reports(db: Session, user_id: int):
        return FeedbackAgent(db).get_reports(user_id)

    @staticmethod
    def get_report(db: Session, report_id: int, user_id: int):
        try:
            return FeedbackAgent(db).get_report(report_id, user_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @staticmethod
    def mark_read(db: Session, report_id: int, user_id: int):
        FeedbackAgent(db).mark_read(report_id, user_id)

    @staticmethod
    def unread_count(db: Session, user_id: int) -> int:
        return FeedbackAgent(db).unread_count(user_id)