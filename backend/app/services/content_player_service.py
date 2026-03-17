from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from app.agents.content_player_agent import ContentPlayerAgent
from app.models.content_player import ContentPlayerSession, SessionMode
from app.schemas.content_player import (
    CreateSessionRequest, ChatRequest, MessageFeedbackRequest
)


class ContentPlayerService:

    @staticmethod
    def create_session(db: Session, user_id: int, req: CreateSessionRequest) -> ContentPlayerSession:
        agent = ContentPlayerAgent(db)
        return agent.create_session(
            user_id  = user_id,
            mode     = req.mode,
            language = req.language,
            topic    = req.topic,
        )

    @staticmethod
    def chat(db: Session, session_id: int, user_id: int, req: ChatRequest) -> dict:
        agent = ContentPlayerAgent(db)
        try:
            return agent.chat(
                session_id    = session_id,
                user_id       = user_id,
                message       = req.message,
                code_snippet  = req.code_snippet,
                code_language = req.code_language,
                error_message = req.error_message,
                mode_override = req.mode,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    @staticmethod
    def get_sessions(db: Session, user_id: int) -> list:
        agent = ContentPlayerAgent(db)
        return agent.get_sessions(user_id)

    @staticmethod
    def get_session(db: Session, session_id: int, user_id: int) -> ContentPlayerSession:
        agent = ContentPlayerAgent(db)
        try:
            return agent.get_session_detail(session_id, user_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @staticmethod
    def archive_session(db: Session, session_id: int, user_id: int):
        agent = ContentPlayerAgent(db)
        agent.archive_session(session_id, user_id)

    @staticmethod
    def rate_message(db: Session, message_id: int, user_id: int, req: MessageFeedbackRequest):
        agent = ContentPlayerAgent(db)
        agent.rate_message(message_id, user_id, req.was_helpful)