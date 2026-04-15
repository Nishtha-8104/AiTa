# from pydantic import BaseModel, Field
# from typing import Optional, List
# from datetime import datetime
# from app.models.content_player import SessionMode, MessageRole


# # ─── Message Schemas ──────────────────────────────────────────────────────────

# class MessageResponse(BaseModel):
#     id: int
#     session_id: int
#     role: MessageRole
#     content: str
#     has_code: bool
#     code_snippet: Optional[str]
#     code_language: Optional[str]
#     error_message: Optional[str]
#     tokens_used: int
#     latency_ms: int
#     was_helpful: Optional[bool]
#     created_at: datetime

#     class Config:
#         from_attributes = True


# # ─── Session Schemas ──────────────────────────────────────────────────────────

# class SessionSummary(BaseModel):
#     id: int
#     title: Optional[str]
#     mode: SessionMode
#     language: Optional[str]
#     topic: Optional[str]
#     total_messages: int
#     concepts_covered: List[str]
#     confusion_detected: bool
#     created_at: datetime
#     last_message_at: Optional[datetime]

#     class Config:
#         from_attributes = True


# class SessionDetail(SessionSummary):
#     messages: List[MessageResponse]
#     total_tokens_used: int
#     mastery_signals: List[str]
#     weak_signals: List[str]

#     class Config:
#         from_attributes = True


# class CreateSessionRequest(BaseModel):
#     mode: SessionMode = SessionMode.QA
#     language: Optional[str] = None
#     topic: Optional[str] = None


# # ─── Chat Request/Response ────────────────────────────────────────────────────

# class ChatRequest(BaseModel):
#     message: str = Field(..., min_length=1, max_length=8000)
#     code_snippet: Optional[str] = Field(None, max_length=20000)
#     code_language: Optional[str] = None
#     error_message: Optional[str] = Field(None, max_length=5000)
#     mode: Optional[SessionMode] = None   # override session mode for this turn


# class ChatResponse(BaseModel):
#     message_id: int
#     session_id: int
#     response: str
#     tokens_used: int
#     latency_ms: int
#     session_title: Optional[str]
#     detected_concepts: List[str]
#     follow_up_suggestions: List[str]
#     confusion_detected: bool


# # ─── Feedback Schema ──────────────────────────────────────────────────────────

# class MessageFeedbackRequest(BaseModel):
#     was_helpful: bool



"""
schemas/content_player.py — UPDATED with difficulty, topic_changed, comfort_signal
Copy to: backend/app/schemas/content_player.py
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SessionCreate(BaseModel):
    mode: str  # walkthrough | qa | quiz | code_help | brainstorm
    topic: str
    language: Optional[str] = "python"
    difficulty: Optional[str] = "medium"  # ← NEW: initial difficulty


class SessionResponse(BaseModel):
    id: int
    mode: str
    topic: str
    language: str
    difficulty: Optional[str] = "medium"
    concepts_covered: Optional[List[str]] = []
    mastery_signals: Optional[List[str]] = []
    weak_signals: Optional[List[str]] = []
    confusion_detected: Optional[bool] = False
    total_tokens_used: Optional[int] = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    code_snippet: Optional[str] = None  # For code_help mode
    difficulty_override: Optional[str] = None  # Allow manual difficulty override


class ChatResponse(BaseModel):
    message_id: int
    response: str
    concepts: List[str] = []
    mode: str
    topic: str
    difficulty: str = "medium"
    difficulty_changed: bool = False
    topic_changed: bool = False
    comfort_signal: str = "comfortable"
    tokens_used: int = 0
    # Question mastery
    question_solved: bool = False          # True if this submission was marked solved
    difficulty_increased: bool = False     # True if difficulty was auto-bumped this turn


class MessageFeedback(BaseModel):
    was_helpful: bool


class GenerateProblemRequest(BaseModel):
    topic: str
    difficulty: str = "medium"
    language: str = "python"
    exclude_titles: list = []   # titles already shown — don't repeat these


class GenerateProblemResponse(BaseModel):
    title: str
    difficulty: str
    description: str
    examples: list = []
    constraints: list = []
    hints: list = []
    starter_code: str = ""
    solution_code: str = ""
    explanation: str = ""