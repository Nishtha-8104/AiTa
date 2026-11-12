"""Assessment policy. Runtime problem generation is always stubbed here."""

from types import SimpleNamespace

import pytest

from app.core.exceptions import LLMUnavailable
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.service import EventInput
from app.features.practice.agent.graph import next_item
from app.features.practice.logic.assessment import policy
from app.features.practice.logic.assessment.grading import grade_mcq
from app.features.practice.logic.assessment.policy import NothingToServe
from app.features.practice.models import DebugAttempt, DebugChallenge, McqQuestion
from app.features.problems.models import (
    Difficulty,
    Problem,
    ProblemSource,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)

_ids = iter(range(1, 10_000))


@pytest.fixture(autouse=True)
def no_generation(monkeypatch):
    def refuse(*a, **k):
        raise LLMUnavailable("generation is stubbed in tests")
    monkeypatch.setattr(policy, "generate_problem", refuse)


def add_mcq(session, topic, difficulty="easy", language="c"):
    n = next(_ids)
    q = McqQuestion(external_id=f"q{n}", topic=topic, difficulty=difficulty, stem=f"stem {n}",
                    options=[{"text": "1", "misconception": None},
                             {"text": "2", "misconception": "off_by_one"}],
                    answer_index=0, verify_code="", explanations=["why"],
                    reviewed=True, language=language)
    session.add(q)
    session.commit()
    return q


def add_problem(session, topic, difficulty="easy"):
    n = next(_ids)
    p = Problem(source=ProblemSource.DSA, statement=f"p{n}", statement_hash=f"{n:064d}",
                topic=topic, difficulty=Difficulty(difficulty))
    p.test_cases = [TestCase(kind=TestCaseKind.SAMPLE, stdin="1\n", expected_stdout="1",
                             stdin_hash="s", origin=TestCaseOrigin.PROBLEM_SAMPLE)]
    session.add(p)
    session.commit()
    return p


def add_debug(session, problem, topic, difficulty="easy", language="c"):
    n = next(_ids)
    c = DebugChallenge(external_id=f"d{n}", problem_id=problem.id, topic=topic,
                       difficulty=difficulty, language=language, statement="s",
                       buggy_code="bug", fixed_code="SECRET_FIX", bug_type="off_by_one",
                       reviewed=True)
    session.add(c)
    session.commit()
    return c


def practise(session, user, topic, score, times=1, kind="code"):
    for _ in range(times):
        ingest(session, EventInput(user_id=user.id, kind=kind, score=score, raw_topic=topic))


def test_c_student_sees_only_c_and_concept_items(session, user):
    c_q, concept = add_mcq(session, "basics_io"), add_mcq(session, "basics_io", language="any")
    add_mcq(session, "basics_io", language="python")
    problem = add_problem(session, "basics_io", "medium")
    c_debug = add_debug(session, problem, "basics_io", "medium")
    add_debug(session, problem, "basics_io", "medium", language="python")

    plan = policy.load_profile(session, user.id)
    plan.topic, plan.item_type, plan.difficulty = "basics_io", "mcq", "easy"
    served = []
    for _ in range(2):
        item = policy.pick_item(session, plan).item
        served.append(item["id"])
        assert item["language"] in ("c", "any")
        grade_mcq(session, user.id, item["id"], 0)
    assert sorted(served) == sorted([c_q.id, concept.id])
    assert policy.pick_item(session, plan).item_type == "debug"

    plan.item_type, plan.difficulty = "debug", "medium"
    assert policy.pick_item(session, plan).item["id"] == c_debug.id
    session.add(DebugAttempt(user_id=user.id, challenge_id=c_debug.id, submitted_code="x",
                             fixed=True))
    session.commit()
    after = policy.pick_item(session, plan)
    assert after.item_type == "coding" and after.item["id"] == problem.id


def test_weakest_unlocked_topic_gets_an_mcq(session, user):
    q = add_mcq(session, "basics_io")
    add_mcq(session, "conditionals")

    item = next_item(session, user.id)

    assert (item.item_type, item.topic, item.difficulty) == ("mcq", "basics_io", "easy")
    assert item.item["id"] == q.id
    assert "haven't practised" in item.reason


def test_prerequisites_gate_topics(session, user):
    add_mcq(session, "conditionals")
    add_mcq(session, "basics_io")
    practise(session, user, "basics_io", 1.0, times=3)
    add_mcq(session, "loops")

    item = next_item(session, user.id)
    assert item.topic == "conditionals"


def test_developing_topic_alternates_coding_and_debug(session, user):
    problem = add_problem(session, "basics_io", "medium")
    challenge = add_debug(session, problem, "basics_io", "medium")
    practise(session, user, "basics_io", 1.0, times=2)
    for topic in ("conditionals", "functions"):
        practise(session, user, topic, 1.0, times=6)

    first = next_item(session, user.id)
    assert (first.item_type, first.difficulty) == ("debug", "medium")
    assert first.item["id"] == challenge.id

    practise(session, user, "basics_io", 0.2, kind="debug")
    second = next_item(session, user.id)
    assert (second.item_type, second.item["id"]) == ("coding", problem.id)


def test_mastered_topic_gets_a_hard_coding_problem(session, user):
    hard = add_problem(session, "basics_io", "hard")
    add_problem(session, "basics_io", "easy")
    for topic in ("basics_io", "conditionals", "functions", "loops", "arrays", "strings",
                  "hashing_sets", "recursion", "sorting", "searching", "stacks_queues",
                  "dynamic_programming"):
        practise(session, user, topic, 1.0, times=8 if topic != "basics_io" else 6)

    item = next_item(session, user.id)
    assert (item.item_type, item.topic, item.difficulty) == ("coding", "basics_io", "hard")
    assert item.item["id"] == hard.id


def test_correct_answers_are_never_repeated_wrong_ones_can_be(session, user):
    a = add_mcq(session, "basics_io")
    b = add_mcq(session, "basics_io")

    grade_mcq(session, user.id, a.id, 0)
    assert next_item(session, user.id).item["id"] == b.id

    grade_mcq(session, user.id, b.id, 1)
    assert next_item(session, user.id).item["id"] == b.id


def test_empty_difficulty_steps_down_then_changes_type(session, user):
    practise(session, user, "basics_io", 1.0, times=2)
    for topic in ("conditionals", "functions"):
        practise(session, user, topic, 1.0, times=6)
    easy = add_problem(session, "basics_io", "easy")

    item = next_item(session, user.id)
    assert (item.item_type, item.difficulty, item.item["id"]) == ("coding", "easy", easy.id)
    assert "no medium one was left" in item.reason


def test_bank_miss_falls_back_to_generation(session, user, monkeypatch):
    generated = add_problem(session, "strings", "easy")
    generated.source = ProblemSource.GENERATED
    session.commit()
    calls = []

    def fake_generate(db, topic, difficulty):
        calls.append((topic, difficulty))
        return SimpleNamespace(problem=generated, ungradeable_reason=None)

    monkeypatch.setattr(policy, "generate_problem", fake_generate)
    practise(session, user, "basics_io", 1.0, times=2)
    for topic in ("conditionals", "functions"):
        practise(session, user, topic, 1.0, times=6)

    item = next_item(session, user.id)
    assert calls == [("Loops", "easy")]
    assert (item.topic, item.item["id"]) == ("loops", generated.id)
    assert "generated" in item.reason


def test_three_misses_in_a_row_rotate_to_another_topic_once(session, user):
    loops_q = add_mcq(session, "loops")
    add_mcq(session, "loops")
    functions_q = add_mcq(session, "functions")
    add_mcq(session, "functions")
    for topic in ("basics_io", "conditionals"):
        practise(session, user, topic, 1.0, times=2)
    practise(session, user, "functions", 1.0, times=1)

    practise(session, user, "loops", 0.0, times=3, kind="mcq")
    rotated = next_item(session, user.id)
    assert (rotated.topic, rotated.item["id"]) == ("functions", functions_q.id)
    assert "you missed Loops 3 times in a row" in rotated.reason

    grade_mcq(session, user.id, functions_q.id, 0)
    back = next_item(session, user.id)
    assert back.topic == "loops"
    assert back.item["id"] in {loops_q.id, loops_q.id + 1}


def test_misses_across_topics_do_not_count_as_stuck(session, user):
    practise(session, user, "loops", 0.0, times=2, kind="mcq")
    practise(session, user, "arrays", 0.0, kind="mcq")
    assert policy.stuck_topic(session, user.id) is None


def test_nothing_left_anywhere_raises(session, user):
    with pytest.raises(NothingToServe):
        next_item(session, user.id)


def test_payloads_never_carry_answers(session, user):
    problem = add_problem(session, "basics_io")
    add_debug(session, problem, "basics_io")
    add_mcq(session, "basics_io")

    mcq = next_item(session, user.id)
    assert set(mcq.item) == {"id", "stem", "options", "topic", "difficulty", "language",
                             "is_diagnostic"}
    assert mcq.item["options"] == ["1", "2"]

    debug = policy.debug_payload(session.query(DebugChallenge).one())
    assert "SECRET_FIX" not in str(debug)
    assert "bug_type" not in debug and "fixed_code" not in debug


def test_passed_coding_problem_is_not_served_again(session, user):
    problem = add_problem(session, "basics_io", "medium")
    submission = CodeSubmission(user_id=user.id, language=Language.PYTHON, code="x",
                                problem_id=problem.id, title="t")
    session.add(submission)
    session.flush()
    session.add(CodeEvaluation(submission_id=submission.id, user_id=user.id,
                               tests_total=1, tests_passed=1, status="done"))
    session.commit()

    assert problem.id in policy._passed_problem_ids(session, user.id)
