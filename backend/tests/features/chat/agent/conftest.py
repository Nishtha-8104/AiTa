from types import SimpleNamespace

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.features.accounts.models import User
from app.features.chat.models import EMBED_DIM, ChatThread


class ScriptedModel(BaseChatModel):
    """Replays scripted replies (a callable is called first, e.g. to hold the turn) and
    records every call. Like a real API, it cannot call tools it was not given, so it
    skips scripted tool calls when unbound; tool_choice it ignores, like a stubborn one."""

    script: list = Field(default_factory=list)
    calls: list = Field(default_factory=list)
    tools: list = Field(default_factory=list)
    tool_choice: str | None = None

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self.model_copy(update={"tools": [t.name for t in tools],
                                       "tool_choice": kwargs.get("tool_choice")})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(SimpleNamespace(messages=list(messages), tools=list(self.tools),
                                          tool_choice=self.tool_choice))
        while True:
            reply = self.script.pop(0)
            if callable(reply):
                reply = reply()
            if isinstance(reply, Exception):
                raise reply
            if isinstance(reply, str):
                reply = AIMessage(content=reply)
            if reply.tool_calls and not self.tools:
                continue
            return ChatResult(generations=[ChatGeneration(message=reply)])


def tool_call(name: str, call_id: str, **args) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id,
                                              "type": "tool_call"}])


def new_thread(db, user, mode="pet") -> ChatThread:
    thread = ChatThread(user_id=user.id, mode=mode)
    db.add(thread)
    db.commit()
    return thread


@pytest.fixture(autouse=True)
def fake_query_embedding(monkeypatch):
    """Every pet turn searches the books first; without passages that finds nothing."""
    monkeypatch.setattr("app.features.chat.logic.rag.embedder.embed_query",
                        lambda text: [1.0] + [0.0] * (EMBED_DIM - 1))


@pytest.fixture
def db():
    # StaticPool: the turn's worker thread must see the same in-memory database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False)() as session:
        yield session


@pytest.fixture
def student(db):
    user = User(email="s@example.com", username="student")
    db.add(user)
    db.commit()
    return user
