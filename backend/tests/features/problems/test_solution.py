import pytest

from app.core.exceptions import LLMUnavailable
from app.features.accounts.models import User
from app.features.gamification.models import GamificationAward
from app.features.grading.logic.execution.base import ExecStatus
from app.features.grading.models import Language
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.learner_model.service import EventInput
from app.features.problems.logic.solution import SolutionLocked, reveal
from app.features.problems.models import (
    Problem,
    ProblemReference,
    ProblemSource,
    ReferenceStatus,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)
from tests.conftest import FakeExecutionProvider, failing, ok

PYTHON_REF = "for _ in range(int(input())):\n    a, b = map(int, input().split())\n    print(a + b)\n"
C_PORT = "#include <stdio.h>\nint main(void) { return 0; }\n"


@pytest.fixture
def user(session):
    u = User(email="g@example.com", username="giver", preferred_language="c")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def problem(session):
    p = Problem(source=ProblemSource.DSA, statement="Print a + b.", statement_hash="s" * 64,
                topic="loops")
    session.add(p)
    session.commit()
    for i, (stdin, out) in enumerate((("1 2\n", "3"), ("4 5\n", "9")), start=1):
        session.add(TestCase(problem_id=p.id, kind=TestCaseKind.NORMAL, stdin=stdin,
                             expected_stdout=out, stdin_hash=str(i) * 64,
                             origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=i))
    session.add(ProblemReference(problem_id=p.id, language=Language.PYTHON, source=PYTHON_REF,
                                 status=ReferenceStatus.VALIDATED))
    session.commit()
    session.refresh(p)
    return p


class Porter:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def passing():
    return FakeExecutionProvider([ok("3\n9\n")])


def test_give_up_is_one_failed_attempt_and_the_answer_counts_as_seen(session, user, problem):
    reveal(session, user.id, problem, "python", give_up=True)
    reveal(session, user.id, problem, "python", give_up=True)

    events = session.query(LearningEvent).filter_by(user_id=user.id).all()
    assert len(events) == 1
    assert events[0].score == 0.0 and events[0].source_ref == "give_up"
    after_give_up = session.get(TopicMastery, (user.id, "loops", "python")).mastery
    assert after_give_up < 0.3

    solved = ingest(session, EventInput(user_id=user.id, kind="code", score=1.0,
                                        raw_topic="loops", item_id=problem.id,
                                        language="python"))
    assert solved.mastery_after == pytest.approx(after_give_up)
    assert session.query(GamificationAward).filter_by(user_id=user.id).count() == 0


def test_solution_stays_locked_until_a_pass(session, user, problem):
    with pytest.raises(SolutionLocked):
        reveal(session, user.id, problem, "python", give_up=False)

    ingest(session, EventInput(user_id=user.id, kind="code", score=1.0, raw_topic="loops",
                               item_id=problem.id, language="python"))
    solution = reveal(session, user.id, problem, "python", give_up=False)
    assert (solution.language, solution.code) == ("python", PYTHON_REF)


def test_c_student_gets_a_validated_port_that_is_cached(session, user, problem):
    porter = Porter(C_PORT)
    provider = passing()

    first = reveal(session, user.id, problem, "c", give_up=True, porter=porter, provider=provider)
    again = reveal(session, user.id, problem, "c", give_up=False, porter=porter, provider=provider)

    assert (first.language, first.code) == ("c", C_PORT)
    assert again.code == C_PORT
    assert len(porter.calls) == 1
    assert provider.calls[0]["language"] is Language.C
    assert provider.calls[0]["stdins"] == ["2\n1 2\n4 5\n"]


def test_a_port_that_fails_the_tests_falls_back_to_python_and_is_not_retried(
        session, user, problem):
    porter = Porter("wrong one", "wrong two")
    provider = FakeExecutionProvider([failing(ExecStatus.COMPILE_ERROR, compile_output="err")])

    solution = reveal(session, user.id, problem, "c", give_up=True, porter=porter,
                      provider=provider)
    later = reveal(session, user.id, problem, "c", give_up=False, porter=porter,
                   provider=provider)

    assert (solution.language, solution.code) == ("python", PYTHON_REF)
    assert later.language == "python"
    assert len(porter.calls) == 2
    assert "did not compile" in porter.calls[1]["failure"]
    failed = [r for r in problem.references if r.language is Language.C]
    assert [r.status for r in failed] == [ReferenceStatus.FAILED]


def test_an_llm_outage_falls_back_without_caching_a_failure(session, user, problem):
    porter = Porter(LLMUnavailable("down"), C_PORT)

    first = reveal(session, user.id, problem, "c", give_up=True, porter=porter,
                   provider=passing())
    second = reveal(session, user.id, problem, "c", give_up=False, porter=porter,
                    provider=passing())

    assert first.language == "python"
    assert (second.language, second.code) == ("c", C_PORT)
