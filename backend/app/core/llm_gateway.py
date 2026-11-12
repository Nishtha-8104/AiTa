"""Every LLM call goes through here: per-key rate limits, key rotation, a fallback
model, a caller-supplied template as the last resort, and one `llm_calls` row each."""

import itertools
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Literal, Sequence

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import LLMUnavailable, ModelKeyError
from app.core.llm import _is_rate_limited, _nvidia, structured
from app.core.llm_call import LLMCall
from app.core.llm_choice import Choice, current_choice, server_choice
from app.core.llm_providers import build_client, classify

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Purpose:
    name: str
    temperature: float
    max_tokens: int
    model_setting: str = "NVIDIA_MODEL"
    deadline_s: float | None = None

    @property
    def model(self) -> str:
        return getattr(settings, self.model_setting)

    @property
    def deadline(self) -> float:
        return settings.LLM_QUEUE_DEADLINE_S if self.deadline_s is None else self.deadline_s


def _purpose(name: str, temperature: float, *, max_tokens: int | None = None,
             model_setting: str = "NVIDIA_MODEL", deadline_s: float | None = None) -> Purpose:
    return Purpose(name, temperature, max_tokens or settings.LLM_MAX_OUTPUT_TOKENS,
                   model_setting, deadline_s)


PURPOSES: dict[str, Purpose] = {p.name: p for p in (
    _purpose("explain", 0.3, deadline_s=60),
    _purpose("feedback", 0.4, deadline_s=60),
    _purpose("session_feedback", 0.4, deadline_s=60),
    _purpose("hint", 0.4, deadline_s=60),
    _purpose("hint_check", 0.0, max_tokens=512, deadline_s=30),
    _purpose("assessment_gen", 0.7, deadline_s=120),
    _purpose("problem_gen", 0.7, deadline_s=120),
    _purpose("test_gen", 0.0, model_setting="NVIDIA_CODEGEN_MODEL", deadline_s=120),
    _purpose("solution_port", 0.0, model_setting="NVIDIA_CODEGEN_MODEL", deadline_s=60),
    _purpose("chat", 0.3, deadline_s=45),
    _purpose("chat_summary", 0.0, max_tokens=1024),
    _purpose("chat_plain", 0.3, deadline_s=45),
    _purpose("eval", 0.0, deadline_s=120),
    _purpose("onboarding_judge", 0.0, max_tokens=1024, deadline_s=45),
    _purpose("theory_judge", 0.0, max_tokens=512, deadline_s=45),
)}


@dataclass
class GatewayResult:
    value: Any
    status: Literal["ok", "fallback", "template"]
    model: str
    key_slot: int | None
    latency_ms: int
    queued_ms: int
    tokens: int


class TokenBucket:
    def __init__(self, rpm: int, clock: Callable[[], float] = time.monotonic):
        self.capacity = float(rpm)
        self.rate = rpm / 60.0
        self.clock = clock
        self.tokens = float(rpm)
        self.updated = clock()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now

    def try_take(self) -> bool:
        with self._lock:
            self._refill()
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

    def wait_time(self) -> float:
        with self._lock:
            self._refill()
            return 0.0 if self.tokens >= 1 else (1 - self.tokens) / self.rate


class RedisBucket:
    """Fixed one-minute window shared by every worker process."""

    def __init__(self, client, slot: int, rpm: int, clock: Callable[[], float] = time.time):
        self.client = client
        self.slot = slot
        self.rpm = rpm
        self.clock = clock

    def try_take(self) -> bool:
        key = f"llm:bucket:{self.slot}:{int(self.clock() // 60)}"
        count = self.client.incr(key)
        if count == 1:
            self.client.expire(key, 60)
        return count <= self.rpm

    def wait_time(self) -> float:
        return 60 - self.clock() % 60


def _key_for(slot: int) -> str:
    return settings.NVIDIA_API_KEY if slot == 0 else settings.NVIDIA_API_KEY_2


_MIN_CALL_S = 0.5
# A hung primary call must not eat the fallback model's share of the deadline.
_PRIMARY_SHARE = 0.6


def _default_factory(model: str, api_key: str, purpose: Purpose, *, timeout: float):
    # The SDK's own retries honour Retry-After for up to a minute, which would blow the
    # deadline; rotation and fallback here are the retry policy.
    return _nvidia(model, purpose.temperature, api_key=api_key,
                   max_tokens=purpose.max_tokens,
                   max_retries=0, timeout=timeout)


def _is_retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    return _is_rate_limited(exc) or (isinstance(status, int) and status >= 500)


def _usage(raw: Any) -> tuple[int, int]:
    metadata = getattr(raw, "usage_metadata", None) or {}
    try:
        return int(metadata.get("input_tokens", 0)), int(metadata.get("output_tokens", 0))
    except (AttributeError, TypeError, ValueError):
        return 0, 0


Call = Callable[[Any], tuple[Any, Any]]


class Gateway:
    def __init__(self, *, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep,
                 session_factory: Callable[[], Any] | None = None,
                 model_factory: Callable[..., Any] | None = None,
                 choice_factory: Callable[..., Any] | None = None):
        self.clock = clock
        self.sleep = sleep
        self.session_factory = session_factory
        self.model_factory = model_factory or _default_factory
        self.choice_factory = choice_factory or build_client
        self._buckets: dict[int, Any] = {}
        self._redis_down = False
        self._turn = itertools.count()
        self._lock = threading.Lock()

    def _bucket(self, slot: int):
        with self._lock:
            if slot not in self._buckets:
                self._buckets[slot] = self._new_bucket(slot)
            return self._buckets[slot]

    def _new_bucket(self, slot: int):
        if settings.REDIS_URL and not self._redis_down:
            try:
                import redis

                client = redis.Redis.from_url(settings.REDIS_URL)
                return RedisBucket(client, slot, settings.NVIDIA_RPM)
            except Exception:
                self._abandon_redis()
        return TokenBucket(settings.NVIDIA_RPM, self.clock)

    def _abandon_redis(self) -> None:
        if not self._redis_down:
            self._redis_down = True
            logger.warning("Redis rate limiter unavailable; using in-process buckets",
                           exc_info=True)
        self._buckets = {s: b for s, b in self._buckets.items()
                         if not isinstance(b, RedisBucket)}

    def _take(self, slot: int) -> bool:
        try:
            return self._bucket(slot).try_take()
        except Exception:
            with self._lock:
                self._abandon_redis()
            return self._bucket(slot).try_take()

    def _wait_time(self, slot: int) -> float:
        try:
            return self._bucket(slot).wait_time()
        except Exception:
            with self._lock:
                self._abandon_redis()
            return self._bucket(slot).wait_time()

    @staticmethod
    def _slots() -> list[int]:
        return [0, 1] if settings.NVIDIA_API_KEY_2 else [0]

    def _rotation(self) -> list[int]:
        slots = self._slots()
        with self._lock:
            start = next(self._turn) % len(slots)
        return slots[start:] + slots[:start]

    def _acquire(self, slots: Sequence[int], deadline: float) -> tuple[int | None, float]:
        began = self.clock()
        while True:
            for slot in slots:
                if self._take(slot):
                    return slot, self.clock() - began
            remaining = deadline - self.clock()
            if remaining <= 0:
                return None, self.clock() - began
            wait = min(self._wait_time(slot) for slot in slots)
            self.sleep(max(0.01, min(wait, remaining, 0.25)))

    def run(self, purpose: str, call: Call, *, user_id: int | None = None,
            template: str | None = None, model_factory=None) -> GatewayResult:
        spec = PURPOSES[purpose]
        choice = current_choice() or server_choice()
        if choice is not None:
            return self._run_choice(spec, call, user_id, choice)
        if not settings.NVIDIA_API_KEY:
            raise ModelKeyError("no_model", "No AI model is set up yet. Choose one in the Model window.")
        factory = model_factory or self.model_factory
        primary = spec.model
        start = self.clock()
        deadline = start + spec.deadline
        primary_until = (start + spec.deadline * _PRIMARY_SHARE
                         if settings.NVIDIA_FALLBACK_MODEL else deadline)
        queued = 0.0
        last: Exception | None = None

        def attempt(model: str, slot: int, status: str, until: float) -> GatewayResult:
            began = self.clock()
            chat = factory(model, _key_for(slot), spec, timeout=until - began)
            value, raw = call(chat)
            tokens_in, tokens_out = _usage(raw)
            result = GatewayResult(
                value=value, status=status, model=model, key_slot=slot,
                latency_ms=int((self.clock() - began) * 1000),
                queued_ms=int(queued * 1000), tokens=tokens_in + tokens_out,
            )
            self._log(purpose=spec.name, status=status, model=model, key_slot=slot,
                      latency_ms=result.latency_ms, queued_ms=result.queued_ms,
                      tokens_in=tokens_in, tokens_out=tokens_out, user_id=user_id)
            return result

        remaining = self._rotation()
        while remaining:
            slot, waited = self._acquire(remaining, primary_until)
            queued += waited
            if slot is None or primary_until - self.clock() < _MIN_CALL_S:
                break
            remaining.remove(slot)
            try:
                return attempt(primary, slot, "ok", primary_until)
            except AssertionError:
                raise
            except Exception as exc:
                last = exc
                if not _is_retryable(exc):
                    break

        if settings.NVIDIA_FALLBACK_MODEL and deadline - self.clock() >= _MIN_CALL_S:
            slot, waited = self._acquire(self._slots(), deadline)
            queued += waited
            if slot is not None and deadline - self.clock() >= _MIN_CALL_S:
                try:
                    return attempt(settings.NVIDIA_FALLBACK_MODEL, slot, "fallback", deadline)
                except AssertionError:
                    raise
                except Exception as exc:
                    last = exc

        elapsed_ms = int((self.clock() - start) * 1000)
        reason = last or "no rate-limit token before the deadline"
        status = "error" if template is None else "template"
        self._log(purpose=spec.name, status=status, model=primary if template is None else "",
                  key_slot=None, latency_ms=elapsed_ms, queued_ms=int(queued * 1000),
                  user_id=user_id, error=str(reason)[:2000])
        if template is None:
            raise LLMUnavailable(f"LLM gateway exhausted for {purpose}: {reason}")
        return GatewayResult(value=template, status="template", model="", key_slot=None,
                             latency_ms=elapsed_ms, queued_ms=int(queued * 1000), tokens=0)

    def _run_choice(self, spec: Purpose, call: Call, user_id: int | None,
                    choice: Choice) -> GatewayResult:
        """No rotation, fallback or template: a failing student key must be seen."""
        key_source = "own" if choice.source == "own" else "pet"
        began = self.clock()
        try:
            chat = self.choice_factory(choice, temperature=spec.temperature,
                                       max_tokens=spec.max_tokens, timeout=spec.deadline)
            value, raw = call(chat)
        except AssertionError:
            raise
        except Exception as exc:
            error = exc if isinstance(exc, ModelKeyError) else classify(exc, choice)
            self._log(purpose=spec.name, status="error", model=choice.model,
                      provider=choice.provider, key_source=key_source, key_slot=None,
                      latency_ms=int((self.clock() - began) * 1000), queued_ms=0,
                      user_id=user_id, error=f"{error.code}: {error.provider_message}")
            if choice.source == "own":
                raise error from exc
            raise LLMUnavailable(f"LLM gateway failed for {spec.name}: {error.detail}") from exc
        tokens_in, tokens_out = _usage(raw)
        latency_ms = int((self.clock() - began) * 1000)
        self._log(purpose=spec.name, status="ok", model=choice.model, provider=choice.provider,
                  key_source=key_source, key_slot=None, latency_ms=latency_ms, queued_ms=0,
                  tokens_in=tokens_in, tokens_out=tokens_out, user_id=user_id)
        return GatewayResult(value=value, status="ok", model=choice.model, key_slot=None,
                             latency_ms=latency_ms, queued_ms=0, tokens=tokens_in + tokens_out)

    def _log(self, **fields: Any) -> None:
        try:
            with (self.session_factory or SessionLocal)() as db:
                db.add(LLMCall(**fields))
                db.commit()
        except Exception:
            logger.exception("could not write llm_calls row for %s", fields.get("purpose"))


_gateway = Gateway()


def invoke(purpose: str, payload, *, schema: type[BaseModel] | None = None,
           user_id: int | None = None, template: str | None = None,
           model_factory=None) -> GatewayResult:
    def call(chat):
        if schema is None:
            result = chat.invoke(payload)
            return result, result
        result = structured(chat, schema).invoke(payload)
        return result.get("parsed"), result.get("raw")

    return _gateway.run(purpose, call, user_id=user_id, template=template,
                        model_factory=model_factory)


class GatewayChatModel(BaseChatModel):
    purpose: str
    user_id: int | None = None
    tools: list[Any] = []
    tool_kwargs: dict[str, Any] = {}

    @property
    def _llm_type(self) -> str:
        return "pet-gateway"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "GatewayChatModel":
        return self.model_copy(update={"tools": list(tools), "tool_kwargs": kwargs})

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,
                  run_manager: CallbackManagerForLLMRun | None = None,
                  **kwargs: Any) -> ChatResult:
        options = {**kwargs, "stop": stop} if stop else kwargs

        def call(chat):
            runnable = chat.bind_tools(self.tools, **self.tool_kwargs) if self.tools else chat
            message = runnable.invoke(messages, **options)
            return message, message

        result = _gateway.run(self.purpose, call, user_id=self.user_id)
        return ChatResult(generations=[ChatGeneration(message=result.value)])


def gateway_chat_model(purpose: str, *, user_id: int | None = None) -> BaseChatModel:
    if purpose not in PURPOSES:
        raise KeyError(f"unknown LLM purpose: {purpose}")
    return GatewayChatModel(purpose=purpose, user_id=user_id)
