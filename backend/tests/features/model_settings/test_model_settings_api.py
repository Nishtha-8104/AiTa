import types

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import ModelKeyError
from app.core.llm_choice import COOKIE, Choice, current_choice, use_choice
from app.features.accounts.models import User
from app.features.chat.service import Error, Turn
from app.features.model_settings import service

KEY = "sk-proj-student-secret-9876"
URL = "/api/v1/model-settings"


class FakeChat:
    """'no-tools' never calls a tool; every other model passes both probes."""

    def __init__(self, model):
        self.model = model

    def invoke(self, prompt):
        return AIMessage(content="OK")

    def bind_tools(self, tools, **kwargs):
        calls = [] if self.model == "no-tools" else [{"name": "add", "args": {"a": 2, "b": 3}, "id": "1"}]
        return types.SimpleNamespace(invoke=lambda prompt: AIMessage(content="", tool_calls=calls))

    def with_structured_output(self, schema, **kwargs):
        return types.SimpleNamespace(invoke=lambda prompt: {"parsed": schema(answer=5), "raw": None})


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="m@example.com", username="m")
    db.add(user)
    db.commit()

    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "server-key")
    checked = []
    monkeypatch.setattr(service, "list_models", lambda choice: checked.append(choice) or {
        "gpt-4.1-mini": 1_047_576, "gpt-4.1": None, "tiny": 4096})
    monkeypatch.setattr(service, "build_client", lambda choice, **kw: FakeChat(choice.model))

    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    c = TestClient(app)
    c.checked = checked
    yield c
    app.dependency_overrides.clear()
    db.close()


def test_saved_choice_is_seen_by_requests_and_never_returned(client):
    saved = client.put(URL, json={"provider": "openai", "model": "gpt-4.1-mini", "api_key": KEY})

    assert saved.status_code == 200
    assert KEY not in saved.text and KEY not in saved.headers["set-cookie"]
    assert "HttpOnly" in saved.headers["set-cookie"]
    seen = client.get(URL).json()
    assert (seen["source"], seen["provider"], seen["model"], seen["key_hint"]) == \
        ("own", "openai", "gpt-4.1-mini", "9876")

    client.delete(URL)
    assert client.get(URL).json()["source"] == "default"


def test_without_a_server_model_the_student_must_choose(client, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")
    monkeypatch.setattr(settings, "DEFAULT_LLM_PROVIDER", "")

    seen = client.get(URL).json()
    assert (seen["source"], seen["model"], seen["has_default"]) == ("none", "", False)


def test_changing_model_reuses_the_saved_key_for_the_same_provider(client):
    client.put(URL, json={"provider": "openai", "model": "gpt-4.1-mini", "api_key": KEY})

    assert client.put(URL, json={"provider": "openai", "model": "gpt-4.1"}).status_code == 200
    assert client.checked[-1].api_key == KEY
    assert client.put(URL, json={"provider": "groq", "model": "llama"}).status_code == 422


def test_local_models_are_always_offered(client):
    assert "ollama" in [p["id"] for p in client.get(URL).json()["providers"]]

    saved = client.put(URL, json={"provider": "custom", "model": "gpt-4.1-mini",
                                  "base_url": "http://10.0.0.5:8000/v1"})
    assert saved.status_code == 200
    assert client.checked[-1].base_url == "http://10.0.0.5:8000/v1"
    assert client.get(URL).json()["source"] == "local"


def test_key_failure_returns_424_with_code(client, monkeypatch):
    def rejected(choice):
        raise ModelKeyError("invalid_key", "Your OpenAI key was rejected. Change your key or "
                                           "model in the Model window.")
    monkeypatch.setattr(service, "list_models", rejected)

    response = client.post(f"{URL}/test", json={"provider": "openai", "api_key": KEY})

    assert response.status_code == 424
    assert response.json()["code"] == "invalid_key"
    assert COOKIE not in response.headers.get("set-cookie", "")


def test_test_reports_each_capability(client):
    body = client.post(f"{URL}/test", json={"provider": "openai", "api_key": KEY,
                                            "model": "gpt-4.1-mini"}).json()

    assert body["ok"] is True
    assert [(c["name"], c["ok"]) for c in body["checks"]] == [
        ("Connection", True), ("Tool calling", True), ("Structured output", True),
        ("Context window", True)]
    assert body["context"] == 1_047_576


@pytest.mark.parametrize("model, failing", [("no-tools", "Tool calling"),
                                            ("tiny", "Context window")])
def test_saving_a_model_that_fails_a_check_is_refused_with_the_reason(client, model, failing):
    response = client.put(URL, json={"provider": "openai", "api_key": KEY, "model": model})

    assert response.status_code == 422
    assert failing in response.json()["detail"]
    assert COOKIE not in response.headers.get("set-cookie", "")


def test_garbage_cookie_counts_as_default_and_is_cleared(client):
    client.cookies.set(COOKIE, "not-a-real-token", path="/api")

    response = client.get(URL)

    assert response.json()["source"] == "default"
    assert f"{COOKIE}=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_chat_worker_thread_runs_with_the_request_choice():
    choice = Choice("openai", "gpt-4.1-mini", "https://api.openai.com/v1", KEY)
    job = types.SimpleNamespace(thread_id=1,
                                run=lambda emit: emit(Error(repr(current_choice()))))

    with use_choice(choice):
        turn = Turn(job)
    event = next(turn)

    assert "gpt-4.1-mini" in event.message
