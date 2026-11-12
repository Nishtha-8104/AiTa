"""The gamify node inside the Profiling graph: ledger, mirrors, isolation, modes."""

from datetime import datetime, timezone

import pytest

from app.features.accounts.models import User
from app.features.gamification import service
from app.features.gamification.models import GamificationAward
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.learner_model.service import EventInput


@pytest.fixture
def user(session):
    u = User(email="g@example.com", username="gamer")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def mode(monkeypatch):
    def set_mode(value):
        monkeypatch.setattr("app.core.config.settings.GAMIFICATION_MODE", value)
    set_mode("silent")
    return set_mode


def solve(user, kind="code", item=1, score=1.0):
    return EventInput(user_id=user.id, kind=kind, score=score, raw_topic="loops", item_id=item)


def test_ingest_writes_awards_and_mirrors(session, user, mode):
    ingest(session, solve(user))
    points = session.query(GamificationAward).filter_by(kind="points").all()
    assert [a.points for a in points] == [10]
    session.refresh(user)
    assert user.points == 10


def test_same_event_applied_twice_creates_no_duplicates(session, user, mode):
    event = ingest(session, solve(user))
    before = session.query(GamificationAward).count()
    assert service.apply(session, event) == []
    assert session.query(GamificationAward).count() == before


def test_gamify_failure_keeps_event_and_mastery(session, user, mode, monkeypatch):
    def boom(db, event):
        db.add(GamificationAward(user_id=event.user_id, learning_event_id=event.id, kind="badge",
                                 code="half", dedupe_key="badge:half", points=0, message="m"))
        db.flush()
        raise RuntimeError("engine down")
    monkeypatch.setattr(service, "apply", boom)

    event = ingest(session, solve(user))
    assert event.id is not None
    assert session.query(LearningEvent).count() == 1
    assert session.get(TopicMastery, (user.id, "loops", event.language)) is not None
    assert session.query(GamificationAward).count() == 0


def test_rebuild_matches_live_ledger_and_resets_stale_mirrors(session, user, mode):
    for event_in in [solve(user, "mcq", 1, 0.0), solve(user, "mcq", 1),
                     solve(user, "code", 5, 0.5), solve(user, "code", 5),
                     solve(user, "debug", 1), solve(user, "debug", 2), solve(user, "debug", 3)]:
        ingest(session, event_in)

    def ledger():
        return {(a.dedupe_key, a.points, a.learning_event_id)
                for a in session.query(GamificationAward).filter_by(user_id=user.id)}
    live = ledger()
    assert "badge:fixed_it" in {key for key, _, _ in live}

    user.points, user.badges = 999, ["legacy"]
    session.commit()
    assert service.rebuild(session, user.id) == len(live)
    assert ledger() == live
    session.refresh(user)
    assert user.points == sum(p for _, p, _ in live)
    assert "legacy" not in user.badges


def test_awards_carry_their_event_time_live_and_after_rebuild(session, user, mode):
    event = ingest(session, solve(user))
    then = datetime(2026, 9, 1, tzinfo=timezone.utc)
    event.created_at = then
    session.commit()
    service.rebuild(session, user.id)
    stamps = {a.created_at.replace(tzinfo=timezone.utc)
              for a in session.query(GamificationAward).filter_by(user_id=user.id)}
    assert stamps == {then}


def test_summary_totals_come_from_the_ledger_not_legacy_mirrors(session, user, mode):
    user.points, user.level = 350, 7
    session.commit()
    body = service.summary(session, user.id)
    assert (body.points, body.level) == (0, 1)


def test_modes(session, user, mode):
    mode("off")
    ingest(session, solve(user, item=1))
    assert session.query(GamificationAward).count() == 0
    mode("silent")
    ingest(session, solve(user, item=2))
    assert session.query(GamificationAward).filter_by(kind="points").count() == 1
