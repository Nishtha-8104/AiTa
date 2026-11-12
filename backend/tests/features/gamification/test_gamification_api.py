import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.gamification.service import awards_for_event
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.service import EventInput
from app.features.practice.models import McqQuestion


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GAMIFICATION_MODE", "silent")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="gam@example.com", username="gam")
    db.add(user)
    db.add(McqQuestion(external_id="mcq-loops", topic="loops", difficulty="easy",
                       stem="?", options=[{"text": "a", "misconception": None},
                                          {"text": "b", "misconception": None}],
                       answer_index=1, verify_code="print('b')", reviewed=True))
    db.commit()

    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield TestClient(app), db, user
    app.dependency_overrides.clear()
    db.close()


def test_me_returns_summary_and_toasts_only_in_live(client, monkeypatch):
    http, db, user = client
    event = ingest(db, EventInput(user_id=user.id, kind="code", score=1.0,
                                  raw_topic="loops", item_id=1))

    body = http.get("/api/v1/gamification/me").json()
    assert body["mode"] == "silent"
    assert body["points"] == 10
    loops = next(t for t in body["topics"] if t["topic"] == "loops")
    assert loops["next_band"] == "mastered" and loops["gap_to_next"] > 0
    assert body["self_board"]["last_7"]["solved"] == 1

    assert awards_for_event(db, event.id) == []
    answer = http.post("/api/v1/assessment/mcq/1/answer", json={"chosen_index": 1}).json()
    assert answer["awards"] == []

    def broken(*args):
        raise RuntimeError("ledger unavailable")
    monkeypatch.setattr("app.features.practice.logic.assessment.grading.awards_for_event", broken)
    graded = http.post("/api/v1/assessment/mcq/1/answer", json={"chosen_index": 1})
    assert graded.status_code == 200 and graded.json()["awards"] == []
    monkeypatch.undo()

    monkeypatch.setattr("app.core.config.settings.GAMIFICATION_MODE", "live")
    toasts = awards_for_event(db, event.id)
    assert [(a.kind, a.points) for a in toasts] == [("points", 10), ("level_up", 0)]
