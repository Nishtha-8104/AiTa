# from fastapi import APIRouter, Depends, status
# from sqlalchemy.orm import Session
# from typing import List

# from app.core.database import get_db
# from app.core.dependencies import get_current_active_user
# from app.models.user import User
# from app.schemas.content_player import (
#     CreateSessionRequest, SessionSummary, SessionDetail,
#     ChatRequest, ChatResponse, MessageFeedbackRequest
# )
# from app.services.content_player_service import ContentPlayerService

# router = APIRouter(prefix="/content-player", tags=["Content Player Agent"])


# # ─── Session management ───────────────────────────────────────────────────────

# @router.post(
#     "/sessions",
#     response_model=SessionSummary,
#     status_code=status.HTTP_201_CREATED,
#     summary="Create a new learning session",
# )
# def create_session(
#     req: CreateSessionRequest,
#     current_user: User = Depends(get_current_active_user),
#     db: Session = Depends(get_db),
# ):
#     """
#     Start a new Content Player session.
#     Choose a mode: qa | code_help | brainstorm | quiz | walkthrough
#     """
#     return ContentPlayerService.create_session(db, current_user.id, req)


# @router.get(
#     "/sessions",
#     response_model=List[SessionSummary],
#     summary="List my learning sessions",
# )
# def list_sessions(
#     current_user: User = Depends(get_current_active_user),
#     db: Session = Depends(get_db),
# ):
#     return ContentPlayerService.get_sessions(db, current_user.id)


# @router.get(
#     "/sessions/{session_id}",
#     response_model=SessionDetail,
#     summary="Get a session with full message history",
# )
# def get_session(
#     session_id: int,
#     current_user: User = Depends(get_current_active_user),
#     db: Session = Depends(get_db),
# ):
#     return ContentPlayerService.get_session(db, session_id, current_user.id)


# @router.delete(
#     "/sessions/{session_id}",
#     summary="Archive a session",
# )
# def archive_session(
#     session_id: int,
#     current_user: User = Depends(get_current_active_user),
#     db: Session = Depends(get_db),
# ):
#     ContentPlayerService.archive_session(db, session_id, current_user.id)
#     return {"success": True, "message": "Session archived."}


# # ─── Chat ─────────────────────────────────────────────────────────────────────

# @router.post(
#     "/sessions/{session_id}/chat",
#     response_model=ChatResponse,
#     summary="💬 Send message to Content Player Agent",
# )
# def chat(
#     session_id: int,
#     req: ChatRequest,
#     current_user: User = Depends(get_current_active_user),
#     db: Session = Depends(get_db),
# ):
#     """
#     Send a message (with optional code + error) to the Content Player Agent.
#     The agent will respond based on the session mode:
#     - **qa**: explanation with Socratic follow-ups
#     - **code_help**: debug hints without giving solutions
#     - **brainstorm**: explore approaches and trade-offs
#     - **quiz**: adaptive question-answer testing
#     - **walkthrough**: step-by-step guided learning
#     """
#     return ContentPlayerService.chat(db, session_id, current_user.id, req)


# # ─── Message feedback ─────────────────────────────────────────────────────────

# @router.patch(
#     "/messages/{message_id}/feedback",
#     summary="Rate an agent response (thumbs up/down)",
# )
# def rate_message(
#     message_id: int,
#     req: MessageFeedbackRequest,
#     current_user: User = Depends(get_current_active_user),
#     db: Session = Depends(get_db),
# ):
#     ContentPlayerService.rate_message(db, message_id, current_user.id, req)
#     return {"success": True, "message": "Feedback recorded."}

"""
api/content_player.py — UPDATED with:
  1. Difficulty level stored in session, adjusted per message
  2. Topic sync — if topic changes, updates session + learning profile  
  3. Interested topics from user profile passed to agent

Copy to: backend/app/api/content_player.py
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.content_player import ContentPlayerSession, ContentPlayerMessage
from app.schemas.content_player import (
    SessionCreate, SessionResponse, ChatRequest, ChatResponse, MessageFeedback,
    GenerateProblemRequest, GenerateProblemResponse
)
from app.agents.content_player_agent import run_content_player, generate_leetcode_problem

router = APIRouter(prefix="/content-player", tags=["Content Player"])


# ─── Session Management ───────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = ContentPlayerSession(
        user_id=current_user.id,
        mode=body.mode,
        topic=body.topic,
        language=body.language or "python",
        difficulty=body.difficulty or "medium",  # ← store difficulty in session
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ContentPlayerSession)
        .filter(
            ContentPlayerSession.user_id == current_user.id,
            ContentPlayerSession.is_archived == False,
        )
        .order_by(ContentPlayerSession.created_at.desc())
        .limit(20)
        .all()
    )
    return sessions


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ContentPlayerSession).filter(
        ContentPlayerSession.id == session_id,
        ContentPlayerSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    
    messages = (
        db.query(ContentPlayerMessage)
        .filter(ContentPlayerMessage.session_id == session_id)
        .order_by(ContentPlayerMessage.created_at.asc())
        .all()
    )
    return {"session": session, "messages": messages}


@router.delete("/sessions/{session_id}")
def archive_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ContentPlayerSession).filter(
        ContentPlayerSession.id == session_id,
        ContentPlayerSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    session.is_archived = True
    db.commit()
    return {"message": "Session archived"}


# ─── Chat (Main Agent Endpoint) ───────────────────────────────────────────────

@router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: int,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Load session
    session = db.query(ContentPlayerSession).filter(
        ContentPlayerSession.id == session_id,
        ContentPlayerSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    
    if not body.message.strip():
        raise HTTPException(422, "Message cannot be empty")
    
    # Load conversation history
    messages = (
        db.query(ContentPlayerMessage)
        .filter(ContentPlayerMessage.session_id == session_id)
        .order_by(ContentPlayerMessage.created_at.asc())
        .all()
    )
    history = [{"role": m.role if isinstance(m.role, str) else m.role.value, "content": m.content} for m in messages]
    
    # Get user profile with interested_topics
    user_profile = {
        "interested_topics": current_user.interested_topics or [],
        "skill_level": current_user.skill_level or "beginner",
        "preferred_languages": current_user.preferred_languages or ["python"],
    }
    
    # Run the agent
    result = await run_content_player(
        mode=session.mode if isinstance(session.mode, str) else session.mode.value,
        topic=session.topic,
        language=session.language,
        message=body.message,
        conversation_history=history,
        user_profile=user_profile,
        difficulty=getattr(session, "difficulty", "medium"),
        solved_questions=getattr(session, "solved_questions", None) or [],
        consecutive_easy_solves=getattr(session, "consecutive_easy_solves", 0) or 0,
        code_snippet=body.code_snippet,
    )
    
    # ─── Topic Sync ───────────────────────────────────────────────────────────
    # If topic changed and user explicitly confirmed, update session + profile
    if result["topic_changed"] and result["new_topic"]:
        new_topic = result["new_topic"]
        # Update session topic
        session.topic = new_topic
        
        # Update learning profile — add new topic to recommended_next
        profile = current_user.learning_profile
        if profile:
            rec_next = profile.recommended_next or []
            if new_topic not in rec_next:
                rec_next.append(new_topic)
                profile.recommended_next = rec_next
        
        # Also update user's interested_topics if it's a valid known topic
        topics = current_user.interested_topics or []
        if new_topic not in topics:
            topics.append(new_topic)
            current_user.interested_topics = topics
    
    # ─── Difficulty Sync ─────────────────────────────────────────────────────
    new_difficulty = result.get("new_difficulty", "medium")
    if hasattr(session, "difficulty"):
        session.difficulty = new_difficulty

    # ─── Question mastery sync ────────────────────────────────────────────────
    if result.get("question_solved"):
        session.solved_questions = result.get("solved_questions", [])
    session.consecutive_easy_solves = result.get("consecutive_easy_solves", 0)
    
    # ─── Save messages ────────────────────────────────────────────────────────
    # Save user message
    user_msg = ContentPlayerMessage(
        session_id=session_id,
        user_id=current_user.id,
        role="user",
        content=body.message,
        code_snippet=body.code_snippet,
    )
    db.add(user_msg)
    
    # Save assistant message
    meta = result["metadata"]
    assistant_msg = ContentPlayerMessage(
        session_id=session_id,
        user_id=current_user.id,
        role="assistant",
        content=result["response"],
    )
    db.add(assistant_msg)
    
    # Update session signals
    session.concepts_covered = list(set(
        (session.concepts_covered or []) + meta.get("concepts", [])
    ))
    if meta.get("confusion"):
        session.confusion_detected = True
    session.mastery_signals = list(set(
        (session.mastery_signals or []) + meta.get("mastery", [])
    ))
    session.weak_signals = list(set(
        (session.weak_signals or []) + meta.get("weak", [])
    ))
    session.total_tokens_used = (session.total_tokens_used or 0) + meta.get("tokens_used", 0)
    
    db.commit()
    db.refresh(assistant_msg)
    
    return ChatResponse(
        message_id=assistant_msg.id,
        response=result["response"],
        concepts=meta.get("concepts", []),
        mode=session.mode if isinstance(session.mode, str) else session.mode.value,
        topic=session.topic,
        difficulty=new_difficulty,
        difficulty_changed=result["metadata"].get("difficulty_changed", False),
        topic_changed=result["topic_changed"],
        comfort_signal=meta.get("comfort_signal", "comfortable"),
        tokens_used=meta.get("tokens_used", 0),
        question_solved=result.get("question_solved", False),
        difficulty_increased=result.get("difficulty_increased", False),
    )


# ─── Message Feedback ─────────────────────────────────────────────────────────

@router.patch("/messages/{message_id}/feedback")
def update_feedback(
    message_id: int,
    body: MessageFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = db.query(ContentPlayerMessage).filter(
        ContentPlayerMessage.id == message_id
    ).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    msg.was_helpful = body.was_helpful
    db.commit()
    return {"message": "Feedback saved"}


# ─── Generate LeetCode Problem ────────────────────────────────────────────────

@router.post("/generate-problem", response_model=GenerateProblemResponse)
async def generate_problem(
    body: GenerateProblemRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a LeetCode-style problem for a given topic and difficulty."""
    result = await generate_leetcode_problem(
        topic=body.topic,
        difficulty=body.difficulty,
        language=body.language,
        exclude_titles=body.exclude_titles,
    )
    return result
