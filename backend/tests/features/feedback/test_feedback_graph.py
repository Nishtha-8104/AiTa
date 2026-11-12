"""Whole-pipeline tests for the Feedback Agent. Offline — a fake runnable stands in
for the LLM, so the graph runs with no network and no live database."""

import pytest

from app.features.accounts.models import LearningProfile, User
from app.features.feedback.agent.graph import generate_feedback
from app.features.feedback.agent.nodes.persist import HEADLINE_LIMIT
from app.features.feedback.agent.schemas import FeedbackNarrative
from app.features.feedback.models import FeedbackReport, FeedbackTone, FeedbackType
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.learner_model.models import LearningEvent


@pytest.fixture
def user(session):
    u = User(email="s@example.com", username="student")
    session.add(u)
    session.commit()
    session.add(LearningProfile(user_id=u.id, weak_areas=["loops"],
                                error_patterns=[], topic_scores={}))
    session.commit()
    return u


def make_evaluation(session, user, **overrides):
    submission = CodeSubmission(user_id=user.id, language=Language.PYTHON,
                                code="print(1)", title="t")
    session.add(submission)
    session.commit()
    fields = dict(
        submission_id=submission.id, user_id=user.id, overall_score=55.0,
        correctness_score=50.0, complexity_score=40.0, efficiency_score=70.0,
        style_score=80.0, verification_status="verified", tests_passed=1,
        tests_total=2, status="done",
        issues=[{"severity": "error", "category": "logic", "message": "off by one"}],
        best_practices_used=["clear names"], learning_points=["boundaries"],
        anti_patterns=[], summary="Nearly there.",
    )
    fields.update(overrides)
    evaluation = CodeEvaluation(**fields)
    session.add(evaluation)
    session.commit()
    return evaluation


def make_activity(session, user):
    """Recursion practice: one MCQ solved with mastery rising, one debug challenge
    failed after a level-3 hint, both tagged with the same misconception."""
    session.add_all([
        LearningEvent(user_id=user.id, kind="mcq", topic="recursion", score=1.0,
                      weight=1.0, language="c", mastery_before=0.3, mastery_after=0.4,
                      misconceptions=["missing_base_case"]),
        LearningEvent(user_id=user.id, kind="debug", topic="recursion", score=0.0,
                      weight=1.0, language="c", hint_level_used=3,
                      mastery_before=0.4, mastery_after=0.35,
                      misconceptions=["missing_base_case"]),
    ])
    session.commit()


def narrative():
    return FeedbackNarrative(
        headline="Solid attempt with one boundary bug",
        summary="You got the shape of the solution right.",
        strengths=["clear names"],
        errors=["off by one at the last index"],
        misconceptions=["ranges are inclusive"],
        action_items=["Trace the loop on a 1-element input"],
        concept_map={"loops": 0.5, "indexing": 0.4},
        next_topics=["indexing", "loop invariants"],
        motivational="You are one small fix away.",
    )


class ProviderError(Exception):
    """Stands in for whatever the provider SDK raises.

    A real caller never raises a pre-wrapped `LLMUnavailable` — `invoke_with_retry`
    is what wraps it. The message deliberately contains no rate-limit marker from
    `app.core.llm._RATE_LIMIT_MARKERS`, so the retry budget is not spent sleeping.
    """


class FakeSynthesiseRunnable:
    """Mirrors what `structured(..., include_raw=True)` hands back."""

    _UNSET = object()

    def __init__(self, result=_UNSET, error=None, tokens=321):
        self.result = narrative() if result is self._UNSET else result
        self.error = error
        self.tokens = tokens
        self.payloads = []

    def invoke(self, payload):
        self.payloads.append(payload)
        if self.error:
            raise self.error
        return {"parsed": self.result, "raw": _Raw(self.tokens)}


class _Raw:
    def __init__(self, tokens):
        self.usage_metadata = {"total_tokens": tokens}


def unavailable():
    """The failure path, entered the way production enters it: the provider raises
    and `invoke_with_retry` turns that into `LLMUnavailable`."""
    return FakeSynthesiseRunnable(error=ProviderError("upstream call failed"))


def test_happy_path_persists_the_narrative(session, user):
    evaluation = make_evaluation(session, user)
    runnable = FakeSynthesiseRunnable()

    report = generate_feedback(
        session, user.id, evaluation.id, FeedbackTone.ENCOURAGING,
        synthesise_runnable=runnable,
    )

    assert report.pattern_only is False
    assert report.headline == "Solid attempt with one boundary bug"
    assert report.summary == "You got the shape of the solution right."
    assert report.strengths == ["clear names"]
    assert report.errors == ["off by one at the last index"]
    assert report.misconceptions == ["ranges are inclusive"]
    assert report.action_items == ["Trace the loop on a 1-element input"]
    assert report.concept_map == {"loops": 0.5, "indexing": 0.4}
    assert report.next_topics == ["indexing", "loop invariants"]
    assert report.motivational == "You are one small fix away."
    assert report.tokens_used == 321
    assert report.agent_steps
    assert len(runnable.payloads) == 1


def test_llm_unavailable_is_labelled_not_hidden(session, user):
    evaluation = make_evaluation(session, user)

    report = generate_feedback(
        session, user.id, evaluation.id, FeedbackTone.ENCOURAGING,
        synthesise_runnable=unavailable(),
    )

    assert report.pattern_only is True
    assert report.tokens_used == 0
    assert report.misconceptions == []
    # The headline must tell the student this is not the detailed analysis.
    assert "could not be generated" in report.headline
    assert "fallback" not in report.headline.lower()
    # The pattern findings still reach the student.
    assert report.errors == ["[logic] off by one"]
    assert report.strengths == ["clear names"]
    assert "correctness" in report.next_topics
    assert report.concept_map == {"correctness": 0.3, "complexity": 0.3}
    assert report.action_items
    # The provider's own error text must not reach a step the student reads.
    assert not any("upstream call failed" in s for s in report.agent_steps)


def test_an_unparseable_narrative_is_labelled_like_an_outage(session, user):
    """`invoke_with_retry` returns parsed=None rather than raising when structured
    output fails to parse. That must be labelled, not persisted as empty prose."""
    evaluation = make_evaluation(session, user)

    report = generate_feedback(
        session, user.id, evaluation.id, FeedbackTone.ENCOURAGING,
        synthesise_runnable=FakeSynthesiseRunnable(result=None),
    )

    assert report.pattern_only is True
    assert report.misconceptions == []
    assert "could not be generated" in report.headline
    assert "fallback" not in report.headline.lower()
    assert report.errors == ["[logic] off by one"]
    assert report.strengths == ["clear names"]
    assert report.concept_map == {"correctness": 0.3, "complexity": 0.3}
    assert report.action_items


@pytest.mark.parametrize("runnable", [FakeSynthesiseRunnable, unavailable])
def test_feedback_never_writes_the_profile(session, user, runnable):
    evaluation = make_evaluation(session, user)
    report = generate_feedback(session, user.id, evaluation.id,
                               FeedbackTone.CONSTRUCTIVE, synthesise_runnable=runnable())

    profile = session.query(LearningProfile).filter(
        LearningProfile.user_id == user.id).one()
    assert profile.weak_areas == ["loops"]
    assert profile.error_patterns == []
    assert profile.topic_scores == {}
    assert profile.last_updated_by_agent is None
    assert report.profile_updates == {}
    assert report.concept_map


def _bound_evaluation(session, user):
    """A failing attempt at a bank problem, the way Code Eval leaves it on disk."""
    from app.features.problems.models import (
        ExecRole,
        ExecutionResult,
        Problem,
        ProblemReference,
        ProblemSource,
        ReferenceStatus,
        TestCase,
        TestCaseKind,
        TestCaseOrigin,
    )

    problem = Problem(source=ProblemSource.DSA, statement="max", statement_hash="f" * 64,
                      topic="dynamic_programming")
    problem.test_cases = [
        TestCase(kind=TestCaseKind.SAMPLE, stdin="1\n5\n", expected_stdout="5",
                 stdin_hash="a", origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=0),
        TestCase(kind=TestCaseKind.EDGE, stdin="1\n-7\n", expected_stdout="-7",
                 stdin_hash="b", origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1,
                 rationale="all negative"),
    ]
    problem.references = [ProblemReference(
        language=Language.PYTHON, status=ReferenceStatus.VALIDATED,
        source="values = read()\nbest = cur = values[0]\nprint(best)")]
    session.add(problem)
    session.commit()

    submission = CodeSubmission(user_id=user.id, language=Language.PYTHON, title="t",
                                code="best = 0\nprint(best)", problem_id=problem.id)
    session.add(submission)
    session.commit()
    evaluation = make_evaluation(session, user, submission_id=submission.id)
    for case, status, out in zip(problem.test_cases, ("ok", "wrong_answer"), ("5", "0")):
        session.add(ExecutionResult(evaluation_id=evaluation.id, test_case_id=case.id,
                                    role=ExecRole.STUDENT, status=status, stdout=out))
    for n, tags in enumerate((["wrong_initial_value"], ["wrong_initial_value"],
                              ["wrong_initial_value", "off_by_one"])):
        session.add(LearningEvent(
            user_id=user.id, kind="code", topic="dynamic_programming", score=0.5,
            weight=1.0, misconceptions=tags, language="python",
            source_ref=f"evaluation:{evaluation.id}" if n == 2 else f"evaluation:{900 + n}"))
    session.commit()
    return evaluation


def test_context_cites_the_failing_input_and_repeated_misconceptions(session, user):
    evaluation = _bound_evaluation(session, user)
    runnable = FakeSynthesiseRunnable()

    generate_feedback(session, user.id, evaluation.id, FeedbackTone.CONSTRUCTIVE,
                      synthesise_runnable=runnable)

    system, human = (text for _, text in runnable.payloads[0])
    assert "quote its input" in system and "NEVER state the fix" in system
    assert "input '1\\n-7\\n', expected '-7', got '0'" in human
    assert '"wrong_initial_value": 3' in human
    assert "Misconceptions tagged on this attempt: wrong_initial_value, off_by_one" in human
    assert "Topic: Dynamic Programming" in human
    assert "Per-test results: ok, wrong_answer" in human


def test_feedback_quoting_the_reference_is_regenerated_then_withheld(session, user):
    evaluation = _bound_evaluation(session, user)
    leaky = narrative()
    leaky.summary = "Just write best = cur = values[0] and you are done."
    runnable = FakeSynthesiseRunnable(result=leaky)

    report = generate_feedback(session, user.id, evaluation.id,
                               FeedbackTone.CONSTRUCTIVE, synthesise_runnable=runnable)

    assert len(runnable.payloads) == 2
    assert report.pattern_only is True
    assert "values[0]" not in report.summary
    assert any("withheld" in step for step in report.agent_steps)


def test_clean_feedback_passes_the_guardrail(session, user):
    evaluation = _bound_evaluation(session, user)
    runnable = FakeSynthesiseRunnable()

    report = generate_feedback(session, user.id, evaluation.id,
                               FeedbackTone.CONSTRUCTIVE, synthesise_runnable=runnable)

    assert len(runnable.payloads) == 1
    assert report.pattern_only is False


def test_feedback_type_is_code_review_from_an_evaluation(session, user):
    evaluation = make_evaluation(session, user)
    report = generate_feedback(session, user.id, evaluation.id,
                               FeedbackTone.ENCOURAGING,
                               synthesise_runnable=FakeSynthesiseRunnable())
    assert report.feedback_type == FeedbackType.CODE_REVIEW


def test_feedback_type_is_learning_recap_from_activity(session, user):
    make_activity(session, user)
    report = generate_feedback(session, user.id, None,
                               FeedbackTone.ENCOURAGING,
                               synthesise_runnable=FakeSynthesiseRunnable())
    assert report.feedback_type == FeedbackType.LEARNING_RECAP
    assert report.evaluation_id is None


def test_feedback_type_is_combined_from_both(session, user):
    evaluation = make_evaluation(session, user)
    make_activity(session, user)
    report = generate_feedback(session, user.id, evaluation.id,
                               FeedbackTone.CHALLENGING,
                               synthesise_runnable=FakeSynthesiseRunnable())
    assert report.feedback_type == FeedbackType.COMBINED
    assert report.tone == FeedbackTone.CHALLENGING


def test_activity_signals_reach_the_pattern_analysis(session, user):
    make_activity(session, user)
    report = generate_feedback(
        session, user.id, None, FeedbackTone.ENCOURAGING,
        synthesise_runnable=unavailable(),
    )

    assert report.errors == ["Repeated mistake: missing base case (2x)",
                             "Needed step-by-step hints (level 3 or 4) 1x"]
    assert report.strengths == ["Solved 1 of 2 on Recursion",
                                "Mastery of Recursion went up"]
    assert report.next_topics == ["Recursion"]


def test_an_overlong_headline_is_clamped_not_raised(session, user):
    """`headline` is the only bounded column in the row, and the profile write has
    already committed by the time it is inserted. SQLite does not enforce VARCHAR
    length, so this asserts the clamp rather than the DataError it prevents."""
    evaluation = make_evaluation(session, user)
    verbose = narrative()
    verbose.headline = "y" * 500

    report = generate_feedback(
        session, user.id, evaluation.id, FeedbackTone.ENCOURAGING,
        synthesise_runnable=FakeSynthesiseRunnable(result=verbose),
    )

    limit = FeedbackReport.__table__.columns["headline"].type.length
    assert limit == HEADLINE_LIMIT, "the clamp must match the column it protects"
    assert len(report.headline) == HEADLINE_LIMIT
    assert report.headline.endswith("…")


def test_a_headline_at_the_limit_is_untouched(session, user):
    evaluation = make_evaluation(session, user)
    exact = narrative()
    exact.headline = "y" * HEADLINE_LIMIT

    report = generate_feedback(
        session, user.id, evaluation.id, FeedbackTone.ENCOURAGING,
        synthesise_runnable=FakeSynthesiseRunnable(result=exact),
    )

    assert report.headline == "y" * HEADLINE_LIMIT


def test_no_evaluation_and_no_activity_raises_value_error(session, user):
    with pytest.raises(ValueError):
        generate_feedback(session, user.id, None, FeedbackTone.ENCOURAGING,
                          synthesise_runnable=FakeSynthesiseRunnable())


def test_unknown_evaluation_without_activity_raises_value_error(session, user):
    with pytest.raises(ValueError):
        generate_feedback(session, user.id, 9999, FeedbackTone.ENCOURAGING,
                          synthesise_runnable=FakeSynthesiseRunnable())
