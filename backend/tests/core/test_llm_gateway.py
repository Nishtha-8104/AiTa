import sys
import types

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import llm_gateway
from app.core.config import settings
from app.core.database import Base
from app.core.exceptions import LLMUnavailable, ModelKeyError
from app.core.llm_call import LLMCall
from app.core.llm_choice import Choice, use_choice
from app.core.llm_gateway import Gateway, TokenBucket, gateway_chat_model, invoke

RATE_LIMITED = Exception("Error code: 429 - rate limit exceeded")


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeChat:
    def __init__(self, outcome):
        self.outcome = outcome
        self.tools = None

    def bind_tools(self, tools, **kwargs):
        self.tools = tools
        return self

    def invoke(self, payload, **kwargs):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def reply(text="hi"):
    return AIMessage(content=text, usage_metadata={
        "input_tokens": 3, "output_tokens": 4, "total_tokens": 7})


class FakeFactory:
    def __init__(self, behaviour=None):
        self.behaviour = behaviour or (lambda model, key: reply())
        self.calls = []
        self.built = []

    def __call__(self, model, api_key, purpose, *, timeout):
        self.calls.append((model, api_key, purpose.name))
        chat = FakeChat(self.behaviour(model, api_key))
        self.built.append(chat)
        return chat


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "k0")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY_2", "k1")
    monkeypatch.setattr(settings, "NVIDIA_MODEL", "primary")
    monkeypatch.setattr(settings, "NVIDIA_FALLBACK_MODEL", "")
    monkeypatch.setattr(settings, "NVIDIA_RPM", 35)
    monkeypatch.setattr(settings, "LLM_QUEUE_DEADLINE_S", 20)
    monkeypatch.setattr(settings, "REDIS_URL", "")

    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    clock = FakeClock()
    factory = FakeFactory()
    gateway = Gateway(clock=clock, sleep=clock.sleep, session_factory=sessions,
                      model_factory=factory)
    monkeypatch.setattr(llm_gateway, "_gateway", gateway)

    class Env:
        pass

    e = Env()
    e.clock, e.factory, e.gateway, e.sessions = clock, factory, gateway, sessions

    def rows():
        with sessions() as db:
            return [(r.purpose, r.status, r.key_slot, r.model)
                    for r in db.query(LLMCall).order_by(LLMCall.id)]

    e.rows = rows
    return e


def test_bucket_gives_rpm_tokens_then_refuses_until_a_minute_passes():
    clock = FakeClock()
    bucket = TokenBucket(35, clock)

    assert all(bucket.try_take() for _ in range(35))
    assert not bucket.try_take()
    assert bucket.wait_time() > 0

    clock.now += 60
    assert sum(bucket.try_take() for _ in range(40)) == 35


def test_calls_alternate_keys_and_each_logs_one_ok_row(env):
    results = [invoke("hint", "p", user_id=None) for _ in range(4)]

    assert [r.key_slot for r in results] == [0, 1, 0, 1]
    assert [c[1] for c in env.factory.calls] == ["k0", "k1", "k0", "k1"]
    assert results[0].status == "ok" and results[0].tokens == 7
    assert env.rows() == [("hint", "ok", s, "primary") for s in (0, 1, 0, 1)]


def test_rate_limited_key_is_retried_on_the_other_key(env):
    env.factory.behaviour = lambda model, key: RATE_LIMITED if key == "k0" else reply()

    result = invoke("explain", "p")

    assert (result.status, result.key_slot) == ("ok", 1)
    assert env.rows() == [("explain", "ok", 1, "primary")]


def test_both_keys_rate_limited_falls_back_to_the_fallback_model(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_FALLBACK_MODEL", "backup")
    env.factory.behaviour = lambda model, key: reply() if model == "backup" else RATE_LIMITED

    result = invoke("feedback", "p")

    assert (result.status, result.model) == ("fallback", "backup")
    assert [r[:2] for r in env.rows()] == [("feedback", "fallback")]


def test_everything_failing_returns_the_template(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_FALLBACK_MODEL", "backup")
    env.factory.behaviour = lambda model, key: RATE_LIMITED

    result = invoke("chat", "p", template="busy")

    assert (result.value, result.status, result.key_slot) == ("busy", "template", None)
    assert len(env.factory.calls) == 3
    assert env.rows() == [("chat", "template", None, "")]


def test_empty_buckets_yield_the_template_within_the_deadline(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_RPM", 1)
    invoke("chat_summary", "p")
    invoke("chat_summary", "p")
    started = env.clock.now

    result = invoke("chat_summary", "p", template="busy")

    assert result.status == "template"
    assert env.clock.now - started <= settings.LLM_QUEUE_DEADLINE_S + 0.25
    assert result.queued_ms >= 19_000
    assert len(env.factory.calls) == 2


def test_no_template_and_all_failing_raises_and_logs_error(env):
    env.factory.behaviour = lambda model, key: RATE_LIMITED

    with pytest.raises(LLMUnavailable):
        invoke("feedback", "p")

    assert env.rows() == [("feedback", "error", None, "primary")]


def test_empty_second_key_only_uses_slot_zero(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY_2", "")

    slots = [invoke("hint", "p").key_slot for _ in range(3)]

    assert slots == [0, 0, 0]
    assert {c[1] for c in env.factory.calls} == {"k0"}


def test_logging_failure_never_reaches_the_caller(env):
    def broken():
        raise RuntimeError("db down")

    env.gateway.session_factory = broken

    assert invoke("hint", "p").status == "ok"


def test_real_client_is_built_without_sdk_retries_and_within_the_deadline(env, monkeypatch):
    built = []

    def fake_nvidia(model, temperature, **kwargs):
        built.append(kwargs)
        return FakeChat(reply())

    monkeypatch.setattr(llm_gateway, "_nvidia", fake_nvidia)
    env.gateway.model_factory = llm_gateway._default_factory

    invoke("test_gen", "p")

    assert built[0]["max_retries"] == 0
    assert 0 < built[0]["timeout"] <= llm_gateway.PURPOSES["test_gen"].deadline == 120


def test_hung_primary_leaves_time_for_the_fallback_model(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_FALLBACK_MODEL", "backup")
    timeouts = []

    def factory(model, api_key, purpose, *, timeout):
        timeouts.append((model, timeout))
        if model == "backup":
            return FakeChat(reply())
        env.clock.now += timeout
        return FakeChat(Exception("Request timed out."))

    result = invoke("chat", "p", model_factory=factory)

    assert (result.status, result.model) == ("fallback", "backup")
    assert timeouts[0] == ("primary", pytest.approx(45 * llm_gateway._PRIMARY_SHARE))
    assert timeouts[-1][1] >= 15


def test_purpose_deadline_overrides_the_default(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_RPM", 1)
    invoke("chat", "p")
    invoke("chat", "p")
    started = env.clock.now

    assert invoke("chat", "p", template="busy").status == "template"
    assert 44 <= env.clock.now - started <= 45.25


def test_broken_redis_degrades_to_in_process_buckets(env, monkeypatch):
    class DeadRedis:
        def incr(self, key):
            raise ConnectionError("redis down")

    fake_module = types.SimpleNamespace(
        Redis=types.SimpleNamespace(from_url=lambda url: DeadRedis()))
    monkeypatch.setitem(sys.modules, "redis", fake_module)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://nowhere")

    assert invoke("hint", "p").status == "ok"
    assert isinstance(env.gateway._buckets[0], TokenBucket)


def test_bound_chat_model_routes_tool_calls_through_the_gateway(env):
    tool = {"type": "function", "function": {
        "name": "search_book", "parameters": {"type": "object", "properties": {}}}}

    message = gateway_chat_model("chat", user_id=None).bind_tools([tool]).invoke("hello")

    assert message.content == "hi"
    assert env.factory.built[0].tools == [tool]
    assert env.gateway._buckets[0].tokens == 34
    assert env.rows() == [("chat", "ok", 0, "primary")]


STUDENT = Choice("openai", "gpt-4.1-mini", "https://api.openai.com/v1", "sk-student-secret-1234")


def _logged(env):
    with env.sessions() as db:
        return [(r.status, r.provider, r.key_source, r.model, r.key_slot, r.error or "")
                for r in db.query(LLMCall).order_by(LLMCall.id)]


def test_student_choice_uses_their_client_and_logs_provider_without_key(env):
    built = []
    env.gateway.choice_factory = lambda choice, **kw: built.append(choice) or FakeChat(reply())

    with use_choice(STUDENT):
        result = invoke("hint", "p")

    assert result.model == "gpt-4.1-mini"
    assert built == [STUDENT] and env.factory.calls == []
    assert _logged(env) == [("ok", "openai", "own", "gpt-4.1-mini", None, "")]


def test_student_key_failure_stops_without_fallback_or_template(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_FALLBACK_MODEL", "fallback")
    failure = Exception("Error code: 429 - Rate limit reached for sk-student-secret-1234")
    failure.status_code = 429
    env.gateway.choice_factory = lambda choice, **kw: FakeChat(failure)

    with use_choice(STUDENT), pytest.raises(ModelKeyError) as caught:
        invoke("hint", "p", template="canned hint")

    assert caught.value.code == "rate_limited"
    assert env.factory.calls == []
    [row] = _logged(env)
    assert row[:3] == ("error", "openai", "own")
    assert "sk-student-secret-1234" not in row[5]


def test_no_choice_keeps_the_pet_path_and_logs_it(env):
    invoke("hint", "p")

    assert _logged(env) == [("ok", "nvidia", "pet", "primary", 0, "")]


def test_no_server_model_and_no_choice_asks_for_a_model(env, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")

    with pytest.raises(ModelKeyError) as caught:
        invoke("hint", "p", template="canned hint")

    assert caught.value.code == "no_model"
    assert env.factory.calls == []
