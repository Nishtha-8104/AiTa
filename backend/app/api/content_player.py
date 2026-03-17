from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.content_player import (
    CreateSessionRequest, SessionSummary, SessionDetail,
    ChatRequest, ChatResponse, MessageFeedbackRequest
)
from app.services.content_player_service import ContentPlayerService

router = APIRouter(prefix="/content-player", tags=["Content Player Agent"])


# ─── Session management ───────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=SessionSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new learning session",
)
def create_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start a new Content Player session.
    Choose a mode: qa | code_help | brainstorm | quiz | walkthrough
    """
    return ContentPlayerService.create_session(db, current_user.id, req)


@router.get(
    "/sessions",
    response_model=List[SessionSummary],
    summary="List my learning sessions",
)
def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return ContentPlayerService.get_sessions(db, current_user.id)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetail,
    summary="Get a session with full message history",
)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return ContentPlayerService.get_session(db, session_id, current_user.id)


@router.delete(
    "/sessions/{session_id}",
    summary="Archive a session",
)
def archive_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    ContentPlayerService.archive_session(db, session_id, current_user.id)
    return {"success": True, "message": "Session archived."}


# ─── Chat ─────────────────────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/chat",
    response_model=ChatResponse,
    summary="💬 Send message to Content Player Agent",
)
def chat(
    session_id: int,
    req: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Send a message (with optional code + error) to the Content Player Agent.
    The agent will respond based on the session mode:
    - **qa**: explanation with Socratic follow-ups
    - **code_help**: debug hints without giving solutions
    - **brainstorm**: explore approaches and trade-offs
    - **quiz**: adaptive question-answer testing
    - **walkthrough**: step-by-step guided learning
    """
    return ContentPlayerService.chat(db, session_id, current_user.id, req)


# ─── Message feedback ─────────────────────────────────────────────────────────

@router.patch(
    "/messages/{message_id}/feedback",
    summary="Rate an agent response (thumbs up/down)",
)
def rate_message(
    message_id: int,
    req: MessageFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    ContentPlayerService.rate_message(db, message_id, current_user.id, req)
    return {"success": True, "message": "Feedback recorded."}