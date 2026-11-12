"""Hint ladder, guardrail and leak metric. Stubbed executor and LLM throughout."""

from types import SimpleNamespace

import pytest

from app.features.accounts.models import User
from app.features.grading.agent.graph import evaluate_submission
from app.features.grading.agent.schemas import Explanation
from app.features.grading.models import CodeSubmission, Language
from app.features.hints.logic import guardrail
from app.features.hints.logic.guardrail import states_fix as real_states_fix
from app.features.hints.logic.prompts import TEMPLATES
from app.features.hints.models import HintEvent
from app.features.hints.service import (
    NoHintAvailable,
    leak_rate,
    next_level,
    request_hint,
)
from app.features.learner_model.models import LearningEvent
from app.features.problems.models import (
    Problem,
    ProblemSource,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)
from tests.conftest import FakeExecutionProvider
from tests.features.grading.test_graph import FakeExplainRunnable, merged, ok

SOLUTION = "for _ in range(int(input())):\n    print(max(map(int, input().split())))"


@pytest.fixture
def user(session):
    u = User(email="h@example.com", username="hinted")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def problem(session):
    p = Problem(source=ProblemSource.DSA, statement="Print the largest value.",
                statement_hash="h" * 64, topic="arrays")
    p.test_cases = [
        TestCase(kind=TestCaseKind.SAMPLE, stdin="3 1 2\n", expected_stdout="3",
                 stdin_hash="a", origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=0),
        TestCase(kind=TestCaseKind.EDGE, stdin="-4 -9\n", expected_stdout="-4",
                 stdin_hash="b", origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1,
                 rationale="all negative"),
    ]
    session.add(p)
    session.commit()
    return p


def attempt(session, user, problem, output):
    s = CodeSubmission(user_id=user.id, language=Language.PYTHON, code="print(0)",
                       problem_id=problem.id, title="t")
    session.add(s)
    session.commit()
    return evaluate_submission(
        session, s.id, user.id,
        provider=FakeExecutionProvider(merged(output)),
        explain_runnable=FakeExplainRunnable(Explanation(summary="s", detailed_feedback="f")),
    )


class FakeHintLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        text = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return SimpleNamespace(content=text)


def test_failing_submission_returns_l1_inline_and_logs_it(session, user, problem):
    report = attempt(session, user, problem, "3\n0\n")

    assert report.hint.level == 1
    assert "-4 -9" in report.hint.text
    assert "`-4`" in report.hint.text and "`0`" in report.hint.text
    assert "all negative" in report.hint.text
    event = session.query(HintEvent).one()
    assert (event.level, event.evaluation_id) == (1, report.evaluation_id)


def test_passing_submission_carries_no_hint(session, user, problem):
    report = attempt(session, user, problem, "3\n-4\n")
    assert report.hint is None
    assert session.query(HintEvent).count() == 0


def test_ladder_climbs_one_level_per_request_and_caps_at_four(session, user, problem):
    attempt(session, user, problem, "3\n0\n")
    llm = FakeHintLLM("Think about what the starting value assumes.")

    levels = [request_hint(session, user.id, problem.id, runnable=llm).level
              for _ in range(4)]

    assert levels == [2, 3, 4, 4]
    assert "LEVEL 2" in llm.prompts[0] and "LEVEL 4" in llm.prompts[2]
    assert "input:\n-4 -9\nexpected output:\n-4\ntheir program printed:\n0" in llm.prompts[0]


def test_full_pass_resets_the_ladder(session, user, problem):
    attempt(session, user, problem, "3\n0\n")
    llm = FakeHintLLM("concept")
    request_hint(session, user.id, problem.id, runnable=llm)
    request_hint(session, user.id, problem.id, runnable=llm)

    attempt(session, user, problem, "3\n-4\n")
    with pytest.raises(NoHintAvailable):
        request_hint(session, user.id, problem.id, runnable=llm)

    attempt(session, user, problem, "3\n0\n")
    assert next_level(session, user.id, problem.id) == 2


def test_no_attempt_means_no_hint(session, user, problem):
    with pytest.raises(NoHintAvailable):
        request_hint(session, user.id, problem.id, runnable=FakeHintLLM("x"))


def test_guardrail_blocks_a_reply_whose_code_passes_the_tests(session, user, problem):
    attempt(session, user, problem, "3\n0\n")
    leaky = f"Try this:\n```python\n{SOLUTION}\n```"
    provider = FakeExecutionProvider([ok("3\n-4\n")])

    hint = request_hint(session, user.id, problem.id,
                        runnable=FakeHintLLM(leaky), provider=provider)

    assert hint.source == "template"
    assert hint.text == TEMPLATES[2]
    assert SOLUTION not in hint.text
    assert session.query(HintEvent).filter_by(level=2).one().was_blocked is True
    assert leak_rate(session) == (1, 1)


def test_regenerates_once_before_falling_back(session, user, problem):
    attempt(session, user, problem, "3\n0\n")
    leaky = f"```python\n{SOLUTION}\n```"
    llm = FakeHintLLM(leaky, "What does your code assume before the first value?")

    hint = request_hint(session, user.id, problem.id, runnable=llm,
                        provider=FakeExecutionProvider([ok("3\n-4\n")]))

    assert hint.source == "llm"
    assert len(llm.prompts) == 2
    assert session.query(HintEvent).filter_by(level=2).one().was_blocked is True


def test_a_fix_told_in_words_is_caught_by_the_judge_and_regenerated(
        session, user, problem, monkeypatch):
    attempt(session, user, problem, "3\n0\n")
    judged = []

    def judge(hint, **context):
        judged.append(context["code"])
        return "start at" in hint

    monkeypatch.setattr(guardrail, "states_fix", judge)
    llm = FakeHintLLM("Make the maximum start at the first value.",
                      "What does your code assume before the first value?")

    hint = request_hint(session, user.id, problem.id, runnable=llm)

    assert (hint.source, hint.text) == ("llm", "What does your code assume before the first value?")
    assert judged == ["print(0)", "print(0)"]
    assert session.query(HintEvent).filter_by(level=2).one().was_blocked is True


def test_fix_judge_asks_about_the_hint_and_treats_no_verdict_as_a_leak(monkeypatch):
    verdicts = [guardrail.FixVerdict(states_fix=False), guardrail.FixVerdict(states_fix=True), None]
    prompts = []

    def fake_invoke(purpose, prompt, *, schema, user_id=None):
        prompts.append((purpose, prompt))
        return SimpleNamespace(value=verdicts.pop(0))

    monkeypatch.setattr(guardrail.llm_gateway, "invoke", fake_invoke)
    context = {"statement": "Print the largest value.", "language": "python", "code": "print(0)"}

    assert [real_states_fix("Trace it by hand.", **context) for _ in range(3)] == [
        False, True, True]
    assert prompts[0][0] == "hint_check"
    assert "Trace it by hand." in prompts[0][1] and "print(0)" in prompts[0][1]


def test_guardrail_line_limits():
    three = "```\na = 1\nb = 2\nc = 3\n```"
    assert guardrail.check(three, 3, Language.PYTHON, []).blocked is False
    assert guardrail.check(three, 4, Language.PYTHON, []).reason == "too_much_code"
    assert guardrail.check("```\n" + "x=1\n" * 4 + "```", 2, Language.PYTHON, []).blocked
    assert guardrail.check("no code at all", 2, Language.PYTHON, []).blocked is False


def test_prose_quoting_a_distinctive_reference_line_is_blocked():
    reference = "import sys\nvalues = list(map(int, input().split()))\nbest = cur = values[0]\n"
    student = "values = list(map(int, input().split()))\nbest = 0\n"

    assert guardrail.quotes_reference("Set best  =  cur = values[0] first.", [reference], student)
    assert not guardrail.quotes_reference(
        "Your code reads values = list(map(int, input().split())) correctly.",
        [reference], student)
    assert not guardrail.quotes_reference("Start from the first element.", [reference], student)
    verdict = guardrail.check("Try `best = cur = values[0]`", 3, Language.PYTHON, [],
                              references=[reference], student_code=student)
    assert verdict.reason == "quotes_reference"


def test_wrong_code_block_is_allowed(session, problem):
    snippet = "```python\nprint(0)\n```"
    verdict = guardrail.check(snippet, 4, Language.PYTHON, list(problem.test_cases),
                              FakeExecutionProvider([ok("0\n0\n")]))
    assert verdict.blocked is False


def test_hint_level_discounts_the_next_attempt(session, user, problem):
    attempt(session, user, problem, "3\n0\n")
    request_hint(session, user.id, problem.id, runnable=FakeHintLLM("concept"))

    attempt(session, user, problem, "3\n-4\n")

    events = session.query(LearningEvent).order_by(LearningEvent.id).all()
    assert events[0].hint_level_used == 0
    assert events[1].hint_level_used == 2
    assert events[1].score == pytest.approx(0.75)


def test_l1_alone_discounts_the_next_attempt(session, user, problem):
    attempt(session, user, problem, "3\n0\n")
    attempt(session, user, problem, "3\n-4\n")

    last = session.query(LearningEvent).order_by(LearningEvent.id.desc()).first()
    assert last.hint_level_used == 1
    assert last.score == pytest.approx(0.9)


def test_llm_outage_falls_back_to_the_template(session, user, problem):
    from app.core.exceptions import LLMUnavailable

    class Down:
        def invoke(self, prompt):
            raise LLMUnavailable("provider down")

    attempt(session, user, problem, "3\n0\n")
    hint = request_hint(session, user.id, problem.id, runnable=Down())
    assert (hint.level, hint.source, hint.text) == (2, "template", TEMPLATES[2])
