import pytest

from app.core.exceptions import ExecutorUnavailable, LLMUnavailable
from app.features.grading.agent.schemas import GeneratedCase, GeneratedTests
from app.features.grading.logic.execution.base import ExecResult, ExecStatus
from app.features.problems.logic.generation import generate_problem
from app.features.problems.logic.listing import list_bank_problems
from app.features.problems.logic.schemas import ProblemDraft
from app.features.problems.models import Difficulty, ProblemSource
from tests.conftest import FakeExecutionProvider

REFERENCE = "print(sum(map(int, input().split())))"


class FakeDraftRunnable:
    """`structured()` is built with include_raw=True, so a call returns this shape."""

    def __init__(self, draft):
        self.draft = draft
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return {"parsed": self.draft, "raw": None}


def draft(statement="Read two integers and print their sum.",
          hints=("Read the line, then split it",)) -> ProblemDraft:
    return ProblemDraft(
        title="Two Integers",
        statement=statement,
        constraints=["1 <= a <= 100", "1 <= b <= 100"],
        hints=list(hints),
    )


class ExplodingProvider(FakeExecutionProvider):
    """The executor sidecar being unreachable, as `run_batch` reports it."""

    def __init__(self):
        super().__init__([])

    def run_batch(self, language, source, stdins, limits):
        raise ExecutorUnavailable("executor unreachable: [Errno 11001] getaddrinfo failed")


def suite_for(*pairs) -> GeneratedTests:
    return GeneratedTests(
        reference_solution=REFERENCE,
        cases=[GeneratedCase(kind="normal", stdin=s, expected_stdout=e, rationale="r")
               for s, e in pairs],
    )


def static(result):
    return lambda **kwargs: result


def ok(stdout):
    return ExecResult(status=ExecStatus.OK, stdout=stdout, time_ms=1)


@pytest.fixture
def agreeing():
    """A generator and provider that agree on three cases."""
    return (
        static(suite_for(("1 2\n", "3"), ("4 5\n", "9"), ("0 0\n", "0"))),
        FakeExecutionProvider([ok("3\n"), ok("9\n"), ok("0\n")]),
    )


def test_generated_problem_is_persisted_and_gradeable(session, agreeing):
    generator, provider = agreeing

    result = generate_problem(
        session, "arrays", "easy",
        runnable=FakeDraftRunnable(draft()), generator=generator, provider=provider,
    )

    problem = result.problem
    assert problem.id is not None
    assert problem.source is ProblemSource.GENERATED
    assert problem.difficulty is Difficulty.EASY
    assert problem.topic == "arrays"
    assert len(problem.test_cases) == 3
    assert result.ungradeable_reason is None
    assert result.title == "Two Integers"
    assert result.hints == ["Read the line, then split it"]


def test_generated_problem_stays_out_of_the_bank(session, agreeing):
    generator, provider = agreeing

    generate_problem(session, "arrays", "easy", runnable=FakeDraftRunnable(draft()),
                     generator=generator, provider=provider)

    assert list_bank_problems(session) == []


def test_constraints_are_stored_on_the_row(session, agreeing):
    generator, provider = agreeing

    result = generate_problem(session, "arrays", "easy",
                              runnable=FakeDraftRunnable(draft()),
                              generator=generator, provider=provider)

    assert result.problem.constraints == "1 <= a <= 100\n1 <= b <= 100"


def test_same_statement_reuses_the_row(session, agreeing):
    generator, provider = agreeing
    first = generate_problem(session, "arrays", "easy",
                             runnable=FakeDraftRunnable(draft()),
                             generator=generator, provider=provider)

    def explode(**kwargs):
        raise AssertionError("cached test cases must not be regenerated")

    second = generate_problem(session, "arrays", "easy",
                              runnable=FakeDraftRunnable(draft()),
                              generator=explode, provider=provider)

    assert second.problem.id == first.problem.id
    assert len(list_bank_problems(session)) == 0
    assert len(second.problem.test_cases) == 3


def test_unverified_suite_keeps_the_row_and_reports(session):
    generator = static(suite_for(("1 2\n", "3"), ("4 5\n", "99"), ("0 0\n", "98")))
    provider = FakeExecutionProvider([ok("3\n"), ok("9\n"), ok("0\n")])

    result = generate_problem(session, "arrays", "easy",
                              runnable=FakeDraftRunnable(draft()),
                              generator=generator, provider=provider)

    assert result.ungradeable_reason == "insufficient_agreed_tests"
    assert result.problem.id is not None
    assert result.problem.test_cases == []


def test_test_generation_outage_keeps_the_row_and_reports(session):
    def unavailable(**kwargs):
        raise LLMUnavailable("codegen model is down")

    result = generate_problem(session, "arrays", "easy",
                              runnable=FakeDraftRunnable(draft()),
                              generator=unavailable,
                              provider=FakeExecutionProvider([]))

    assert result.ungradeable_reason == "tests_unavailable"
    assert result.problem.id is not None
    assert result.problem.test_cases == []


def test_unparsed_draft_is_an_outage(session):
    class NoParse:
        def invoke(self, prompt):
            return {"parsed": None, "raw": None}

    with pytest.raises(LLMUnavailable):
        generate_problem(session, "arrays", "easy", runnable=NoParse())


def test_executor_outage_keeps_the_row_and_reports(session):
    result = generate_problem(session, "arrays", "easy",
                              runnable=FakeDraftRunnable(draft()),
                              generator=static(suite_for(("1 2\n", "3"))),
                              provider=ExplodingProvider())

    assert result.ungradeable_reason == "executor_unavailable"
    assert result.problem.id is not None
    assert result.problem.test_cases == []


def test_unknown_difficulty_records_the_one_generated_at(session, agreeing):
    generator, provider = agreeing

    result = generate_problem(session, "arrays", "nonsense",
                              runnable=FakeDraftRunnable(draft()),
                              generator=generator, provider=provider)

    # Never NULL: the row must not claim a difficulty the prompt did not ask for,
    # and must not leave the response with nothing truthful to report.
    assert result.problem.difficulty is Difficulty.MEDIUM


def test_hints_are_capped(session, agreeing):
    generator, provider = agreeing
    walkthrough = [
        "Use a sliding window over the array",
        "Expand the right edge and add each element to a running sum",
        "Shrink from the left while the sum still qualifies",
        "Continue until the right edge reaches the end",
    ]

    result = generate_problem(session, "arrays", "hard",
                              runnable=FakeDraftRunnable(draft(hints=walkthrough)),
                              generator=generator, provider=provider)

    assert result.hints == walkthrough[:2]
