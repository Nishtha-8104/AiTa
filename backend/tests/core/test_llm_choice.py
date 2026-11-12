import httpx
import pytest
from openai import APIConnectionError

from app.core.llm_choice import COOKIE_KWARGS, Choice, decode, encode
from app.core.llm_providers import classify

KEY = "sk-proj-abcdefghijklmnop1234"
CHOICE = Choice("openai", "gpt-4.1-mini", "https://api.openai.com/v1", KEY)


class StatusError(Exception):
    def __init__(self, status, text=""):
        super().__init__(f"Error code: {status} - {text}")
        self.status_code = status


def test_cookie_round_trip_keeps_the_key_unreadable():
    token = encode(CHOICE)

    assert decode(token) == CHOICE
    assert KEY not in token
    assert decode(token[:-4] + "AAAA") is None
    assert decode("not-a-token") is None
    assert KEY not in repr(CHOICE)


@pytest.mark.parametrize("exc, code", [
    (StatusError(401, "invalid api key"), "invalid_key"),
    (StatusError(403), "invalid_key"),
    (StatusError(402, "payment required"), "out_of_credit"),
    (StatusError(429, "You exceeded your current quota"), "out_of_credit"),
    (StatusError(429, "Rate limit reached"), "rate_limited"),
    (StatusError(400, "This model's maximum context length is 8192 tokens"), "too_many_tokens"),
    (StatusError(404, "The model `x` does not exist"), "model_not_found"),
    (APIConnectionError(request=httpx.Request("GET", "https://api.openai.com")),
     "provider_unreachable"),
    (StatusError(400, "bad request"), "provider_error"),
])
def test_classify_maps_provider_errors(exc, code):
    error = classify(exc, CHOICE)

    assert error.code == code
    assert error.status_code == 424
    assert error.detail.endswith("Change your key or model in the Model window.")


def test_classify_never_echoes_the_key():
    error = classify(StatusError(401, f"Incorrect API key provided: {KEY}. Also sk-other1234567"), CHOICE)

    assert KEY not in error.provider_message
    assert "sk-other1234567" not in error.provider_message
    assert KEY not in error.detail


def test_cookie_is_http_only_and_kept_for_a_year():
    assert COOKIE_KWARGS["max_age"] == 365 * 86400
    assert COOKIE_KWARGS["httponly"] and COOKIE_KWARGS["samesite"] == "strict"
    assert COOKIE_KWARGS["path"] == "/api" and "secure" not in COOKIE_KWARGS
