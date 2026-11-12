import pytest

from app.features.grading.agent.schemas import GeneratedCase, GeneratedTests
from app.features.grading.logic.execution.base import ExecResult, ExecStatus
from app.features.problems.logic.test_generation.generate_tests import generate_tests
from app.features.problems.models import Problem, ProblemSource, ReferenceStatus, TestCaseOrigin
from tests.conftest import FakeExecutionProvider


@pytest.fixture
def problem(session):
    p = Problem(source=ProblemSource.DSA, statement="Sum n numbers",
                statement_hash="a" * 64)
    session.add(p)
    session.commit()
    return p


def gen(*pairs, reference="print(sum(map(int, input().split())))"):
    return GeneratedTests(
        reference_solution=reference,
        cases=[GeneratedCase(kind="normal", stdin=s, expected_stdout=e, rationale="r")
               for s, e in pairs],
    )


def static_generator(result):
    return lambda **kwargs: result


def ok(stdout):
    return ExecResult(status=ExecStatus.OK, stdout=stdout, time_ms=1)


class RoundSwitchingProvider(FakeExecutionProvider):
    """Returns a different scripted batch on each successive run_batch call."""

    def __init__(self, rounds):
        super().__init__([])
        self.rounds = rounds
        self.index = 0

    def run_batch(self, language, source, stdins, limits):
        results = self.rounds[min(self.index, len(self.rounds) - 1)]
        self.index += 1
        return results[: len(stdins)]


def test_all_agree_all_persisted(session, problem):
    generated = gen(("1\n", "1"), ("2\n", "2"), ("3\n", "3"))
    provider = FakeExecutionProvider([ok("1\n"), ok("2\n"), ok("3\n")])

    suite = generate_tests(session, problem,
                           generator=static_generator(generated), provider=provider)

    assert suite.agreed == 3
    assert suite.dropped == 0
    assert suite.unverified_reason is None
    assert len(problem.test_cases) == 3
    assert all(c.origin is TestCaseOrigin.CROSS_CHECKED for c in problem.test_cases)


def test_disagreements_are_dropped_silently(session, problem):
    generated = gen(("1\n", "1"), ("2\n", "99"), ("3\n", "3"), ("4\n", "4"))
    provider = FakeExecutionProvider([ok("1\n"), ok("2\n"), ok("3\n"), ok("4\n")])

    suite = generate_tests(session, problem,
                           generator=static_generator(generated), provider=provider)

    assert suite.agreed == 3
    assert suite.dropped == 1
    assert "99" not in [c.expected_stdout for c in problem.test_cases]


def test_persisted_expected_output_is_the_executed_one(session, problem):
    generated = gen(("1\n", "1"), ("2\n", "2"), ("3\n", "3"))
    provider = FakeExecutionProvider([ok("1\n"), ok("2  \n"), ok("3\n\n")])

    generate_tests(session, problem,
                   generator=static_generator(generated), provider=provider)

    assert sorted(c.expected_stdout for c in problem.test_cases) == ["1", "2", "3"]


def test_trailing_newline_counts_as_agreement(session, problem):
    generated = gen(("1\n", "1"), ("2\n", "2"), ("3\n", "3"))
    provider = FakeExecutionProvider([ok("1\n\n"), ok("2   \n"), ok("3")])

    suite = generate_tests(session, problem,
                           generator=static_generator(generated), provider=provider)
    assert suite.agreed == 3


def test_too_few_survivors_is_unverified(session, problem):
    generated = gen(("1\n", "1"), ("2\n", "99"), ("3\n", "98"))
    provider = FakeExecutionProvider([ok("1\n"), ok("2\n"), ok("3\n")])

    suite = generate_tests(session, problem,
                           generator=static_generator(generated), provider=provider)

    assert suite.unverified_reason == "insufficient_agreed_tests"
    assert len(problem.test_cases) == 0


def test_reference_crash_triggers_regeneration(session, problem):
    attempts = {"n": 0}

    def generator(**kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return gen(("1\n", "1"), ("2\n", "2"), ("3\n", "3"), reference="1/0")
        return gen(("1\n", "1"), ("2\n", "2"), ("3\n", "3"))

    crashed = ExecResult(status=ExecStatus.RUNTIME_ERROR, stderr="ZeroDivisionError")
    provider = RoundSwitchingProvider([
        [crashed, crashed, crashed],
        [ok("1\n"), ok("2\n"), ok("3\n")],
    ])

    suite = generate_tests(session, problem, generator=generator, provider=provider)

    assert suite.attempts == 2
    assert suite.agreed == 3
    assert problem.references[-1].status is ReferenceStatus.VALIDATED


def test_gives_up_after_max_attempts(session, problem):
    generated = gen(("1\n", "1"), ("2\n", "2"), ("3\n", "3"), reference="1/0")
    crashed = ExecResult(status=ExecStatus.RUNTIME_ERROR, stderr="boom")
    provider = RoundSwitchingProvider([[crashed, crashed, crashed]])

    suite = generate_tests(session, problem,
                           generator=static_generator(generated), provider=provider)

    assert suite.unverified_reason == "reference_unvalidated"
    assert suite.attempts == 3
    assert len(problem.test_cases) == 0
    assert problem.references[-1].status is ReferenceStatus.FAILED


def test_duplicate_stdin_is_persisted_once(session, problem):
    generated = gen(("1\n", "1"), ("1\n", "1"), ("2\n", "2"), ("3\n", "3"))
    provider = FakeExecutionProvider([ok("1\n"), ok("1\n"), ok("2\n"), ok("3\n")])

    generate_tests(session, problem,
                   generator=static_generator(generated), provider=provider)

    stdins = [c.stdin for c in problem.test_cases]
    assert len(stdins) == len(set(stdins)) == 3


def test_existing_cases_short_circuit(session, problem):
    generated = gen(("1\n", "1"), ("2\n", "2"), ("3\n", "3"))
    provider = FakeExecutionProvider([ok("1\n"), ok("2\n"), ok("3\n")])
    generate_tests(session, problem, generator=static_generator(generated),
                   provider=provider)

    def explode(**kwargs):
        raise AssertionError("generator must not run on a cache hit")

    suite = generate_tests(session, problem, generator=explode, provider=provider)
    assert suite.agreed == 3
    assert suite.attempts == 0
