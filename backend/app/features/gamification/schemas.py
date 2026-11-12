from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AwardOut(BaseModel):
    kind: str
    code: str
    title: str
    message: str
    points: int
    created_at: Optional[datetime] = None


class TopicProgress(BaseModel):
    topic: str
    label: str
    band: str
    mastery: float
    next_band: Optional[str] = None
    gap_to_next: Optional[float] = None


class Window(BaseModel):
    points: int = 0
    solved: int = 0
    level_ups: int = 0


class SelfBoard(BaseModel):
    last_7: Window = Window()
    prev_7: Window = Window()


class GamificationSummary(BaseModel):
    mode: str
    points: int = 0
    level: int = 1
    topics: List[TopicProgress] = []
    badges: List[AwardOut] = []
    self_board: SelfBoard = SelfBoard()
    recent: List[AwardOut] = []
