import pytest

from app.features.accounts.models import User
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.logic.mastery import PRIOR
from app.features.learner_model.models import TopicMastery
from app.features.learner_model.service import EventInput, mastery_snapshot


@pytest.fixture
def user(session):
    u = User(email="l@example.com", username="lang",
             preferred_language="c")
    session.add(u)
    session.commit()
    return u


def loops(snapshot):
    return next(t for t in snapshot["topics"] if t["topic"] == "loops")["mastery"]


def test_mastery_is_kept_per_language(session, user):
    ingest(session, EventInput(user_id=user.id, kind="code", score=1.0, raw_topic="loops"))
    c_value = session.get(TopicMastery, (user.id, "loops", "c")).mastery
    assert c_value > PRIOR
    assert session.get(TopicMastery, (user.id, "loops", "python")) is None

    user.preferred_language = "python"
    session.commit()
    assert loops(mastery_snapshot(session, user.id)) == pytest.approx(PRIOR)

    user.preferred_language = "c"
    session.commit()
    assert loops(mastery_snapshot(session, user.id)) == pytest.approx(c_value, abs=1e-3)


def test_event_language_follows_the_item(session, user):
    event = ingest(session, EventInput(user_id=user.id, kind="debug", score=1.0,
                                       raw_topic="loops", language="cpp"))
    assert event.language == "cpp"
    assert session.get(TopicMastery, (user.id, "loops", "cpp")) is not None
    assert session.get(TopicMastery, (user.id, "loops", "c")) is None
