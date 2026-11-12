import pytest

from app.features.accounts.models import LearningProfile, User
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.learner_model.service import EventInput, mastery_snapshot


@pytest.fixture
def user(session):
    u = User(email="p@example.com", username="prof")
    session.add(u)
    session.commit()
    return u


def code_event(user, score, topic="loops", **kw):
    return EventInput(user_id=user.id, kind="code", score=score, raw_topic=topic, **kw)


def test_two_events_move_mastery_exactly_as_the_formula_says(session, user):
    ingest(session, code_event(user, 4 / 6))
    ingest(session, code_event(user, 1.0))

    row = session.get(TopicMastery, (user.id, "loops", "c"))
    first = 0.3 + 0.3 * 1.0 * (4 / 6 - 0.3)
    second = first + 0.3 * 1.0 * (1.0 - first)
    assert row.mastery == pytest.approx(second)
    assert row.evidence_count == 2

    events = session.query(LearningEvent).order_by(LearningEvent.id).all()
    assert events[0].mastery_before == pytest.approx(0.3)
    assert events[0].mastery_after == pytest.approx(first)
    assert events[1].mastery_before == pytest.approx(first)


def test_raw_bank_tags_are_normalised(session, user):
    event = ingest(session, code_event(user, 1.0, topic="two pointers"))
    assert event.topic == "arrays"
    assert event.raw_topic == "two pointers"
    assert session.get(TopicMastery, (user.id, "arrays", "c")) is not None


def test_off_list_topic_is_logged_but_moves_nothing(session, user):
    event = ingest(session, code_event(user, 1.0, topic="graph traversal"))
    assert event.topic is None
    assert event.raw_topic == "graph traversal"
    assert event.mastery_after is None
    assert session.query(TopicMastery).count() == 0


def test_resolving_a_solved_item_is_logged_but_moves_nothing(session, user):
    first = ingest(session, code_event(user, 1.0, item_id=9))
    again = ingest(session, code_event(user, 1.0, item_id=9))
    assert again.mastery_before == pytest.approx(first.mastery_after)
    assert again.mastery_after == pytest.approx(first.mastery_after)
    assert session.get(TopicMastery, (user.id, "loops", "c")).evidence_count == 1

    broke = ingest(session, code_event(user, 0.0, item_id=9))
    assert broke.mastery_after == pytest.approx(first.mastery_after)

    other = ingest(session, code_event(user, 1.0, item_id=10))
    assert other.mastery_after > first.mastery_after


def test_retrying_an_mcq_after_its_key_was_revealed_moves_nothing(session, user):
    def answer(score):
        return ingest(session, EventInput(user_id=user.id, kind="mcq", score=score,
                                          raw_topic="loops", item_id=3))
    wrong = answer(0.0)
    retry = answer(1.0)
    assert retry.mastery_after == pytest.approx(wrong.mastery_after)


def test_mcq_weight_is_half_a_coding_attempt(session, user):
    ingest(session, EventInput(user_id=user.id, kind="mcq", score=0.0, raw_topic="loops"))
    row = session.get(TopicMastery, (user.id, "loops", "c"))
    assert row.mastery == pytest.approx(0.3 + 0.3 * 0.5 * (0.0 - 0.3))


def test_unknown_kind_is_rejected(session, user):
    with pytest.raises(ValueError):
        ingest(session, EventInput(user_id=user.id, kind="essay", score=1.0, raw_topic="loops"))


def test_profile_mirror_owns_scores_and_bands(session, user):
    session.add(LearningProfile(user_id=user.id, weak_areas=["Some LLM phrase"],
                                topic_scores={"junk": 0.9}, error_patterns=["kept"]))
    session.commit()

    ingest(session, code_event(user, 0.0, topic="loops"))
    for _ in range(5):
        ingest(session, code_event(user, 1.0, topic="arrays"))

    profile = session.query(LearningProfile).filter_by(user_id=user.id).one()
    assert set(profile.topic_scores) == {"loops", "arrays"}
    assert profile.weak_areas == ["loops"]
    assert profile.strong_areas == ["arrays"]
    assert profile.error_patterns == []
    assert profile.recommended_next == ["basics_io", "hashing_sets", "sorting"]
    assert profile.accuracy_rate == pytest.approx(5 / 6, abs=1e-3)


def test_mirror_derives_error_patterns_and_next_topics(session, user):
    ingest(session, code_event(user, 1.0, topic="basics_io"))
    ingest(session, code_event(user, 0.5, topic="basics_io", misconceptions=["off_by_one"]))
    ingest(session, code_event(user, 0.5, topic="basics_io",
                               misconceptions=["off_by_one", "integer_division"]))

    profile = session.query(LearningProfile).filter_by(user_id=user.id).one()
    assert profile.error_patterns == ["off_by_one", "integer_division"]
    assert profile.recommended_next == ["conditionals", "functions", "basics_io"]


def test_mirror_creates_a_profile_when_none_exists(session, user):
    ingest(session, code_event(user, 1.0))
    assert session.query(LearningProfile).filter_by(user_id=user.id).one().topic_scores


def test_snapshot_lists_all_twelve_topics_with_unseen_at_prior(session, user):
    ingest(session, code_event(user, 1.0, topic="loops"))
    snap = mastery_snapshot(session, user.id)

    assert len(snap["topics"]) == 12
    by_topic = {t["topic"]: t for t in snap["topics"]}
    assert by_topic["strings"]["mastery"] == 0.3
    assert by_topic["strings"]["evidence_count"] == 0
    assert by_topic["strings"]["band"] == "unseen"
    assert by_topic["loops"]["evidence_count"] == 1


def test_prerequisite_gating(session, user):
    snap = {t["topic"]: t for t in mastery_snapshot(session, user.id)["topics"]}
    assert snap["basics_io"]["unlocked"] is True
    assert snap["conditionals"]["unlocked"] is False

    for _ in range(2):
        ingest(session, code_event(user, 1.0, topic="basics_io"))
    snap = {t["topic"]: t for t in mastery_snapshot(session, user.id)["topics"]}
    assert snap["conditionals"]["unlocked"] is True
    assert snap["functions"]["unlocked"] is True
    assert snap["loops"]["unlocked"] is False


def test_misconceptions_and_hint_reliance(session, user):
    ingest(session, code_event(user, 0.5, misconceptions=["off_by_one", "bogus"], hint_level=2))
    ingest(session, code_event(user, 0.5, misconceptions=["off_by_one"]))
    snap = mastery_snapshot(session, user.id)

    assert snap["top_misconceptions"] == [{"tag": "off_by_one", "count": 2}]
    assert snap["hint_reliance"] == 1.0
    assert len(snap["recent_events"]) == 2
