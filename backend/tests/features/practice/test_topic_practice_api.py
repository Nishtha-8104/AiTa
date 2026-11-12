import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import content
from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.practice.logic.topic_practice import runs
from app.features.practice.models import McqQuestion


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.GAMIFICATION_MODE", "silent")
    monkeypatch.setattr("app.core.config.settings.CONTENT_DIR", tmp_path)
    content.write("loops", "explanation", [{"id": "explanation-c-loops", "language": "c",
                                           "title": "Loops", "markdown": ["", "A loop repeats."]}])
    monkeypatch.setattr(runs, "generate_coding", lambda *a: (None, None))
    runs._read.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="tp@example.com", username="tp",
                preferred_language="c")
    db.add(user)
    db.add(McqQuestion(external_id="mcq-c-loops-1", topic="loops", difficulty="easy",
                       language="c", stem="q", options=[{"text": "a"}, {"text": "b"}],
                       answer_index=1, verify_code="", reviewed=True))
    db.commit()

    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()
    runs._read.cache_clear()
    db.close()


def test_explanation_then_a_run_to_its_wrap_up(client):
    assert client.get("/api/v1/topic-practice/loops/explanation").json()["markdown"].startswith("# Loops")
    assert client.get("/api/v1/topic-practice/arrays/explanation").status_code == 404
    assert client.get("/api/v1/topic-practice/next").status_code == 404

    run = client.post("/api/v1/topic-practice/loops/start").json()
    assert run["total"] == 10
    step = client.get("/api/v1/topic-practice/next").json()
    assert step["item_type"] == "mcq" and step["position"] == 1
    assert "answer_index" not in step["item"]

    client.post(f"/api/v1/assessment/mcq/{step['item']['id']}/answer", json={"chosen_index": 1})
    done = client.get("/api/v1/topic-practice/next").json()
    assert done["done"] and done["total"] == 1

    wrap = client.post(f"/api/v1/practice-sessions/{done['session_id']}/finish").json()
    assert wrap["topic"] == "loops" and wrap["by_type"]["mcq"] == {"tried": 1, "solved": 1}
