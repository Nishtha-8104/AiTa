from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.feedback import FeedbackType, FeedbackTone


# ── Request schemas ───────────────────────────────────────────────────────────

class GenerateFeedbackRequest(BaseModel):
    """
    At least one of evaluation_id or cp_session_id must be provided.
    The agent uses whichever sources are available and sets feedback_type
    automatically (code_review / learning_recap / combined).
    """
    evaluation_id: Optional[int] = Field(
        None, description="ID from code_evaluations table (Code Eval Agent output)"
    )
    cp_session_id: Optional[int] = Field(
        None, description="ID from content_player_sessions table (Content Player output)"
    )
    tone: FeedbackTone = Field(
        FeedbackTone.ENCOURAGING,
        description="Tone of the feedback: encouraging | constructive | challenging"
    )

    class Config:
        use_enum_values = True


# ── Response schemas ──────────────────────────────────────────────────────────

class FeedbackReportResponse(BaseModel):
    id:             int
    user_id:        int
    evaluation_id:  Optional[int]         = None
    cp_session_id:  Optional[int]         = None
    feedback_type:  FeedbackType
    tone:           FeedbackTone
    headline:       Optional[str]         = None
    summary:        Optional[str]         = None
    strengths:      List[str]             = []
    errors:         List[str]             = []
    misconceptions: List[str]             = []
    action_items:   List[str]             = []
    concept_map:    Dict[str, float]      = {}
    next_topics:    List[str]             = []
    motivational:   Optional[str]         = None
    profile_updates: Dict[str, Any]       = {}
    agent_steps:    List[str]             = []
    tokens_used:    int                   = 0
    latency_ms:     int                   = 0
    is_read:        bool                  = False
    created_at:     datetime

    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    is_read: bool = True