"""One chat turn. The student's message is saved before anything else; the agent then
runs on a worker thread with its own DB session and pushes events into a queue, so the
reply is persisted even when the client stops listening half way."""

import contextvars
import logging
import queue
import re
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import LLMUnavailable, ModelKeyError, ThreadNotFound, TurnInProgress
from app.core.llm_gateway import gateway_chat_model
from app.features.chat.agent import context as chat_context
from app.features.chat.agent.agent import build_agent
from app.features.chat.agent.middleware import (
    FixedReply,
    ForceHint,
    ToolEvents,
    citations_from,
    trace_dict,
)
from app.features.chat.agent.prompts import summary_prompt
from app.features.chat.agent.tools import PASSAGE_CHARS, ToolContext, ToolTrace, build_tools
from app.features.chat.logic import moderation
from app.features.chat.logic.rag.search import search
from app.features.chat.models import ChatMessage, ChatThread

logger = logging.getLogger(__name__)

BUSY_REPLY = "PET is busy right now — please try again in a moment."
EMPTY_REPLY = "Sorry, I couldn't put an answer together. Could you ask that again?"
FAILED = "Sorry — something went wrong. Please try again."
BUSY_FLAG = "busy"
FAILED_FLAG = "error"
TITLE_CHARS = 60
# The last 5 turns verbatim; everything older is in the summary, refreshed every turn.
WINDOW = 10
SUMMARY_BATCH = 2
SUMMARY_LINE_CHARS = 1500
SUMMARY_CHARS = 2000
MAX_GRAPH_STEPS = 60
AUTO_HITS = 4
AUTO_MIN_WORDS = 3
AUTO_QUERY_CHARS = 500
HELP_MAX_WORDS = 6
ARG_CHARS = 200


@dataclass
class ToolStart:
    event: ClassVar[str] = "tool_start"
    name: str
    args: dict


@dataclass
class ToolEnd:
    event: ClassVar[str] = "tool_end"
    trace: dict


@dataclass
class Token:
    event: ClassVar[str] = "token"
    text: str


@dataclass
class Final:
    event: ClassVar[str] = "final"
    message_id: int
    content: str
    citations: list[dict]
    tool_calls: list[dict]
    moderation_flag: str | None = None


@dataclass
class Error:
    event: ClassVar[str] = "error"
    message: str
    code: str = ""


Event = ToolStart | ToolEnd | Token | Final | Error

# One turn per thread at a time, within this process.
_in_flight: set[int] = set()
_in_flight_lock = threading.Lock()


def _claim(thread_id: int) -> None:
    with _in_flight_lock:
        if thread_id in _in_flight:
            raise TurnInProgress("PET is still answering your last message in this chat.")
        _in_flight.add(thread_id)


def _release(thread_id: int) -> None:
    with _in_flight_lock:
        _in_flight.discard(thread_id)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


_PROBLEM_MESSAGE = re.compile(r"^Problem: (.*?)(?: \(problem_id \d+\))?\n.*?\n\nMy question: (.*)$",
                              re.DOTALL)


def _title(content: str) -> str:
    """Code Help's first message carries the whole problem; its name and the question
    make the title, not the start of the statement."""
    match = _PROBLEM_MESSAGE.match(content)
    if match:
        content = f"{match.group(1)} · {match.group(2)}"
    return _clip(" ".join(content.split()), TITLE_CHARS)


_CODE_SPANS = re.compile(r"(```.*?(?:```|$)|`[^`\n]*`)", re.DOTALL)
_HELP_REQUEST = re.compile(r"\b(?:hint|stuck|help|solution|answer|code)\b", re.IGNORECASE)
_MARKER = r"\[\d+(?:,\s*\d+)*\]"
_CITE_MARKERS = re.compile(rf"[ \t]*(?<![\w\])]){_MARKER}(?:{_MARKER})*")
_CITE_LINE = re.compile(rf"[ \t]*(?:[-*][ \t]*)?{_MARKER}")


def _strip_markers(text: str) -> str:
    """For replies that cite nothing found this turn: drops invented source lines such as
    "[1] explains ...", then any [n] left in the prose. Code is never touched."""
    kept, in_fence = [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and _CITE_LINE.match(line):
            continue
        kept.append(line)
    parts = _CODE_SPANS.split("".join(kept))
    return "".join(p if i % 2 else _CITE_MARKERS.sub("", p) for i, p in enumerate(parts))


def _as_message(row) -> BaseMessage:
    return HumanMessage(content=row.content) if row.role == "user" else AIMessage(content=row.content)


def _transcript(rows) -> str:
    return "\n".join(f"{'Student' if r.role == 'user' else 'PET'}: "
                     f"{_clip(r.content, SUMMARY_LINE_CHARS)}"
                     for r in rows if not r.moderation_flag)


def _rollback(db: Session) -> None:
    try:
        db.rollback()
    except Exception:
        logger.exception("rollback after a failed chat turn failed")


def _close(db: Session) -> None:
    try:
        db.close()
    except Exception:
        logger.exception("closing a chat turn's session failed")


class Turn(Iterator[Event]):
    """The events of one turn, ending with Final or Error. The worker owns the turn and
    finishes it whether or not anyone drains this iterator."""

    def __init__(self, job: "_Job"):
        self._events: queue.Queue = queue.Queue()
        self._finished = False
        # The copied context carries the request's model choice into the worker.
        self._worker = threading.Thread(target=contextvars.copy_context().run,
                                        args=(job.run, self._events.put),
                                        name=f"chat-turn-{job.thread_id}")
        self._worker.start()

    def __next__(self) -> Event:
        if self._finished:
            raise StopIteration
        event = self._events.get()
        self._finished = isinstance(event, (Final, Error))
        return event

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the worker is done, including the summary refresh after Final."""
        self._worker.join(timeout)
        return not self._worker.is_alive()


@dataclass
class _Job:
    user_id: int
    thread_id: int
    language: str | None
    flag: str | None
    session_factory: Callable[[], Session]
    model: BaseChatModel | None = None
    summary_model: BaseChatModel | None = None
    tool_ctx_overrides: dict = field(default_factory=dict)

    def run(self, emit: Callable[[Event], None]) -> None:
        """Ends with exactly one Final or Error whatever happens, so a reader never blocks
        forever; the thread takes its next turn as soon as that event is out."""
        started = time.perf_counter()
        db = None
        terminal: Event | None = None
        memory = None
        try:
            db = self.session_factory()
            terminal, memory = self._answer(db, emit, started)
        except ModelKeyError as exc:
            logger.warning("student model failed in thread %s: %s", self.thread_id, exc.code)
            terminal = self._failed(db, started, exc.detail, exc.code)
        except Exception:
            logger.exception("chat turn failed in thread %s", self.thread_id)
            terminal = self._failed(db, started)
        finally:
            if memory is None and db is not None:
                _close(db)
            _release(self.thread_id)
            emit(terminal or Error(FAILED))
        if memory is not None:
            self._remember(db, *memory)
            _close(db)

    def _summary_model(self) -> BaseChatModel:
        return self.summary_model or gateway_chat_model("chat_summary", user_id=self.user_id)

    def _answer(self, db: Session, emit, started: float) -> tuple[Final, tuple | None]:
        if self.flag:
            return self._save(db, moderation.SAFE_REPLY[self.flag], started, flag=self.flag), None

        thread = db.get(ChatThread, self.thread_id)
        plain = thread.mode == "plain"
        summary, upto = thread.summary, thread.summary_upto or 0
        prior = db.query(ChatMessage).filter(ChatMessage.thread_id == thread.id).count() - 1
        start = max(0, prior - WINDOW) if plain else min(upto, max(prior, 0))
        rows = (db.query(ChatMessage.role, ChatMessage.content, ChatMessage.moderation_flag)
                .filter(ChatMessage.thread_id == thread.id)
                .order_by(ChatMessage.created_at, ChatMessage.id)
                .offset(start).all())
        history = [_as_message(r) for r in rows if not r.moderation_flag]

        model = self.model or gateway_chat_model("chat_plain" if plain else "chat",
                                                 user_id=self.user_id)
        traces: list[ToolTrace] = []
        if plain:
            graph = build_agent("plain", None, [], model)
        else:
            ctx = chat_context.load(db, self.user_id, thread, language=self.language)
            tool_ctx = ToolContext(db=db, user_id=self.user_id, language=ctx.language,
                                   last_attempt=ctx.last_attempt, **self.tool_ctx_overrides)
            traces = tool_ctx.traces
            ctx.passages = self._retrieve(db, rows[-1].content if rows else "", tool_ctx, emit)
            events = ToolEvents(tool_ctx, on_start=lambda name, args: emit(ToolStart(name, args)),
                                on_end=lambda trace: emit(ToolEnd(trace)))
            graph = build_agent("pet", ctx, build_tools(tool_ctx), model, self._summary_model(),
                                middleware=[events, FixedReply(tool_ctx), ForceHint(tool_ctx)])
        # Hand the connection back while the model works; tools check one out as needed.
        db.commit()

        try:
            state = graph.invoke({"messages": history}, {"recursion_limit": MAX_GRAPH_STEPS})
        except LLMUnavailable:
            logger.warning("LLM unavailable for chat thread %s; sent the busy reply",
                           self.thread_id)
            _rollback(db)
            return self._save(db, BUSY_REPLY, started, traces=traces, flag=BUSY_FLAG), None

        reply = state["messages"][-1]
        text = (reply.text.strip() if isinstance(reply, AIMessage) else "") or EMPTY_REPLY
        flag = state.get("moderation_flag")
        citations = None if flag else citations_from(traces)
        if not citations:
            text = _strip_markers(text).strip() or EMPTY_REPLY
        produced = [m for m in state["messages"] if isinstance(m, AIMessage) and m.usage_metadata]
        emit(Token(text))

        memory = None
        unsummarised = prior + 2 - WINDOW - upto
        if not plain and unsummarised >= SUMMARY_BATCH:
            target = upto + unsummarised // SUMMARY_BATCH * SUMMARY_BATCH
            memory = (summary, upto, target, _transcript(rows[: target - start]))
        final = self._save(
            db, text, started, traces=traces, flag=flag,
            citations=citations,
            model_name=reply.response_metadata.get("model_name") if isinstance(reply, AIMessage) else None,
            tokens=sum(m.usage_metadata.get("total_tokens", 0) for m in produced) or None,
        )
        return final, memory

    def _retrieve(self, db: Session, message: str, tool_ctx: ToolContext, emit) -> list[dict]:
        """Book passages for the student's message, fetched before the model runs so a
        concept answer never depends on the model choosing to search. Recorded as an
        automatic search_books call so the chip, citations and refs work as usual."""
        if "```" in message:
            return []
        query = _clip(" ".join(message.split()), AUTO_QUERY_CHARS)
        words = query.split()
        if len(words) < AUTO_MIN_WORDS or (len(words) <= HELP_MAX_WORDS
                                           and _HELP_REQUEST.search(query)):
            return []
        started = time.perf_counter()
        try:
            hits = [h for h in search(db, query, language=tool_ctx.language, k=AUTO_HITS,
                                      embed=tool_ctx.embed)
                    if h.score >= settings.RAG_MIN_SCORE]
        except Exception:
            logger.warning("automatic book search failed in thread %s", self.thread_id,
                           exc_info=True)
            _rollback(db)
            return []
        if not hits:
            return []
        args = {"query": _clip(query, ARG_CHARS), "auto": True}
        emit(ToolStart("search_books", args))
        cites = [{"title": h.source_title, "chapter": h.chapter, "section": h.section,
                  "url": h.url} for h in hits]
        citations = [c for i, c in enumerate(cites) if c not in cites[:i]]
        trace = ToolTrace(name="search_books", args=args, summary=f"{len(citations)} sources",
                          ok=True, ms=int((time.perf_counter() - started) * 1000),
                          citations=citations)
        tool_ctx.traces.append(trace)
        emit(ToolEnd(trace_dict(trace)))
        return [{"ref": citations.index(cite) + 1, **cite, "text": _clip(h.text, PASSAGE_CHARS)}
                for h, cite in zip(hits, cites)]

    def _save(self, db: Session, text: str, started: float, *, traces: list[ToolTrace] = (),
              flag: str | None = None, citations: list[dict] | None = None,
              model_name: str | None = None, tokens: int | None = None) -> Final:
        calls = [trace_dict(t) for t in traces]
        message = ChatMessage(
            thread_id=self.thread_id, user_id=self.user_id, role="assistant", content=text,
            tool_calls=calls or None, citations=citations or None, moderation_flag=flag,
            model=model_name, tokens=tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        db.add(message)
        db.get(ChatThread, self.thread_id).updated_at = _now()
        db.flush()
        message_id = message.id
        db.commit()
        return Final(message_id=message_id, content=text, citations=citations or [],
                     tool_calls=calls, moderation_flag=flag)

    def _failed(self, db: Session | None, started: float, message: str = FAILED,
                code: str = "") -> Error:
        if db is not None:
            _rollback(db)
            try:
                self._save(db, message, started, flag=FAILED_FLAG)
            except Exception:
                logger.exception("could not save the failure reply in thread %s", self.thread_id)
                _rollback(db)
        return Error(message, code)

    def _remember(self, db: Session, previous: str | None, upto: int, target: int,
                  transcript: str) -> None:
        """Folds messages [upto, target) into the summary. Guarded on the old marker, so
        a fold that lost a race changes nothing and the next turn catches up instead."""
        try:
            summary = previous
            if transcript:
                reply = self._summary_model().invoke(
                    [HumanMessage(summary_prompt(previous, transcript))])
                summary = _clip(reply.text.strip(), SUMMARY_CHARS)
                if not summary:
                    return
            (db.query(ChatThread)
             .filter(ChatThread.id == self.thread_id, ChatThread.summary_upto == upto)
             .update({ChatThread.summary: summary, ChatThread.summary_upto: target},
                     synchronize_session=False))
            db.commit()
        except Exception:
            logger.warning("could not refresh the summary of chat thread %s", self.thread_id,
                           exc_info=True)
            _rollback(db)


def _drop_failed_attempt(db: Session, thread_id: int, content: str) -> None:
    """Try again resends the same message after a busy or failed reply; that exchange is
    replaced, not kept beside the new one."""
    failed, asked = (db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id)
                     .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                     .limit(2).all() + [None, None])[:2]
    if (failed is not None and asked is not None and failed.role == "assistant"
            and failed.moderation_flag in (BUSY_FLAG, FAILED_FLAG)
            and asked.role == "user" and asked.content.strip() == content.strip()):
        db.delete(failed)
        db.delete(asked)


def run_turn(db: Session, user_id: int, thread_id: int, content: str,
             language: str | None = None, *, model: BaseChatModel | None = None,
             summary_model: BaseChatModel | None = None, tool_ctx_overrides: dict | None = None,
             session_factory: Callable[[], Session] | None = None) -> Turn:
    """Saves the message and starts the turn. Raises ThreadNotFound (missing or someone
    else's thread) or TurnInProgress (a reply is still running) before saving anything."""
    thread = db.get(ChatThread, thread_id)
    if thread is None or thread.user_id != user_id:
        raise ThreadNotFound("Chat thread not found.")
    _claim(thread_id)
    try:
        _drop_failed_attempt(db, thread_id, content)
        flag = moderation.check(content).category
        db.add(ChatMessage(thread_id=thread.id, user_id=user_id, role="user", content=content,
                           moderation_flag=flag))
        if not thread.title and not flag:
            thread.title = _title(content)
        thread.updated_at = _now()
        db.commit()
        return Turn(_Job(
            user_id=user_id, thread_id=thread_id, language=language, flag=flag,
            session_factory=session_factory or sessionmaker(bind=db.get_bind(), autoflush=False),
            model=model, summary_model=summary_model,
            tool_ctx_overrides=tool_ctx_overrides or {},
        ))
    except BaseException:
        _release(thread_id)
        raise
