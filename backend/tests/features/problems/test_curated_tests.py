import pytest

from app.features.grading.logic.execution.base import ExecResult, ExecStatus
from app.features.problems.logic.test_generation.curated_tests import curated_tests
from app.features.problems.models import (
    Problem, ProblemSource, ReferenceStatus, TestCase, TestCaseOrigin,
)
from tests.conftest import FakeExecutionProvider

REFERENCE = "print(sum(map(int, input().split())))"


@pytest.fixture
def problem(session):
    p = Problem(source=ProblemSource.DSA, statement="Add two numbers",
                statement_hash="c" * 64)
    session.add(p)
    session.commit()
    return p


def case(stdin, expected, kind="normal"):
    return {"kind": kind, "stdin": stdin, "expected_stdout": expected,
            "rationale": "why"}


def ok(stdout):
    return ExecResult(status=ExecStatus.OK, stdout=stdout, time_ms=1)


CASES = [case("1 2\n", "3"), case("4 5\n", "9"), case("0 0\n", "0", kind="edge")]
# One more than TEST_CASES_MIN, so a single drop still leaves a usable suite.
FOUR = CASES + [case("6 7\n", "13")]


def test_agreeing_cases_are_stored(session, problem):
    provider = FakeExecutionProvider([ok("3"), ok("9"), ok("0")])
    suite = curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    assert suite.unverified_reason is None
    assert (suite.agreed, suite.dropped, suite.case_count) == (3, 0, 3)
    stored = session.query(TestCase).filter(TestCase.problem_id == problem.id).all()
    assert len(stored) == 3
    assert [c.ordinal for c in stored] == [1, 2, 3]


def test_every_case_runs_as_a_batch_of_one(session, problem):
    provider = FakeExecutionProvider([ok("3"), ok("9"), ok("0")])
    curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    stdins = provider.calls[0]["stdins"]
    assert len(stdins) == 3
    assert all(s.startswith("1\n") for s in stdins)


def test_origin_marks_the_case_as_shipped(session, problem):
    provider = FakeExecutionProvider([ok("3"), ok("9"), ok("0")])
    curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    stored = session.query(TestCase).filter(TestCase.problem_id == problem.id).all()
    assert {c.origin for c in stored} == {TestCaseOrigin.PROBLEM_SAMPLE}


def test_authored_output_losing_to_the_reference_is_dropped(session, problem):
    # The authored expectation for case 2 is wrong; the executed reference wins.
    provider = FakeExecutionProvider([ok("3"), ok("99"), ok("0"), ok("13")])
    suite = curated_tests(session, problem, REFERENCE, FOUR, provider=provider)

    assert (suite.agreed, suite.dropped) == (3, 1)
    stored = session.query(TestCase).filter(TestCase.problem_id == problem.id).all()
    assert [c.stdin for c in stored] == ["1 2\n", "0 0\n", "6 7\n"]


def test_expected_output_comes_from_execution_not_the_file(session, problem):
    provider = FakeExecutionProvider([ok("3   \n\n\n"), ok("9"), ok("0")])
    curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    stored = session.query(TestCase).filter(TestCase.problem_id == problem.id).first()
    assert stored.expected_stdout == "3"


def test_a_crashing_case_is_dropped(session, problem):
    provider = FakeExecutionProvider([
        ok("3"), ExecResult(status=ExecStatus.RUNTIME_ERROR, stderr="boom"), ok("0"),
    ])
    suite = curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    assert (suite.agreed, suite.dropped) == (2, 1)


def test_duplicate_stdin_is_collapsed(session, problem):
    cases = CASES + [case("1 2\n", "3")]
    provider = FakeExecutionProvider([ok("3"), ok("9"), ok("0"), ok("3")])
    suite = curated_tests(session, problem, REFERENCE, cases, provider=provider)

    assert suite.agreed == 3


def test_too_few_agreeing_cases_is_unverified(session, problem):
    provider = FakeExecutionProvider([ok("3"), ok("99"), ok("99")])
    suite = curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    assert suite.unverified_reason == "insufficient_agreed_tests"
    assert session.query(TestCase).count() == 0


def test_a_reference_that_will_not_compile_is_unverified(session, problem):
    provider = FakeExecutionProvider([
        ExecResult(status=ExecStatus.COMPILE_ERROR, compile_output="syntax error"),
    ] * 3)
    suite = curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    assert suite.unverified_reason == "reference_unvalidated"
    assert suite.reference_solution is None
    assert session.query(TestCase).count() == 0


def test_the_validated_reference_is_recorded(session, problem):
    provider = FakeExecutionProvider([ok("3"), ok("9"), ok("0")])
    curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    session.refresh(problem)
    assert [r.status for r in problem.references] == [ReferenceStatus.VALIDATED]
    assert problem.references[0].source == REFERENCE


def test_no_llm_is_involved(session, problem, monkeypatch):
    from app.core import llm_gateway

    def explode(*args, **kwargs):
        raise AssertionError("curated ingest must not call the LLM")

    monkeypatch.setattr(llm_gateway, "invoke", explode)
    provider = FakeExecutionProvider([ok("3"), ok("9"), ok("0")])
    suite = curated_tests(session, problem, REFERENCE, CASES, provider=provider)

    assert suite.case_count == 3
