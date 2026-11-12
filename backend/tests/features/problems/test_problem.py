import pytest
from sqlalchemy.exc import IntegrityError

from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.problems.models import (
    Difficulty,
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


def test_problem_round_trips(session):
    problem = Problem(
        source=ProblemSource.STUDENT, statement="Sum two numbers",
        statement_hash="a" * 64, difficulty=Difficulty.EASY, topic="arrays",
    )
    session.add(problem)
    session.commit()
    assert problem.id is not None


def test_statement_hash_is_unique(session):
    session.add(Problem(source=ProblemSource.MBPP, statement="x", statement_hash="b" * 64))
    session.commit()
    session.add(Problem(source=ProblemSource.DSA, statement="y", statement_hash="b" * 64))
    with pytest.raises(IntegrityError):
        session.commit()


def test_test_cases_cascade_from_problem(session):
    problem = Problem(source=ProblemSource.DSA, statement="s", statement_hash="c" * 64)
    problem.test_cases.append(TestCase(
        kind=TestCaseKind.EDGE, stdin="0\n", expected_stdout="0",
        stdin_hash="d" * 64, origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1,
    ))
    session.add(problem)
    session.commit()
    assert len(problem.test_cases) == 1

    session.delete(problem)
    session.commit()
    assert session.query(TestCase).count() == 0


def test_reference_records_attempts(session):
    problem = Problem(source=ProblemSource.DSA, statement="s", statement_hash="e" * 64)
    problem.references.append(ProblemReference(
        language=Language.PYTHON, source="print(1)",
        status=ReferenceStatus.VALIDATED, attempts=2,
    ))
    session.add(problem)
    session.commit()
    assert problem.references[0].attempts == 2


def test_submission_problem_id_is_optional(session):
    session.add(CodeSubmission(user_id=1, language=Language.PYTHON, code="print(1)"))
    session.commit()
    assert session.query(CodeSubmission).one().problem_id is None


def test_evaluation_allows_null_correctness(session):
    session.add(CodeEvaluation(user_id=1, correctness_score=None,
                               tests_total=0, tests_passed=0))
    session.commit()
    assert session.query(CodeEvaluation).one().correctness_score is None


def test_dropped_columns_are_gone():
    columns = {c.name for c in CodeEvaluation.__table__.columns}
    for name in ("corrected_code", "security_score", "quality_score",
                 "documentation_score"):
        assert name not in columns


def test_submission_eval_status_columns_moved():
    columns = {c.name for c in CodeSubmission.__table__.columns}
    assert "status" not in columns
    assert "eval_count" not in columns
    assert "problem_id" in columns


def test_new_evaluation_columns_exist():
    columns = {c.name for c in CodeEvaluation.__table__.columns}
    for name in ("mode", "verification_status", "unverified_reason", "tests_total",
                 "tests_passed", "complexity_score", "attempt_number", "status"):
        assert name in columns


def test_execution_result_allows_null_test_case(session):
    session.add(ExecutionResult(
        evaluation_id=None, test_case_id=None, role=ExecRole.STUDENT,
        status="ok", stdout="", stderr="", time_ms=1,
    ))
    session.commit()
    assert session.query(ExecutionResult).count() == 1


def test_expected_indexes_declared():
    submission_indexes = {tuple(c.name for c in idx.columns)
                          for idx in CodeSubmission.__table__.indexes}
    assert ("user_id", "created_at") in submission_indexes
    assert ("problem_id",) in submission_indexes

    evaluation_indexes = {tuple(c.name for c in idx.columns)
                          for idx in CodeEvaluation.__table__.indexes}
    assert ("user_id", "created_at") in evaluation_indexes


def test_duplicate_stdin_rejected_per_problem(session):
    problem = Problem(source=ProblemSource.DSA, statement="s", statement_hash="f" * 64)
    session.add(problem)
    session.commit()
    for _ in range(2):
        session.add(TestCase(
            problem_id=problem.id, kind=TestCaseKind.NORMAL, stdin="1",
            expected_stdout="1", stdin_hash="9" * 64,
            origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1,
        ))
    with pytest.raises(IntegrityError):
        session.commit()
