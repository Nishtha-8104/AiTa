from app.features.problems.logic.listing import get_bank_problem, list_bank_problems
from app.features.problems.models import (
    IOMode,
    Problem,
    ProblemSource,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)


def _problem(source: ProblemSource, statement_hash: str) -> Problem:
    return Problem(
        source=source, statement="s", statement_hash=statement_hash,
        io_mode=IOMode.STDIN_STDOUT,
    )


def _test_case(problem_id: int, stdin_hash: str) -> TestCase:
    return TestCase(
        problem_id=problem_id, kind=TestCaseKind.NORMAL,
        stdin="1", expected_stdout="1", stdin_hash=stdin_hash,
        origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1,
    )


def test_student_problem_with_test_cases_is_absent(session):
    problem = _problem(ProblemSource.STUDENT, "a" * 64)
    session.add(problem)
    session.commit()
    session.add(_test_case(problem.id, "1" * 64))
    session.commit()

    assert list_bank_problems(session) == []


def test_generated_problem_with_test_cases_is_absent(session):
    problem = _problem(ProblemSource.GENERATED, "b" * 64)
    session.add(problem)
    session.commit()
    session.add(_test_case(problem.id, "2" * 64))
    session.commit()

    assert list_bank_problems(session) == []


def test_dsa_problem_with_test_cases_is_present(session):
    problem = _problem(ProblemSource.DSA, "c" * 64)
    session.add(problem)
    session.commit()
    session.add(_test_case(problem.id, "3" * 64))
    session.commit()

    summaries = list_bank_problems(session)
    assert [s.id for s in summaries] == [problem.id]


def test_curated_problem_with_no_test_cases_is_absent(session):
    problem = _problem(ProblemSource.MBPP, "d" * 64)
    session.add(problem)
    session.commit()

    assert list_bank_problems(session) == []


def test_get_bank_problem_returns_none_for_non_curated(session):
    problem = _problem(ProblemSource.STUDENT, "e" * 64)
    session.add(problem)
    session.commit()
    session.add(_test_case(problem.id, "4" * 64))
    session.commit()

    assert get_bank_problem(session, problem.id) is None
