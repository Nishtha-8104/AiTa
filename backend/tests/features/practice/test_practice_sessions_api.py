from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User
from app.features.learner_model.models import LearningEvent
from app.features.practice.models import PracticeSession


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GAMIFICATION_MODE", "silent")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="ps@example.com", username="ps")
    db.add(user)
    db.commit()

    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield TestClient(app), db, user
    app.dependency_overrides.clear()
    db.close()


def real_session(db, user_id, last_activity, ended_at=None, end_reason=None):
    s = PracticeSession(user_id=user_id, language="c", started_at=last_activity,
                        last_activity_at=last_activity, ended_at=ended_at,
                        end_reason=end_reason, graded_count=1,
                        served=[{"type": "mcq", "id": 1, "solved": True}])
    db.add(s)
    db.flush()
    db.add(LearningEvent(user_id=user_id, kind="mcq", item_id=1, topic="loops", score=1.0,
                         weight=1.0, language="c", misconceptions=[], mastery_before=0.2,
                         mastery_after=0.4, session_id=s.id, created_at=last_activity))
    db.commit()
    return s.id


def test_finish_then_read(client):
    http, db, user = client
    sid = real_session(db, user.id, datetime.now(timezone.utc))

    assert http.get("/api/v1/practice-sessions/current").json() == {"id": sid,
                                                                    "graded_count": 1}
    finished = http.post(f"/api/v1/practice-sessions/{sid}/finish")
    assert finished.status_code == 200
    body = finished.json()
    assert body["end_reason"] == "finished"
    assert body["by_type"]["mcq"] == {"tried": 1, "solved": 1}
    assert body["topics"][0]["topic"] == "loops"
    assert body["awards"] is None and body["feedback"] is None

    read = http.get(f"/api/v1/practice-sessions/{sid}")
    assert read.status_code == 200 and read.json()["id"] == sid
    assert http.get("/api/v1/practice-sessions/current").json()["id"] is None


def test_pending_cleared_after_read(client):
    http, db, user = client
    sid = real_session(db, user.id, datetime.now(timezone.utc) - timedelta(hours=2))

    pending = http.get("/api/v1/practice-sessions/pending").json()
    assert pending["id"] == sid and pending["solved"] == 1 and pending["topics"] == ["loops"]
    assert pending["end_reason"] == "idle"

    read = http.get(f"/api/v1/practice-sessions/{sid}")
    assert read.status_code == 200 and read.json()["end_reason"] == "idle"
    assert http.get("/api/v1/practice-sessions/pending").json() is None


def test_reopening_failed_feedback_does_not_regenerate(client):
    http, db, user = client
    now = datetime.now(timezone.utc)
    sid = real_session(db, user.id, now, ended_at=now, end_reason="finished")
    db.get(PracticeSession, sid).feedback_status = "unavailable"
    db.commit()

    reopened = http.post(f"/api/v1/practice-sessions/{sid}/feedback")
    assert reopened.status_code == 200
    assert reopened.json()["feedback_status"] == "unavailable"


def test_other_users_session_404(client):
    http, db, _ = client
    other = User(email="other@example.com", username="other")
    db.add(other)
    db.commit()
    now = datetime.now(timezone.utc)
    open_id = real_session(db, other.id, now)
    closed_id = real_session(db, other.id, now, ended_at=now, end_reason="idle")

    assert http.post(f"/api/v1/practice-sessions/{open_id}/finish").status_code == 404
    assert http.get(f"/api/v1/practice-sessions/{closed_id}").status_code == 404
    assert http.post(f"/api/v1/practice-sessions/{closed_id}/feedback",
                     json={"retry": False}).status_code == 404
