import pytest

from app.features.accounts.models import User
from app.features.gamification import service as gamification
from app.features.gamification.models import GamificationAward
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.learner_model.service import (
    EventInput,
    apply_theory_adjustment,
    derive_profile,
    record_diagnostic_seed,
)
from app.features.practice.logic.assessment import policy


@pytest.fixture
def user(session):
    u = User(email="seed@example.com", username="seed")
    session.add(u)
    session.commit()
    return u


def seed(session, user, seeds):
    return record_diagnostic_seed(session, user.id, seeds, "c")


def loops(session, user):
    return session.get(TopicMastery, (user.id, "loops", "c")).mastery


def test_seed_sets_mastery_and_evidence_one(session, user):
    seed(session, user, {"loops": 0.7, "arrays": 0.25})

    for topic, value in (("loops", 0.7), ("arrays", 0.25)):
        row = session.get(TopicMastery, (user.id, topic, "c"))
        assert row.mastery == pytest.approx(value)
        assert row.evidence_count == 1
    events = session.query(LearningEvent).filter_by(kind="diagnostic_seed").all()
    assert len(events) == 2
    assert all(e.mastery_before == pytest.approx(0.3) for e in events)
    assert {e.topic: e.mastery_after for e in events} == pytest.approx(
        {"loops": 0.7, "arrays": 0.25})


def test_seed_awards_nothing(session, user):
    seed(session, user, {"loops": 0.7, "arrays": 0.25})

    board = gamification.summary(session, user.id)
    assert board.points == 0
    assert board.badges == []
    assert board.self_board.last_7.level_ups == 0
    assert gamification.rebuild(session, user.id) == 0


def test_seed_does_not_trigger_stuck_rule(session, user):
    seed(session, user, {"loops": 0.25})
    ingest(session, EventInput(user.id, "code", 0.0, raw_topic="loops", item_id=1))
    ingest(session, EventInput(user.id, "code", 0.0, raw_topic="loops", item_id=2))
    assert policy.stuck_topic(session, user.id) is None


def test_seed_band_is_not_a_level_up_but_mastery_still_is(session, user):
    seed(session, user, {"loops": 0.7})

    def level_ups():
        return [a.code for a in session.query(GamificationAward).filter_by(kind="level_up")]

    ingest(session, EventInput(user.id, "code", 0.6, raw_topic="loops", item_id=1))
    assert level_ups() == []

    for item in (2, 3, 4):
        ingest(session, EventInput(user.id, "code", 1.0, raw_topic="loops", item_id=item))
    assert level_ups() == ["loops:mastered"]


def test_seed_excluded_from_accuracy(session, user):
    seed(session, user, {"loops": 0.7, "arrays": 0.5})
    assert derive_profile(session, user.id).accuracy_rate == 0.0


def test_theory_adjustment_only_without_practice(session, user):
    seed(session, user, {"loops": 0.5})

    event = apply_theory_adjustment(session, user.id, "loops", 0.7, "c")
    assert event.kind == "diagnostic_theory"
    assert loops(session, user) == pytest.approx(0.7)
    assert session.query(LearningEvent).filter_by(kind="diagnostic_theory").count() == 1

    ingest(session, EventInput(user.id, "code", 1.0, raw_topic="loops", item_id=1))
    after_practice = loops(session, user)

    assert apply_theory_adjustment(session, user.id, "loops", 0.2, "c") is None
    assert loops(session, user) == pytest.approx(after_practice)
    assert session.query(LearningEvent).filter_by(kind="diagnostic_theory").count() == 1


def test_seed_twice_is_noop(session, user):
    assert len(seed(session, user, {"loops": 0.7})) == 1
    assert seed(session, user, {"loops": 0.25}) == []
    assert session.query(LearningEvent).filter_by(kind="diagnostic_seed").count() == 1
    assert loops(session, user) == pytest.approx(0.7)
