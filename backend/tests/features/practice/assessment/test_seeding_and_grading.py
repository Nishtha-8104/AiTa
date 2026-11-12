import pytest

from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.practice.logic.assessment.grading import (
    InvalidAnswer,
    ItemNotFound,
    grade_debug,
    grade_mcq,
)
from app.features.practice.logic.assessment.seeding import seed
from app.features.practice.models import (
    DebugAttempt,
    DebugChallenge,
    McqAttempt,
    McqQuestion,
)
from tests.features.practice.assessment.conftest import (
    BUGGY,
    FIXED,
    debug_item,
    mcq,
    standard_provider,
)


def seeded(session, **extra):
    bank = {"mcqs": [mcq()], "diagnostic": [mcq(external_id="diag-loops", is_diagnostic=True)],
            "debug": [debug_item()], **extra}
    return seed(session, bank, standard_provider())


def test_seed_writes_verified_items_and_is_idempotent(session, bank_problem):
    first = seeded(session)
    assert first == {"mcq created": 2, "debug created": 1}
    assert seeded(session) == {"mcq updated": 2, "debug updated": 1}
    assert session.query(McqQuestion).count() == 2
    assert session.query(McqQuestion).filter_by(is_diagnostic=True).count() == 1
    challenge = session.query(DebugChallenge).one()
    assert challenge.problem_id == bank_problem.id and challenge.reviewed


def test_seed_rejects_items_edited_into_an_unproven_state(session, bank_problem):
    report = seed(session, {"mcqs": [mcq(answer_index=2, options=[
        {"text": "5", "misconception": "off_by_one"},
        {"text": "4", "misconception": "none_of_these"},
        {"text": "3", "misconception": None},
    ])], "debug": [debug_item(problem_external_id="missing")]}, standard_provider())
    assert report["mcq rejected"] == 1
    assert report["debug rejected: problem not seeded"] == 1
    assert session.query(McqQuestion).count() == 0


def test_correct_mcq_raises_mastery_at_half_weight(session, bank_problem, user):
    seeded(session)
    question = session.query(McqQuestion).filter_by(external_id="mcq-loops-1").one()

    result = grade_mcq(session, user.id, question.id, 1)

    assert result.correct and result.misconception is None
    assert result.mastery_after == pytest.approx(0.3 + 0.3 * 0.5 * (1 - 0.3))
    assert session.query(McqAttempt).one().correct is True
    assert session.query(LearningEvent).one().kind == "mcq"


def test_wrong_mcq_records_the_distractors_misconception(session, bank_problem, user):
    seeded(session)
    question = session.query(McqQuestion).filter_by(external_id="diag-loops").one()

    result = grade_mcq(session, user.id, question.id, 0)

    assert not result.correct
    assert result.answer_index == 1
    assert result.misconception == "off_by_one"
    event = session.query(LearningEvent).one()
    assert (event.kind, event.score, event.misconceptions) == ("diagnostic", 0.0, ["off_by_one"])


def test_mcq_errors(session, bank_problem, user):
    seeded(session)
    question = session.query(McqQuestion).first()
    with pytest.raises(InvalidAnswer):
        grade_mcq(session, user.id, question.id, 9)
    with pytest.raises(ItemNotFound):
        grade_mcq(session, user.id, 999, 0)


def test_fixed_debug_attempt_scores_full_credit(session, bank_problem, user):
    seeded(session)
    challenge = session.query(DebugChallenge).one()

    result = grade_debug(session, user.id, challenge.id, FIXED, provider=standard_provider())

    assert result.fixed and result.verdict == "Accepted"
    assert result.failing_input is None
    event = session.query(LearningEvent).one()
    assert (event.kind, event.score, event.weight, event.misconceptions) == ("debug", 1.0, 0.8, [])
    key = (user.id, "arrays", challenge.language)
    assert session.get(TopicMastery, key).mastery == pytest.approx(0.3 + 0.24 * 0.7)


def test_unfixed_debug_attempt_gets_half_partial_credit_and_the_bug_tag(session, bank_problem, user):
    seeded(session)
    challenge = session.query(DebugChallenge).one()

    result = grade_debug(session, user.id, challenge.id, BUGGY, provider=standard_provider())

    assert not result.fixed
    assert (result.tests_passed, result.tests_total) == (1, 2)
    assert (result.failing_input, result.failing_expected, result.failing_actual) == \
        ("-4 -9\n", "-4", "0")
    event = session.query(LearningEvent).one()
    assert event.score == pytest.approx(0.25)
    assert event.misconceptions == ["wrong_initial_value"]
    assert session.query(DebugAttempt).one().fixed is False
