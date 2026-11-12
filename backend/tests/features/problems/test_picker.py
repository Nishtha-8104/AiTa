import pytest

from app.features.problems.logic.picker import pick_problem, requested_difficulty
from app.features.problems.models import (
    Difficulty,
    IOMode,
    Problem,
    ProblemSource,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)

_HASHES = iter(f"{n:064x}" for n in range(1, 500))


@pytest.fixture
def make_problem(session):
    def _make(source=ProblemSource.DSA, topic="arrays", difficulty=Difficulty.EASY,
              with_tests=True):
        problem = Problem(
            source=source, statement="Add two numbers", statement_hash=next(_HASHES),
            topic=topic, difficulty=difficulty, io_mode=IOMode.STDIN_STDOUT,
        )
        session.add(problem)
        session.commit()
        if with_tests:
            session.add(TestCase(
                problem_id=problem.id, kind=TestCaseKind.SAMPLE,
                stdin="1 2\n", expected_stdout="3", stdin_hash=next(_HASHES),
                origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1,
            ))
            session.commit()
        return problem
    return _make


def test_returns_curated_match(session, make_problem):
    problem = make_problem()

    picked = pick_problem(session, topic="arrays", difficulty="easy")

    assert picked is not None
    assert picked.id == problem.id


def test_topic_match_is_case_insensitive(session, make_problem):
    problem = make_problem(topic="Dynamic Programming")

    picked = pick_problem(session, topic="dynamic programming", difficulty="easy")

    assert picked is not None and picked.id == problem.id


@pytest.mark.parametrize("asked", ["dynamic programming", "DP", "dynamic_programming"])
def test_free_text_topic_finds_the_canonical_bank_topic(session, make_problem, asked):
    problem = make_problem(topic="dynamic_programming")

    picked = pick_problem(session, topic=asked, difficulty="easy")

    assert picked is not None and picked.id == problem.id


def test_student_problem_is_never_picked(session, make_problem):
    make_problem(source=ProblemSource.STUDENT)

    assert pick_problem(session, topic="arrays", difficulty="easy") is None


def test_generated_problem_is_never_picked(session, make_problem):
    make_problem(source=ProblemSource.GENERATED)

    assert pick_problem(session, topic="arrays", difficulty="easy") is None


def test_excluded_ids_are_skipped(session, make_problem):
    first = make_problem()
    second = make_problem()

    picked = pick_problem(session, topic="arrays", difficulty="easy",
                          exclude_ids=[first.id])

    assert picked is not None and picked.id == second.id


def test_every_candidate_excluded_returns_none(session, make_problem):
    first = make_problem()
    second = make_problem()

    assert pick_problem(session, topic="arrays", difficulty="easy",
                        exclude_ids=[first.id, second.id]) is None


def test_curated_problem_without_test_cases_is_skipped(session, make_problem):
    make_problem(with_tests=False)
    gradeable = make_problem()

    picked = pick_problem(session, topic="arrays", difficulty="easy")

    assert picked is not None and picked.id == gradeable.id


def test_no_match_returns_none(session, make_problem):
    make_problem(topic="arrays", difficulty=Difficulty.EASY)

    assert pick_problem(session, topic="graphs", difficulty="easy") is None
    assert pick_problem(session, topic="arrays", difficulty="hard") is None


def test_invalid_difficulty_returns_none(session, make_problem):
    make_problem()

    assert pick_problem(session, topic="arrays", difficulty="nonsense") is None


def test_expert_resolves_to_hard(session, make_problem):
    hard = make_problem(topic="arrays", difficulty=Difficulty.HARD)
    make_problem(topic="arrays", difficulty=Difficulty.EASY)

    assert requested_difficulty("expert") is Difficulty.HARD
    assert requested_difficulty("nonsense") is None
    picked = pick_problem(session, topic="arrays",
                          difficulty=requested_difficulty("expert"))
    assert picked is not None and picked.id == hard.id


def test_omitted_filters_do_not_narrow(session, make_problem):
    problem = make_problem(topic="trees", difficulty=Difficulty.HARD)

    assert pick_problem(session).id == problem.id
    assert pick_problem(session, topic="trees").id == problem.id
    assert pick_problem(session, difficulty="hard").id == problem.id
