"""Whole-pipeline tests. No Docker, no network — a FakeExecutionProvider supplies
execution results and a fake runnable supplies the explanation."""

import pytest

from app.core.exceptions import LLMUnavailable, SubmissionNotFound
from app.features.accounts.models import User
from app.features.grading.agent.graph import evaluate_submission
from app.features.grading.agent.schemas import Explanation, GeneratedCase, GeneratedTests
from app.features.grading.logic.execution.base import ExecResult, ExecStatus
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.problems.models import ExecutionResult, Problem
from tests.conftest import FakeExecutionProvider

SUM_STATEMENT = ("Read an integer n on the first line, then n integers on the second "
                 "line. Print their sum.")


@pytest.fixture
def user(session):
    u = User(email="s@example.com", username="student")
    session.add(u)
    session.commit()
    return u


def make_submission(session, user, *, code="print(1)", language=Language.PYTHON,
                    problem_context=SUM_STATEMENT):
    submission = CodeSubmission(user_id=user.id, language=language, code=code,
                                problem_context=problem_context, title="t")
    session.add(submission)
    session.commit()
    return submission


def generated_tests():
    return GeneratedTests(
        reference_solution="print(sum(map(int, input().split())))",
        cases=[GeneratedCase(kind="normal", stdin=f"{i}\n", expected_stdout=str(i),
                             rationale=f"checks {i}") for i in (1, 2, 3)],
    )


class FakeExplainRunnable:
    def __init__(self, explanation=None, error=None):
        self.explanation = explanation or Explanation(
            summary="Close.", detailed_feedback="## Feedback",
            time_complexity="O(n)", space_complexity="O(1)",
            learning_points=["boundaries"],
        )
        self.error = error
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return {"parsed": self.explanation, "raw": None}


def ok(stdout):
    return ExecResult(status=ExecStatus.OK, stdout=stdout, time_ms=3)


def gen_then_student(gen_results, student_results):
    """Two phases with different shapes.

    Generation validates each sub-case separately, so it asks for len(cases) runs.
    The student's program runs ONCE over every sub-case merged into one stdin, so the
    second phase returns exactly one result whose stdout is the whole output stream.
    """
    class Provider(FakeExecutionProvider):
        def __init__(self):
            super().__init__([])
            self.round = 0
            self.student_stdin = None

        def run_batch(self, language, source, stdins, limits):
            self.round += 1
            if self.round == 1:
                return gen_results[: len(stdins)]
            self.student_stdin = stdins[0]
            return student_results[: len(stdins)]

    return Provider()


def merged(output: str):
    """One student run producing the whole output stream."""
    return [ok(output)]


def test_all_tests_pass_gives_full_correctness(session, user):
    submission = make_submission(session, user)
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n2\n3\n"))
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(),
    )

    assert report.verification_status == "verified"
    assert (report.tests_passed, report.tests_total) == (3, 3)
    assert report.scores.correctness == 100.0
    assert report.first_failing_case is None
    assert report.verdict == "Accepted"


def test_student_runs_once_over_a_merged_stdin(session, user):
    submission = make_submission(session, user)
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n2\n3\n"))
    evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(),
    )
    # Test count first, then every sub-case block concatenated behind it.
    assert provider.student_stdin == "3\n1\n2\n3\n"


def test_one_failing_sub_case_scores_partial(session, user):
    submission = make_submission(session, user)
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n999\n3\n"))
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(),
    )

    assert (report.tests_passed, report.tests_total) == (2, 3)
    assert report.scores.correctness == round(200 / 3, 1)
    assert report.verdict == "Wrong answer on test 2"
    assert report.first_failing_case.ordinal == 2
    assert report.first_failing_case.actual_stdout == "999"
    assert report.first_failing_case.rationale == "checks 2"


def test_output_ending_early_fails_only_the_tail(session, user):
    submission = make_submission(session, user)
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n2\n"))
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(),
    )

    assert (report.tests_passed, report.tests_total) == (2, 3)
    assert report.missing_output is True
    assert report.verdict == "Wrong answer on test 3"


def test_a_crash_credits_no_sub_case(session, user):
    from app.features.grading.logic.execution.base import ExecResult, ExecStatus

    submission = make_submission(session, user)
    crashed = [ExecResult(status=ExecStatus.RUNTIME_ERROR, stderr="IndexError")]
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], crashed)
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(),
    )

    # The batch stopped partway, so later sub-cases never ran and cannot be credited.
    assert (report.tests_passed, report.tests_total) == (0, 3)
    assert report.verdict == "Runtime error"
    assert report.scores.correctness == 0.0


def test_no_problem_statement_is_review_mode(session, user):
    submission = make_submission(session, user, problem_context=None)
    provider = FakeExecutionProvider([ok("1\n")])
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        explain_runnable=FakeExplainRunnable(),
    )

    assert report.mode == "review"
    assert report.verification_status == "unverified"
    assert report.unverified_reason == "no_problem_statement"
    assert report.scores.correctness is None
    # The smoke run is not a test — it must not inflate either counter.
    assert (report.tests_passed, report.tests_total) == (0, 0)


def test_non_executable_language_is_review_mode(session, user):
    submission = make_submission(session, user, language=Language.JAVA,
                                 code="class A{}")
    report = evaluate_submission(
        session, submission.id, user.id,
        provider=FakeExecutionProvider([ok("")]),
        explain_runnable=FakeExplainRunnable(),
    )

    assert report.mode == "review"
    assert report.unverified_reason == "language_not_executable"
    assert report.scores.correctness is None


def test_compile_failure_short_circuits_before_the_llm(session, user):
    submission = make_submission(session, user, code="def broken(:")
    runnable = FakeExplainRunnable()
    provider = gen_then_student(
        [ok("1\n"), ok("2\n"), ok("3\n")],
        [ExecResult(status=ExecStatus.COMPILE_ERROR, compile_output="SyntaxError")],
    )
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(), explain_runnable=runnable,
    )

    assert report.compiled is False
    assert report.compile_output == "SyntaxError"
    assert runnable.prompts == []
    assert report.summary is None


def test_insufficient_agreed_tests_falls_back_to_review(session, user):
    submission = make_submission(session, user)
    disagreeing = GeneratedTests(
        reference_solution="print(1)",
        cases=[GeneratedCase(kind="normal", stdin=f"{i}\n", expected_stdout="WRONG",
                             rationale="r") for i in (1, 2, 3)],
    )
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n"))
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: disagreeing, explain_runnable=FakeExplainRunnable(),
    )

    assert report.unverified_reason == "insufficient_agreed_tests"
    assert report.scores.correctness is None


def test_llm_unavailable_during_generation_falls_back_to_review(session, user):
    submission = make_submission(session, user)

    def exploding_generator(**kwargs):
        raise LLMUnavailable("provider down")

    report = evaluate_submission(
        session, submission.id, user.id,
        provider=FakeExecutionProvider([ok("1\n")]),
        generator=exploding_generator, explain_runnable=FakeExplainRunnable(),
    )

    assert report.unverified_reason == "test_generation_failed"
    assert report.scores.correctness is None


def test_llm_unavailable_during_explanation_still_returns_scores(session, user):
    submission = make_submission(session, user)
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n2\n3\n"))
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(error=LLMUnavailable("provider down")),
    )

    assert report.scores.correctness == 100.0
    assert report.summary is None
    assert report.verification_status == "verified"


def test_missing_submission_raises_domain_error(session, user):
    with pytest.raises(SubmissionNotFound):
        evaluate_submission(session, 9999, user.id,
                            provider=FakeExecutionProvider([]))


def test_evaluation_and_execution_results_are_persisted(session, user):
    submission = make_submission(session, user)
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n999\n3\n"))
    report = evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(),
    )

    evaluation = session.query(CodeEvaluation).one()
    assert evaluation.id == report.evaluation_id
    assert evaluation.tests_passed == 2
    assert evaluation.verification_status == "verified"
    assert evaluation.attempt_number == 1
    assert session.query(ExecutionResult).count() == 3


def test_second_attempt_increments_attempt_number(session, user):
    submission = make_submission(session, user)

    def run():
        provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")],
                                    merged("1\n2\n3\n"))
        return evaluate_submission(
            session, submission.id, user.id, provider=provider,
            generator=lambda **k: generated_tests(),
            explain_runnable=FakeExplainRunnable(),
        )

    run()
    run()
    attempts = [e.attempt_number for e in session.query(CodeEvaluation).all()]
    assert sorted(attempts) == [1, 2]


def test_test_cases_are_reused_on_the_second_attempt(session, user):
    submission = make_submission(session, user)
    provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n2\n3\n"))
    evaluate_submission(
        session, submission.id, user.id, provider=provider,
        generator=lambda **k: generated_tests(),
        explain_runnable=FakeExplainRunnable(),
    )

    def explode(**kwargs):
        raise AssertionError("cache hit must not call the generator")

    report = evaluate_submission(
        session, submission.id, user.id,
        provider=FakeExecutionProvider([ok("1\n"), ok("2\n"), ok("3\n")]),
        generator=explode, explain_runnable=FakeExplainRunnable(),
    )
    assert report.tests_total == 3
    assert session.query(Problem).count() == 1
