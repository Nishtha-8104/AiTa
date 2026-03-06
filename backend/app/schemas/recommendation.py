from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.recommendation import ContentType, DifficultyLevel, InteractionType


# ─── Content Schemas ──────────────────────────────────────────────────────────

class ContentResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    content_type: ContentType
    difficulty: DifficultyLevel
    url: Optional[str]
    thumbnail_url: Optional[str]
    duration_mins: Optional[float]
    language: Optional[str]
    topics: List[str]
    skills_gained: List[str]
    author: Optional[str]
    source: Optional[str]
    avg_rating: float
    completion_rate: float

    class Config:
        from_attributes = True


# ─── Recommendation Schemas ───────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    """One recommended content item returned to the frontend."""
    id: int
    content: ContentResponse
    score: float
    cf_score: float
    cbf_score: float
    rl_bonus: float
    rank: int
    agent_reasoning: Optional[str]
    generated_at: datetime
    is_clicked: bool
    is_dismissed: bool

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    """Full response from GET /recommendations."""
    batch_id: str
    user_id: int
    total: int
    items: List[RecommendationItem]
    agent_thought_steps: List[str]   # streamed thinking for UI
    generated_at: datetime


# ─── Interaction Schema ───────────────────────────────────────────────────────

class LogInteractionRequest(BaseModel):
    content_id: int
    interaction: InteractionType
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    time_spent_mins: Optional[float] = Field(None, ge=0)
    completion_pct: Optional[float] = Field(None, ge=0, le=100)


class LogInteractionResponse(BaseModel):
    success: bool
    message: str
    implicit_score: float


# ─── Agent Run Schemas ────────────────────────────────────────────────────────

class AgentRunStatus(BaseModel):
    batch_id: str
    status: str
    step_log: List[str]
    cf_candidates: int
    cbf_candidates: int
    final_count: int
    llm_tokens_used: int
    duration_ms: int
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Seed Content Schema (admin) ──────────────────────────────────────────────

class CreateContentRequest(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    content_type: ContentType
    difficulty: DifficultyLevel
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_mins: Optional[float] = None
    language: Optional[str] = None
    topics: List[str] = []
    skills_gained: List[str] = []
    prerequisites: List[str] = []
    author: Optional[str] = None
    source: Optional[str] = None