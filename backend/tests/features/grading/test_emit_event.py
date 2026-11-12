"""Code Eval → Profiling Agent wiring. Stubbed executor and explanation."""

import pytest

from app.features.accounts.models import User
from app.features.grading.agent.graph import evaluate_submission
from app.features.grading.agent.schemas import Explanation
from app.features.grading.models import CodeSubmission, Language
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.problems.models import (
    Problem,
    ProblemSource,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)
from tests.conftest import FakeExecutionProvider
from tests.features.grading.test_graph import FakeExplainRunnable, merged


@pytest.fixture
def user(session):
    u = User(email="e@example.com", username="emitter")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def problem(session):
    p = Problem(source=ProblemSource.DSA, statement="max", statement_hash="e" * 64,
                topic="dynamic_programming")
    p.test_cases = [
        TestCase(kind=TestCaseKind.SAMPLE, stdin="1\n5\n", expected_stdout="5",
                 stdin_hash="a", origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=0),
        TestCase(kind=TestCaseKind.EDGE, stdin="1\n-7\n", expected_stdout="-7",
                 stdin_hash="b", origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1),
    ]
    session.add(p)
    session.commit()
    return p


def submit(session, user, problem_id=None, language=Language.PYTHON):
    s = CodeSubmission(user_id=user.id, language=language, code="print(0)",
                       problem_id=problem_id, title="t")
    session.add(s)
    session.commit()
    return s


def explain_with(tags):
    return FakeExplainRunnable(Explanation(
        summary="s", detailed_feedback="## f", misconceptions=tags,
    ))


def test_verified_submission_emits_one_event_and_moves_mastery(session, user, problem):
    submission = submit(session, user, problem.id)
    report = evaluate_submission(
        session, submission.id, user.id,
        provider=FakeExecutionProvider(merged("5\n0\n")),
        explain_runnable=explain_with(["wrong_initial_value", "not_a_tag"]),
    )

    assert (report.tests_passed, report.tests_total) == (1, 2)
    assert report.misconceptions == ["wrong_initial_value"]

    event = session.query(LearningEvent).one()
    assert event.kind == "code"
    assert event.topic == "dynamic_programming"
    assert event.score == pytest.approx(0.5)
    assert event.item_id == problem.id
    assert event.misconceptions == ["wrong_initial_value"]
    assert event.source_ref == f"evaluation:{report.evaluation_id}"
    assert event.language == "python"

    row = session.get(TopicMastery, (user.id, "dynamic_programming", "python"))
    assert row.mastery == pytest.approx(0.3 + 0.3 * (0.5 - 0.3))


def test_passing_submission_carries_no_misconceptions(session, user, problem):
    submission = submit(session, user, problem.id)
    report = evaluate_submission(
        session, submission.id, user.id,
        provider=FakeExecutionProvider(merged("5\n-7\n")),
        explain_runnable=explain_with(["off_by_one"]),
    )
    assert report.misconceptions == []
    assert session.query(LearningEvent).one().misconceptions == []


def test_review_mode_emits_nothing(session, user):
    submission = submit(session, user)
    evaluate_submission(
        session, submission.id, user.id,
        provider=FakeExecutionProvider(merged("1\n")),
        explain_runnable=explain_with([]),
    )
    assert session.query(LearningEvent).count() == 0


def test_profiling_failure_does_not_break_the_evaluation(session, user, problem, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("profiling down")

    monkeypatch.setattr("app.features.grading.agent.nodes.emit_event.ingest", boom)
    submission = submit(session, user, problem.id)
    report = evaluate_submission(
        session, submission.id, user.id,
        provider=FakeExecutionProvider(merged("5\n-7\n")),
        explain_runnable=explain_with([]),
    )
    assert report.evaluation_id is not None
    assert report.tests_passed == 2
