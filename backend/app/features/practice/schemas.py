from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.features.gamification.schemas import AwardOut

# ─── Assessment (next item, MCQ, debug) ─────────────────────────────────────


class NextItemResponse(BaseModel):
    item_type: str
    topic: str
    difficulty: str
    item: Dict[str, Any]
    reason: str


class McqAnswerRequest(BaseModel):
    chosen_index: int


class McqAnswerResponse(BaseModel):
    correct: bool
    chosen_index: int
    answer_index: int
    misconception: Optional[str] = None
    explanation: Optional[str] = None
    mastery_after: Optional[float] = None
    awards: List[AwardOut] = []


class DebugSubmitRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000)


class DebugSubmitResponse(BaseModel):
    fixed: bool
    verdict: str
    tests_passed: int
    tests_total: int
    failing_input: Optional[str] = None
    failing_expected: Optional[str] = None
    failing_actual: Optional[str] = None
    mastery_after: Optional[float] = None
    awards: List[AwardOut] = []


# ─── Practice sessions ──────────────────────────────────────────────────────


class CurrentOut(BaseModel):
    id: Optional[int] = None
    graded_count: int = 0


class PendingOut(BaseModel):
    id: int
    ended_at: datetime
    end_reason: str
    solved: int
    topics: List[str]


class TypeCountOut(BaseModel):
    tried: int
    solved: int


class TopicChangeOut(BaseModel):
    topic: str
    before: float
    after: float
    band_after: str


class MistakeOut(BaseModel):
    misconception: str
    count: int


class SessionFeedbackOut(BaseModel):
    summary: str
    work_on_next: List[str] = []


class FeedbackRequest(BaseModel):
    retry: bool = False


class WrapUpOut(BaseModel):
    id: int
    language: str
    started_at: datetime
    ended_at: datetime
    end_reason: str
    # Set for a topic run: the one topic the student chose.
    topic: Optional[str] = None
    duration_s: int
    by_type: Dict[str, TypeCountOut]
    topics: List[TopicChangeOut]
    hints: Dict[int, int]
    mistakes: List[MistakeOut]
    stuck_topics: List[str]
    awards: Optional[List[AwardOut]] = None
    feedback: Optional[SessionFeedbackOut] = None
    feedback_status: str


# ─── Topic practice ─────────────────────────────────────────────────────────


class ExplanationOut(BaseModel):
    topic: str
    language: str
    markdown: str


class RunOut(BaseModel):
    session_id: int
    total: int


class RunStepOut(BaseModel):
    session_id: int
    position: int
    total: int
    done: bool
    item_type: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    item: Optional[Dict[str, Any]] = None


class TheoryAnswerRequest(BaseModel):
    answer: str = Field("", max_length=2000)


class TheoryAnswerOut(BaseModel):
    score: float
    key_points: List[str]
    points_present: List[bool]
    model_answer: str
    feedback: str
    mastery_after: Optional[float] = None
    awards: List[AwardOut] = []
