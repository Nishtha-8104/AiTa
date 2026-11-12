from app.features.problems.models import (
    Problem, ProblemSource, TestCase, TestCaseKind, TestCaseOrigin,
)
from app.features.problems.service import (
    find_problem_by_statement, get_or_create_problem, has_test_cases,
)


def test_creates_on_first_call(session):
    problem, created = get_or_create_problem(session, "Sum two numbers",
                                             source=ProblemSource.STUDENT)
    assert created is True
    assert problem.id is not None
    assert len(problem.statement_hash) == 64


def test_second_call_reuses_the_row(session):
    first, _ = get_or_create_problem(session, "Sum two numbers", source=ProblemSource.STUDENT)
    second, created = get_or_create_problem(session, "Sum two numbers",
                                            source=ProblemSource.STUDENT)
    assert created is False
    assert second.id == first.id
    assert session.query(Problem).count() == 1


def test_whitespace_and_case_variants_share_a_row(session):
    first, _ = get_or_create_problem(session, "Sum   two\nnumbers",
                                     source=ProblemSource.STUDENT)
    second, created = get_or_create_problem(session, "sum two numbers",
                                            source=ProblemSource.STUDENT)
    assert created is False
    assert second.id == first.id


def test_different_statements_do_not_collide(session):
    a, _ = get_or_create_problem(session, "Sum two numbers", source=ProblemSource.STUDENT)
    b, _ = get_or_create_problem(session, "Sum three numbers", source=ProblemSource.STUDENT)
    assert a.id != b.id


def test_original_statement_text_is_preserved(session):
    problem, _ = get_or_create_problem(session, "Sum   TWO\nnumbers",
                                       source=ProblemSource.STUDENT)
    assert problem.statement == "Sum   TWO\nnumbers"


def test_metadata_stored_on_create(session):
    problem, _ = get_or_create_problem(
        session, "Binary search", source=ProblemSource.DSA,
        topic="searching", difficulty="easy", created_by_user_id=None,
    )
    assert problem.topic == "searching"


def test_find_returns_none_when_absent(session):
    assert find_problem_by_statement(session, "nothing here") is None


def test_has_test_cases_false_then_true(session):
    problem, _ = get_or_create_problem(session, "s", source=ProblemSource.DSA)
    assert has_test_cases(session, problem.id) is False

    session.add(TestCase(problem_id=problem.id, kind=TestCaseKind.NORMAL,
                         stdin="1", expected_stdout="1", stdin_hash="f" * 64,
                         origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1))
    session.commit()
    assert has_test_cases(session, problem.id) is True
