import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, delete, event, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.features.accounts.models import User
from app.features.chat.models import ChatMessage, ChatThread
from app.features.chat.schemas import SendMessageIn


@pytest.fixture
def fk_session():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        yield db


def test_thread_messages_round_trip_and_cascade_with_user(fk_session):
    db = fk_session
    user = User(email="a@x.io", username="a")
    db.add(user)
    db.flush()
    thread = ChatThread(user_id=user.id)
    db.add(thread)
    db.flush()
    calls = [{"name": "search_books", "args": {"q": "pointers"}, "result": "3 hits", "ms": 42}]
    db.add_all([
        ChatMessage(thread_id=thread.id, user_id=user.id, role="user", content="what is a pointer?"),
        ChatMessage(thread_id=thread.id, user_id=user.id, role="assistant", content="An address.",
                    tool_calls=calls, citations=[{"book": "K&R", "section": "5.1"}]),
    ])
    db.commit()
    db.expire_all()

    assert db.get(ChatThread, thread.id).mode == "pet"
    reply = db.scalars(select(ChatMessage).where(ChatMessage.role == "assistant")).one()
    assert reply.tool_calls == calls

    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    assert db.scalar(select(func.count()).select_from(ChatThread)) == 0
    assert db.scalar(select(func.count()).select_from(ChatMessage)) == 0


def test_send_message_rejects_too_long_and_blank():
    assert SendMessageIn(content="  hi  ").content == "hi"
    with pytest.raises(ValidationError):
        SendMessageIn(content="x" * 8001)
    with pytest.raises(ValidationError):
        SendMessageIn(content="   \n\t ")
