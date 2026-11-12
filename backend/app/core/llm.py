import time
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI
from openai import OpenAIError
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import LLMUnavailable

_RATE_LIMIT_MARKERS = (
    "429", "resource has been exhausted", "quota", "rate limit",
    "resourceexhausted", "unavailable", "503", "deadline",
)


@dataclass(frozen=True)
class LLMUsage:
    tokens: int
    latency_ms: int
    model: str


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _nvidia(model: str, temperature: float, *, api_key: str | None = None,
            thinking: bool = False, max_tokens: int | None = None,
            max_retries: int | None = None, timeout: float | None = None) -> ChatOpenAI:
    transport = {key: value for key, value in
                 (("max_retries", max_retries), ("timeout", timeout)) if value is not None}
    try:
        return ChatOpenAI(
            **transport,
            model=model,
            api_key=settings.NVIDIA_API_KEY if api_key is None else api_key,
            base_url=NVIDIA_BASE_URL,
            temperature=temperature,
            max_completion_tokens=max_tokens or settings.LLM_MAX_OUTPUT_TOKENS,
            # These models reason before answering, and on a structured call they spend
            # the entire budget thinking and return nothing to parse. Off unless a
            # purpose has been shown to survive it.
            extra_body={"chat_template_kwargs": {"thinking": thinking}},
        )
    except OpenAIError as exc:
        # The client refuses to be built at all — no credentials, unusable base URL.
        # Narrow on purpose: a bad keyword or a wrong type fails pydantic validation
        # instead, and that is a bug in us, not an outage to degrade around.
        raise LLMUnavailable(f"LLM client could not be built: {exc}") from exc


def get_chat_model(temperature: float = 0.0) -> ChatOpenAI:
    """Prose: feedback, explanations, conversation."""
    return _nvidia(settings.NVIDIA_MODEL, temperature)


def get_codegen_model(temperature: float = 0.0) -> ChatOpenAI:
    """Code inside a JSON field, a stricter requirement than prose.

    Kept separate because the prose model cannot do this: it strips the line breaks
    out of a program returned in a JSON string, leaving one unparseable line. Plain
    completions from it are fine, so it is the structured-output path rather than
    the model being weak.
    """
    return _nvidia(settings.NVIDIA_CODEGEN_MODEL, temperature)


def structured(model, schema: type[BaseModel]):
    # Some OpenAI-compatible endpoints (Anthropic's) ignore response_format; tool calls
    # are the one structured channel every provider honours.
    base_url = getattr(model, "openai_api_base", None)
    if base_url and base_url != NVIDIA_BASE_URL:
        return model.with_structured_output(schema, include_raw=True, method="function_calling")
    return model.with_structured_output(schema, include_raw=True)


def _is_rate_limited(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _RATE_LIMIT_MARKERS)


def _read_usage(raw: Any) -> int:
    metadata = getattr(raw, "usage_metadata", None) or {}
    try:
        return int(metadata.get("total_tokens", 0))
    except (AttributeError, TypeError, ValueError):
        return 0


def invoke_with_retry(runnable, payload, *, attempts: int | None = None,
                      model: str | None = None) -> tuple[Any, LLMUsage]:
    budget = attempts or settings.LLM_MAX_ATTEMPTS
    started = time.monotonic()
    last: Exception | None = None

    for attempt in range(budget):
        try:
            result = runnable.invoke(payload)
        except Exception as exc:
            last = exc
            if not _is_rate_limited(exc):
                break
            if attempt + 1 < budget:
                time.sleep(2 ** attempt)
            continue

        elapsed_ms = int((time.monotonic() - started) * 1000)
        usage_model = model or settings.NVIDIA_MODEL
        if isinstance(result, dict):
            return result.get("parsed"), LLMUsage(
                tokens=_read_usage(result.get("raw")),
                latency_ms=elapsed_ms,
                model=usage_model,
            )
        return result, LLMUsage(tokens=0, latency_ms=elapsed_ms, model=usage_model)

    raise LLMUnavailable(f"LLM call failed after {budget} attempt(s): {last}")
