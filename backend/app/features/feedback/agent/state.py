from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.features.feedback.models import FeedbackTone, FeedbackType


class FeedbackState(BaseModel):
    """Pipeline state for the Feedback Agent. `steps` is persisted onto the report
    and shown to the student, so every entry is written to be read by one."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: Any
    user_id: int
    evaluation_id: Optional[int] = None
    tone: FeedbackTone = FeedbackTone.ENCOURAGING
    started_ms: int = 0

    # Injection point. None in production; tests supply a fake so the graph runs
    # with no network.
    synthesise_runnable: Any = None

    user_ctx: dict = {}
    eval_ctx: Optional[dict] = None
    events: list[Any] = []
    activity_ctx: Optional[dict] = None
    feedback_type: Optional[FeedbackType] = None

    patterns: dict = {}
    narrative: Any = None
    pattern_only: bool = False
    tokens_used: int = 0

    profile_updates: dict = {}
    steps: list[str] = []
    report: Any = None

    def log(self, message: str) -> None:
        self.steps.append(message)
