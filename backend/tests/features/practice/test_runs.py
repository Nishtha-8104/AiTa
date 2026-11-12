import random
from datetime import datetime, timezone

import pytest

from app.features.accounts.models import User
from app.features.learner_model.models import LearningEvent
from app.features.practice import service as lifecycle
from app.features.practice.logic.assessment.grading import grade_mcq
from app.features.practice.logic.topic_practice import runs
from app.features.practice.models import McqAttempt, McqQuestion, PracticeSession

# The graders stamp the real time, so the run must not look idle against it.
NOW = datetime.now(timezone.utc)


@pytest.fixture
def user(session):
    u = User(email="t@example.com", username="topical")
    session.add(u)
    session.commit()
    return u


def add_mcq(session, n, topic="loops"):
    q = McqQuestion(external_id=f"mcq-c-{topic}-{n}", topic=topic, difficulty="easy",
                    language="c", stem=f"q{n}", options=[{"text": "a"}, {"text": "b"}],
                    answer_index=0, verify_code="", reviewed=True)
    session.add(q)
    session.commit()
    return q


def run_with_plan(session, user, plan):
    s = runs.start(session, user.id, "loops", NOW)
    s.plan = plan
    session.commit()
    return s


def test_plan_is_three_of_each_and_one_coding_never_first():
    for seed in range(30):
        plan = runs.make_plan(random.Random(seed))
        assert len(plan) == 10 and plan[0] != "coding"
        assert sorted(plan) == sorted(["coding"] + ["theory", "mcq", "debug"] * 3)


def test_run_serves_unseen_first_holds_until_graded_then_ends_when_dry(session, user):
    seen, fresh = add_mcq(session, 1), add_mcq(session, 2)
    session.add(McqAttempt(user_id=user.id, question_id=seen.id, chosen_index=1, correct=False))
    session.commit()
    run_with_plan(session, user, ["mcq", "mcq", "mcq"])

    step = runs.next_step(session, user.id, NOW)
    assert (step.item["id"], step.position, step.total) == (fresh.id, 1, 3)
    assert runs.next_step(session, user.id, NOW).item["id"] == fresh.id
    assert "answer_index" not in step.item

    grade_mcq(session, user.id, fresh.id, 0)
    step = runs.next_step(session, user.id, NOW)
    assert (step.item["id"], step.position) == (seen.id, 2)

    grade_mcq(session, user.id, seen.id, 0)
    step = runs.next_step(session, user.id, NOW)
    assert step.done and step.total == 2
    assert session.query(LearningEvent).filter_by(session_id=step.session_id).count() == 2


def test_a_type_with_nothing_left_falls_back_to_another(session, user):
    q = add_mcq(session, 1)
    run_with_plan(session, user, ["theory"])
    step = runs.next_step(session, user.id, NOW)
    assert (step.item_type, step.item["id"]) == ("mcq", q.id)


def test_a_run_and_adaptive_practice_close_each_other(session, user):
    q = add_mcq(session, 1, topic="arrays")
    lifecycle.record_served(session, user.id, "mcq", q.id, "c", NOW)
    grade_mcq(session, user.id, q.id, 0)
    adaptive = session.query(PracticeSession).one()

    run = runs.start(session, user.id, "loops", NOW)
    assert adaptive.end_reason == "mode_switch" and run.topic == "loops"
    assert runs.start(session, user.id, "loops", NOW).id == run.id

    add_mcq(session, 2)
    runs.next_step(session, user.id, NOW)
    lifecycle.record_served(session, user.id, "mcq", q.id, "c", NOW)
    assert lifecycle.open_run(session, user.id, NOW) is None
