# Endpoints, under /api/v1/chat:
#   POST  /threads                       start a new chat thread
#   GET   /threads                       my recent threads, newest first
#   GET   /threads/{thread_id}           one thread with all its messages
#   POST  /threads/{thread_id}/messages  send a message; the reply streams back as SSE
#   PATCH /messages/{message_id}/thumbs  thumbs up / down on an assistant reply

"""The chatbot over HTTP. A reply streams back as Server-Sent Events while the turn runs on
its own worker, so a student who closes the tab still finds the reply saved."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import ThreadNotFound
from app.features.accounts.models import User
from app.features.chat.models import ChatMessage, ChatThread
from app.features.chat.schemas import (
    CreateThreadIn,
    MessageOut,
    SendMessageIn,
    ThreadDetailOut,
    ThreadOut,
    ThumbsIn,
)
from app.features.chat.service import Event, Turn, run_turn

router = APIRouter(prefix="/chat", tags=["Chat"])

THREAD_LIST_CAP = 50
PING_SECONDS = 15
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

_pullers = ThreadPoolExecutor(max_workers=64, thread_name_prefix="chat-sse")


def get_chat_runner() -> Callable[..., Turn]:
    return run_turn


def _own_thread(db: Session, user_id: int, thread_id: int) -> ChatThread:
    thread = db.get(ChatThread, thread_id)
    if thread is None or thread.user_id != user_id:
        raise ThreadNotFound("Chat thread not found.")
    return thread


def _frame(event: Event) -> str:
    data = json.dumps(asdict(event), ensure_ascii=False, default=str)
    return f"event: {event.event}\ndata: {data}\n\n"


async def _stream(turn: Turn) -> AsyncIterator[str]:
    """A pull still waiting when a ping falls due is kept rather than cancelled, so no
    event is lost; after a hang-up it is abandoned and the worker carries on."""
    loop = asyncio.get_running_loop()
    pending = None
    while True:
        if pending is None:
            pending = loop.run_in_executor(_pullers, next, turn, None)
        done, _ = await asyncio.wait({pending}, timeout=PING_SECONDS)
        if not done:
            yield ": ping\n\n"
            continue
        event, pending = pending.result(), None
        if event is None:
            return
        yield _frame(event)


@router.post("/threads", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(
    body: CreateThreadIn | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Plain mode is the study's comparison arm; outside debug only study mode may grant it.
    mode = "plain" if body and body.mode == "plain" and settings.DEBUG else "pet"
    thread = ChatThread(user_id=current_user.id, mode=mode)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.get("/threads", response_model=list[ThreadOut])
def list_threads(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return (db.query(ChatThread)
            .filter(ChatThread.user_id == current_user.id)
            .order_by(ChatThread.updated_at.desc(), ChatThread.id.desc())
            .limit(THREAD_LIST_CAP).all())


@router.get("/threads/{thread_id}", response_model=ThreadDetailOut)
def get_thread(
    thread_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    thread = _own_thread(db, current_user.id, thread_id)
    messages = (db.query(ChatMessage)
                .filter(ChatMessage.thread_id == thread.id)
                .order_by(ChatMessage.created_at, ChatMessage.id).all())
    return ThreadDetailOut(thread=ThreadOut.model_validate(thread),
                           messages=[MessageOut.model_validate(m) for m in messages])


@router.post("/threads/{thread_id}/messages")
def send_message(
    thread_id: int,
    body: SendMessageIn,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    runner: Callable[..., Turn] = Depends(get_chat_runner),
):
    """Streams `tool_start`, `tool_end`, `token`, then `final` or `error`. The thread is
    checked and the message saved before the stream opens, so a stranger's thread is a
    plain 404."""
    turn = runner(db, current_user.id, thread_id, body.content, body.language)
    return StreamingResponse(_stream(turn), media_type="text/event-stream",
                             headers=SSE_HEADERS)


@router.patch("/messages/{message_id}/thumbs")
def set_thumbs(
    message_id: int,
    body: ThumbsIn,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    message = (db.query(ChatMessage)
               .filter(ChatMessage.id == message_id,
                       ChatMessage.user_id == current_user.id,
                       ChatMessage.role == "assistant")
               .first())
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found.")
    message.thumbs = body.value
    db.commit()
    return {"ok": True}
