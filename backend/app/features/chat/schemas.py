from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints


class ThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: str
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    citations: list[dict[str, Any]] | None = None
    moderation_flag: str | None = None
    thumbs: str | None = None
    model: str | None = None
    tokens: int | None = None
    latency_ms: int | None = None
    created_at: datetime | None = None


class ThreadDetailOut(BaseModel):
    thread: ThreadOut
    messages: list[MessageOut]


class CreateThreadIn(BaseModel):
    mode: Literal["pet", "plain"] | None = None


class SendMessageIn(BaseModel):
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
    language: Literal["c", "cpp", "python"] | None = None


class ThumbsIn(BaseModel):
    value: Literal["up", "down"] | None
