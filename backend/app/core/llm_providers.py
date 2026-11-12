"""Every provider is reached through its OpenAI-compatible endpoint, so one client type
serves them all; only the base URL, the key header for listing models, and the error
wording differ."""

import os
import re
from dataclasses import dataclass

import httpx
from openai import APIConnectionError, OpenAIError

from app.core import llm
from app.core.exceptions import ModelKeyError
from app.core.llm_choice import Choice

_LOCAL_HOST = "host.docker.internal" if os.path.exists("/.dockerenv") else "localhost"


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    base_url: str
    needs_key: bool = True
    local: bool = False


PROVIDERS: dict[str, Provider] = {p.id: p for p in (
    Provider("nvidia", "NVIDIA NIM", llm.NVIDIA_BASE_URL),
    Provider("openai", "OpenAI", "https://api.openai.com/v1"),
    Provider("anthropic", "Anthropic", "https://api.anthropic.com/v1"),
    Provider("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai"),
    Provider("groq", "Groq", "https://api.groq.com/openai/v1"),
    Provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1"),
    Provider("ollama", "Ollama", f"http://{_LOCAL_HOST}:11434/v1", needs_key=False, local=True),
    Provider("lmstudio", "LM Studio", f"http://{_LOCAL_HOST}:1234/v1", needs_key=False, local=True),
    Provider("custom", "Custom (OpenAI-compatible)", "", needs_key=False, local=True),
)}

SUFFIX = " Change your key or model in the Model window."
_KEY_LIKE = re.compile(r"(sk-|sk_|nvapi-|gsk_|AIza|xai-)[A-Za-z0-9_\-]{6,}")
_TOKEN_MARKERS = ("context length", "context_length", "maximum context", "too many tokens",
                  "token limit", "reduce the length", "max_tokens", "too long")
_CREDIT_MARKERS = ("quota", "credit", "billing", "insufficient", "balance", "payment")


def label(provider_id: str) -> str:
    provider = PROVIDERS.get(provider_id)
    return provider.label if provider else provider_id


def build_client(choice: Choice, *, temperature: float, max_tokens: int, timeout: float):
    extra = ({"extra_body": {"chat_template_kwargs": {"thinking": False}}}
             if choice.provider == "nvidia" else {})
    try:
        return llm.ChatOpenAI(
            model=choice.model, api_key=choice.api_key or "none", base_url=choice.base_url,
            temperature=temperature, max_completion_tokens=max_tokens,
            max_retries=0, timeout=timeout, **extra)
    except OpenAIError as exc:
        raise classify(exc, choice) from exc


_CONTEXT_KEYS = ("context_length", "context_window", "max_context_length", "max_input_tokens",
                 "input_token_limit")


def _context(row: dict) -> int | None:
    for key in _CONTEXT_KEYS:
        value = row.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return None


def list_models(choice: Choice) -> dict[str, int | None]:
    """Model id → context window, where the provider reports one."""
    if choice.provider == "anthropic":
        headers = {"x-api-key": choice.api_key, "anthropic-version": "2023-06-01"}
    else:
        headers = {"Authorization": f"Bearer {choice.api_key}"} if choice.api_key else {}
    try:
        response = httpx.get(f"{choice.base_url.rstrip('/')}/models", headers=headers, timeout=15)
        response.raise_for_status()
        rows = response.json().get("data", [])
    except Exception as exc:
        raise classify(exc, choice) from exc
    return {str(row["id"]).removeprefix("models/"): _context(row)
            for row in sorted(rows, key=lambda r: str(r.get("id", ""))) if row.get("id")}


def redact(text: str, key: str) -> str:
    if key:
        text = text.replace(key, "[key]")
    return _KEY_LIKE.sub("[key]", text)[:300]


def _status(exc: Exception) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


def classify(exc: Exception, choice: Choice) -> ModelKeyError:
    name, model = label(choice.provider), choice.model or "This model"
    status = _status(exc)
    text = str(exc).lower()
    if isinstance(exc, (APIConnectionError, httpx.TransportError)):
        code, message = "provider_unreachable", f"Couldn't reach {name}."
    elif status in (401, 403):
        code, message = "invalid_key", f"Your {name} key was rejected."
    elif status == 402 or (status == 429 and any(m in text for m in _CREDIT_MARKERS)):
        code, message = "out_of_credit", f"Your {name} account is out of credit."
    elif status == 429:
        code, message = "rate_limited", f"Your {name} key hit its rate limit. Wait a minute or switch model."
    elif any(m in text for m in _TOKEN_MARKERS):
        code, message = ("too_many_tokens",
                         f"This request is too long for {model}. Pick a model with a larger context.")
    elif status == 404 or "model_not_found" in text or "does not exist" in text:
        code, message = "model_not_found", f"{model} isn't available on your {name} account."
    elif status is not None and status >= 500:
        code, message = "provider_unreachable", f"{name} is having problems right now."
    else:
        code, message = "provider_error", f"{name} returned an error."
    return ModelKeyError(code, message + SUFFIX, redact(str(exc), choice.api_key))
