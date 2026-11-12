import pytest

from app.core.exceptions import LanguageNotExecutable, ProblemNotFound
from app.features.grading.logic.execution.base import ExecStatus
from app.features.grading.models import Language
from app.features.problems.logic.sample_run import run_sample
from app.features.problems.models import (
    Problem,
    ProblemSource,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)
from tests.conftest import FakeExecutionProvider, failing, ok


def _problem(session) -> Problem:
    problem = Problem(source=ProblemSource.DSA, statement="max", statement_hash="m" * 64)
    problem.test_cases = [
        TestCase(kind=TestCaseKind.SAMPLE, stdin="3\n1 5 2\n", expected_stdout="5",
                 stdin_hash="a", origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=0),
        TestCase(kind=TestCaseKind.EDGE, stdin="1\n-15\n", expected_stdout="-15",
                 stdin_hash="b", origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1),
    ]
    session.add(problem)
    session.commit()
    return problem


def test_runs_only_the_shown_example(session):
    problem = _problem(session)
    provider = FakeExecutionProvider([ok("5\n")])

    result = run_sample(session, problem.id, Language.PYTHON, "code", provider=provider)

    assert provider.calls[0]["stdins"] == ["1\n3\n1 5 2\n"]
    assert "-15" not in result.model_dump_json()
    assert result.verdict == "Accepted"
    assert (result.passed, result.total) == (1, 1)
    assert result.cases[0].input == "1\n3\n1 5 2\n"


def test_wrong_output_is_reported_with_what_the_code_printed(session):
    problem = _problem(session)
    provider = FakeExecutionProvider([ok("0\n")])

    result = run_sample(session, problem.id, Language.PYTHON, "code", provider=provider)

    assert result.verdict == "Wrong answer on test 1"
    assert result.status == "wrong_answer"
    assert result.cases[0].expected == "5"
    assert result.cases[0].actual == "0"
    assert not result.cases[0].passed


def test_compile_error_surfaces_compiler_output(session):
    problem = _problem(session)
    provider = FakeExecutionProvider(
        [failing(ExecStatus.COMPILE_ERROR, compile_output="error: expected ';'")]
    )

    result = run_sample(session, problem.id, Language.CPP, "code", provider=provider)

    assert result.verdict == "Compilation error"
    assert result.compile_output == "error: expected ';'"
    assert result.passed == 0


def test_runtime_error_keeps_stderr(session):
    problem = _problem(session)
    provider = FakeExecutionProvider(
        [failing(ExecStatus.RUNTIME_ERROR, stderr="IndexError")]
    )

    result = run_sample(session, problem.id, Language.PYTHON, "code", provider=provider)

    assert result.verdict == "Runtime error"
    assert result.stderr == "IndexError"


def test_unknown_problem_raises_not_found(session):
    with pytest.raises(ProblemNotFound):
        run_sample(session, 4242, Language.PYTHON, "code",
                   provider=FakeExecutionProvider([]))


def test_non_executable_language_is_rejected_before_running(session):
    problem = _problem(session)
    provider = FakeExecutionProvider([])

    with pytest.raises(LanguageNotExecutable):
        run_sample(session, problem.id, Language.SQL, "select 1", provider=provider)
    assert provider.calls == []
