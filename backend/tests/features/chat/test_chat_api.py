"""The chat API over HTTP: the SSE contract, ownership, thumbs, and a client that hangs up
mid-stream. Scripted models only."""

import json
import threading
from types import SimpleNamespace

import anyio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user, get_current_user
from app.features.accounts.models import User
from app.features.chat.models import EMBED_DIM, ChatMessage, ChatThread
from app.features.chat.router import get_chat_runner
from app.features.chat.service import FAILED, run_turn
from tests.features.chat.agent.conftest import ScriptedModel, tool_call

CHAT = "/api/v1/chat"
VECTOR = [1.0] + [0.0] * (EMBED_DIM - 1)


@pytest.fixture
def api():
    # StaticPool: the request thread and the turn's worker must share one in-memory database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    me = User(email="me@example.com", username="me")
    other = User(email="other@example.com", username="other")
    db.add_all([me, other])
    db.commit()
    state = SimpleNamespace(db=db, me=me, other=other, script=[], turns=[],
                            embed=lambda text: VECTOR)

    def runner(*args, **kwargs):
        turn = run_turn(*args, model=ScriptedModel(script=state.script),
                        summary_model=ScriptedModel(),
                        tool_ctx_overrides={"embed": state.embed}, **kwargs)
        state.turns.append(turn)
        return turn

    from app.main import app

    app.dependency_overrides.update({
        get_db: lambda: db, get_current_user: lambda: me, get_current_active_user: lambda: me,
        get_chat_runner: lambda: runner,
    })
    state.app, state.client = app, TestClient(app)
    yield state
    app.dependency_overrides.clear()
    for turn in state.turns:
        turn.wait(30)
    db.close()


def frames(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((fields["event"], json.loads(fields["data"])))
    return events


async def hang_up_after_first_chunk(app, path: str, payload: dict) -> list[dict]:
    """Drives the ASGI app like a browser that closes the tab once the first event lands."""
    sent, first_chunk, asked = [], anyio.Event(), False

    async def receive():
        nonlocal asked
        if not asked:
            asked = True
            return {"type": "http.request", "body": json.dumps(payload).encode(),
                    "more_body": False}
        await first_chunk.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)
        if message.get("body"):
            first_chunk.set()

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": "POST", "scheme": "http", "path": path, "raw_path": path.encode(),
             "root_path": "", "query_string": b"",
             "headers": [(b"content-type", b"application/json")],
             "client": ("test", 1), "server": ("test", 80)}
    await app(scope, receive, send)
    return sent


def test_a_message_streams_tool_events_then_the_reply(api):
    thread = api.client.post(f"{CHAT}/threads", json={}).json()
    api.script = [tool_call("search_books", "c1", query="pointer arithmetic"),
                  "Adding 1 moves it one element on."]

    response = api.client.post(f"{CHAT}/threads/{thread['id']}/messages",
                               json={"content": "  How do pointers move?  "})
    assert api.turns[0].wait(30)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert (response.headers["cache-control"], response.headers["x-accel-buffering"]) == (
        "no-cache", "no")
    events = frames(response.text)
    assert [(name, sorted(data)) for name, data in events] == [
        ("tool_start", ["args", "name"]),
        ("tool_end", ["trace"]),
        ("token", ["text"]),
        ("final", ["citations", "content", "message_id", "moderation_flag", "tool_calls"]),
    ]
    assert events[0][1] == {"name": "search_books", "args": {"query": "pointer arithmetic"}}
    final = events[-1][1]
    detail = api.client.get(f"{CHAT}/threads/{thread['id']}").json()
    assert detail["thread"]["title"] == "How do pointers move?"
    assert [(m["role"], m["content"]) for m in detail["messages"]] == [
        ("user", "How do pointers move?"), ("assistant", "Adding 1 moves it one element on.")]
    assert detail["messages"][1]["id"] == final["message_id"]

    api.script = [RuntimeError("provider fell over")]
    failed = api.client.post(f"{CHAT}/threads/{thread['id']}/messages", json={"content": "and?"})
    assert frames(failed.text) == [("error", {"message": FAILED, "code": ""})]


def test_strangers_threads_and_bad_input_never_reach_the_agent(api):
    theirs = ChatThread(user_id=api.other.id, title="their secret")
    api.db.add(theirs)
    api.db.commit()
    their_reply = ChatMessage(thread_id=theirs.id, user_id=api.other.id, role="assistant",
                              content="their private answer")
    api.db.add(their_reply)
    api.db.commit()
    mine = api.client.post(f"{CHAT}/threads").json()

    responses = [
        api.client.get(f"{CHAT}/threads/{theirs.id}"),
        api.client.post(f"{CHAT}/threads/{theirs.id}/messages", json={"content": "hi"}),
        api.client.patch(f"{CHAT}/messages/{their_reply.id}/thumbs", json={"value": "down"}),
    ]
    assert [r.status_code for r in responses] == [404, 404, 404]
    assert not any("their" in r.text for r in responses)
    assert [t["id"] for t in api.client.get(f"{CHAT}/threads").json()] == [mine["id"]]
    assert mine["mode"] == "pet"

    too_long = api.client.post(f"{CHAT}/threads/{mine['id']}/messages",
                               json={"content": "x" * 8001})
    assert too_long.status_code == 422
    assert api.turns == []
    api.db.expire_all()
    assert [(m.id, m.thumbs) for m in api.db.query(ChatMessage).all()] == [(their_reply.id, None)]


def test_thumbs_are_stored_then_cleared_on_own_replies_only(api):
    thread = ChatThread(user_id=api.me.id)
    api.db.add(thread)
    api.db.commit()
    question = ChatMessage(thread_id=thread.id, user_id=api.me.id, role="user", content="q")
    reply = ChatMessage(thread_id=thread.id, user_id=api.me.id, role="assistant", content="a")
    api.db.add_all([question, reply])
    api.db.commit()
    url = f"{CHAT}/messages/{reply.id}/thumbs"

    assert api.client.patch(url, json={"value": "up"}).json() == {"ok": True}
    api.db.refresh(reply)
    assert reply.thumbs == "up"
    assert api.client.patch(url, json={"value": None}).json() == {"ok": True}
    api.db.refresh(reply)
    assert reply.thumbs is None
    assert api.client.patch(f"{CHAT}/messages/{question.id}/thumbs",
                            json={"value": "up"}).status_code == 404
    assert api.client.patch(url, json={}).status_code == 422


def test_closing_the_tab_mid_stream_still_saves_the_reply(api):
    released, calls = threading.Event(), []

    def held_embed(text):
        # The first call is the automatic search before the model; hold the agent's own.
        calls.append(text)
        if len(calls) > 1:
            released.wait(10)
        return VECTOR

    api.embed = held_embed
    api.script = [tool_call("search_books", "c1", query="pointers"), "Pointers hold addresses."]
    thread_id = api.client.post(f"{CHAT}/threads").json()["id"]

    sent = anyio.run(hang_up_after_first_chunk, api.app,
                     f"{CHAT}/threads/{thread_id}/messages", {"content": "What is a pointer?"})
    released.set()
    assert api.turns[0].wait(30)

    streamed = b"".join(m.get("body", b"") for m in sent)
    assert sent[0]["status"] == 200 and streamed.startswith(b"event: tool_start")
    assert b"event: final" not in streamed
    messages = api.client.get(f"{CHAT}/threads/{thread_id}").json()["messages"]
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "What is a pointer?"), ("assistant", "Pointers hold addresses.")]
