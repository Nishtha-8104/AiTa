from app.features.grading.schemas import Language, SubmitCodeRequest
from app.features.grading.service import CodeEvalService
from app.features.problems.models import IOMode, Problem, ProblemSource


def _problem(session, source: ProblemSource, statement_hash: str) -> Problem:
    problem = Problem(
        source=source, statement="s", statement_hash=statement_hash,
        io_mode=IOMode.STDIN_STDOUT,
    )
    session.add(problem)
    session.commit()
    return problem


def _submit(session, problem_id):
    req = SubmitCodeRequest(
        language=Language.PYTHON, code="print(1)", problem_id=problem_id,
    )
    return CodeEvalService.submit(session, user_id=1, req=req)


def test_generated_problem_is_not_from_bank(session):
    problem = _problem(session, ProblemSource.GENERATED, "a" * 64)

    submission = _submit(session, problem.id)

    assert submission.problem_id == problem.id
    assert submission.from_bank is False


def test_dsa_problem_is_from_bank(session):
    problem = _problem(session, ProblemSource.DSA, "b" * 64)

    assert _submit(session, problem.id).from_bank is True


def test_mbpp_problem_is_from_bank(session):
    problem = _problem(session, ProblemSource.MBPP, "c" * 64)

    assert _submit(session, problem.id).from_bank is True


def test_no_problem_is_not_from_bank(session):
    assert _submit(session, None).from_bank is False


def test_unknown_problem_id_is_not_from_bank(session):
    assert _submit(session, 4242).from_bank is False
