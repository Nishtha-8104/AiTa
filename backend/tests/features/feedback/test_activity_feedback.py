"""The Feedback page report built from learning events, for a student whose work is
MCQs and debug challenges rather than a code evaluation."""

import pytest
from fastapi import HTTPException

from app.features.accounts.models import User
from app.features.feedback.models import FeedbackReport, FeedbackType
from app.features.feedback.router import auto_generate
from app.features.feedback.schemas import GenerateFeedbackRequest
from app.features.feedback.service import FeedbackService
from app.features.learner_model.models import LearningEvent
from tests.features.feedback.test_feedback_graph import (
    FakeSynthesiseRunnable,
    make_evaluation,
    narrative,
)


@pytest.fixture
def user(session):
    u = User(email="mcq@example.com", username="mcq")
    session.add(u)
    session.commit()
    return u


def add_event(session, user, kind, topic="loops", score=1.0, **fields):
    session.add(LearningEvent(user_id=user.id, kind=kind, topic=topic, score=score,
                              weight=1.0, language="c", **fields))
    session.commit()


@pytest.fixture
def mcq_and_debug(session, user):
    add_event(session, user, "mcq", item_id=1)
    add_event(session, user, "mcq", item_id=2, score=0.0, misconceptions=["off_by_one"])
    add_event(session, user, "mcq", topic="arrays", item_id=3)
    add_event(session, user, "debug", item_id=4, score=0.0, hint_level_used=3,
              misconceptions=["off_by_one"])


def test_mcq_only_student_gets_report(session, user, mcq_and_debug):
    runnable = FakeSynthesiseRunnable()

    report = FeedbackService.generate(session, user.id, GenerateFeedbackRequest(),
                                      synthesise_runnable=runnable)

    assert report.feedback_type == FeedbackType.LEARNING_RECAP
    assert report.pattern_only is False
    assert report.evaluation_id is None
    human = runnable.payloads[0][1][1]
    assert '"kind": "debug"' in human and "off_by_one" in human


def test_no_activity_still_422(session, user):
    add_event(session, user, "diagnostic_seed")

    with pytest.raises(HTTPException) as exc:
        auto_generate(current_user=user, db=session)

    assert exc.value.status_code == 422


def test_another_users_evaluation_is_404_and_no_report(session, user, mcq_and_debug):
    other = User(email="other@example.com", username="other")
    session.add(other)
    session.commit()
    evaluation = make_evaluation(session, other)

    with pytest.raises(HTTPException) as exc:
        FeedbackService.generate(session, user.id,
                                 GenerateFeedbackRequest(evaluation_id=evaluation.id),
                                 synthesise_runnable=FakeSynthesiseRunnable())

    assert exc.value.status_code == 404
    assert session.query(FeedbackReport).count() == 0


def test_activity_report_guarded(session, user, mcq_and_debug):
    leaky = narrative()
    leaky.summary = "Compare with this:\n```c\nfor (i = 0; i < n; i++) total += a[i];\n```"
    runnable = FakeSynthesiseRunnable(result=leaky)

    report = FeedbackService.generate(session, user.id, GenerateFeedbackRequest(),
                                      synthesise_runnable=runnable)

    assert len(runnable.payloads) == 2
    assert report.pattern_only is True
    assert "```" not in report.summary
