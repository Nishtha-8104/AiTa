import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.learner_model.service import record_diagnostic_seed
from app.features.practice.models import McqQuestion


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="api-a@example.com", username="apia",
                preferred_language="python")
    db.add(user)
    db.add(McqQuestion(external_id="q-basics", topic="basics_io", difficulty="easy",
                       stem="What does print(7 // 2) print?",
                       options=[{"text": "3.5", "misconception": "integer_division"},
                                {"text": "3", "misconception": None}],
                       answer_index=1, verify_code="print(7 // 2)",
                       explanations=["// is floor division"], reviewed=True))
    db.commit()

    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield TestClient(app), db
    app.dependency_overrides.clear()
    db.close()


def test_next_then_answer_round_trip(client):
    http, _ = client
    nxt = http.get("/api/v1/assessment/next")
    assert nxt.status_code == 200
    body = nxt.json()
    assert body["item_type"] == "mcq"
    assert "answer_index" not in body["item"] and "verify_code" not in nxt.text

    answer = http.post(f"/api/v1/assessment/mcq/{body['item']['id']}/answer",
                       json={"chosen_index": 0})
    assert answer.status_code == 200
    result = answer.json()
    assert result["correct"] is False
    assert result["misconception"] == "integer_division"
    assert result["answer_index"] == 1

    mastery = http.get("/api/v1/profile/mastery").json()
    basics = next(t for t in mastery["topics"] if t["topic"] == "basics_io")
    assert basics["evidence_count"] == 1


def test_first_item_follows_seeds(client):
    http, db = client
    user = db.query(User).one()
    loops_q = McqQuestion(external_id="q-loops", topic="loops", difficulty="easy",
                          stem="What does print(len(range(1, 5))) print?",
                          options=[{"text": "5", "misconception": "off_by_one"},
                                   {"text": "4", "misconception": None}],
                          answer_index=1, verify_code="print(len(range(1, 5)))",
                          explanations=["range stops before its end"], reviewed=True)
    db.add(McqQuestion(external_id="diag-old", topic="loops", difficulty="easy", stem="old",
                       options=[{"text": "a", "misconception": None}], answer_index=0,
                       verify_code="print(1)", explanations=["x"], is_diagnostic=True,
                       reviewed=True))
    db.add(loops_q)
    db.commit()
    record_diagnostic_seed(db, user.id, {"basics_io": 0.7, "conditionals": 0.7, "loops": 0.25},
                           "python")

    body = http.get("/api/v1/assessment/next").json()

    assert (body["item_type"], body["topic"], body["item"]["id"]) == ("mcq", "loops", loops_q.id)
    assert "Loops" in body["reason"]


def test_unknown_question_is_404_and_bad_index_422(client):
    http, _ = client
    assert http.post("/api/v1/assessment/mcq/999/answer",
                     json={"chosen_index": 0}).status_code == 404
    assert http.post("/api/v1/assessment/mcq/1/answer",
                     json={"chosen_index": 9}).status_code == 422


def test_nothing_to_serve_is_503(client, monkeypatch):
    from app.core.exceptions import LLMUnavailable
    from app.features.practice.logic.assessment import policy

    def refuse(*a, **k):
        raise LLMUnavailable("generation is stubbed in tests")

    monkeypatch.setattr(policy, "generate_problem", refuse)
    http, db = client
    db.query(McqQuestion).delete()
    db.commit()

    assert http.get("/api/v1/assessment/next").status_code == 503
