import pytest
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import LLMUnavailable
from app.core.llm import LLMUsage, get_chat_model, get_codegen_model, invoke_with_retry


class FakeRunnable:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeRaw:
    def __init__(self, tokens):
        self.usage_metadata = {"total_tokens": tokens}


def ok(value, tokens=42):
    return {"parsed": value, "raw": FakeRaw(tokens)}


def test_returns_parsed_value_and_usage():
    runnable = FakeRunnable([ok("hello", tokens=17)])
    value, usage = invoke_with_retry(runnable, "prompt")
    assert value == "hello"
    assert isinstance(usage, LLMUsage)
    assert usage.tokens == 17
    assert usage.latency_ms >= 0
    assert usage.model


def test_retries_on_rate_limit_then_succeeds():
    runnable = FakeRunnable([Exception("429 Resource has been exhausted"), ok("later")])
    value, _ = invoke_with_retry(runnable, "prompt")
    assert value == "later"
    assert runnable.calls == 2


def test_gives_up_after_attempts_and_raises_domain_error():
    runnable = FakeRunnable([Exception("429 quota exceeded")] * 3)
    with pytest.raises(LLMUnavailable):
        invoke_with_retry(runnable, "prompt", attempts=2)
    assert runnable.calls == 2


def test_non_rate_limit_error_is_not_retried():
    runnable = FakeRunnable([Exception("invalid schema"), ok("unused")])
    with pytest.raises(LLMUnavailable):
        invoke_with_retry(runnable, "prompt")
    assert runnable.calls == 1


def test_usage_defaults_to_zero_when_raw_has_none():
    runnable = FakeRunnable([{"parsed": "v", "raw": object()}])
    _, usage = invoke_with_retry(runnable, "prompt")
    assert usage.tokens == 0


# ── model construction ───────────────────────────────────────────────────────

@pytest.fixture
def no_credentials(monkeypatch):
    # Construction is this section's subject, so it opts out of the suite-wide guard
    # in tests/conftest.py. Safe: with the key emptied the client is refused before
    # it can reach a provider, which is the behaviour under test.
    monkeypatch.setattr("app.core.llm.ChatOpenAI", ChatOpenAI)
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.mark.parametrize("build", [get_chat_model, get_codegen_model])
def test_construction_without_credentials_raises_domain_error(no_credentials, build):
    with pytest.raises(LLMUnavailable) as caught:
        build()
    assert "could not be built" in caught.value.detail


def test_construction_failure_detail_keeps_the_provider_reason(no_credentials):
    with pytest.raises(LLMUnavailable) as caught:
        get_chat_model()
    assert "credential" in caught.value.detail.lower()


def test_a_bad_argument_is_not_disguised_as_an_outage(no_credentials):
    with pytest.raises(ValidationError):
        get_chat_model(temperature="hot")
