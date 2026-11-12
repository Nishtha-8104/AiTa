import pytest

from app.core import llm_gateway
from app.core.exceptions import LLMUnavailable
from app.core.llm_gateway import GatewayResult
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.practice.logic.assessment.content import theory_row
from app.features.practice.logic.assessment.seeding import seed_theory
from app.features.practice.logic.assessment.theory import GraderBusy, TheoryVerdict, grade_theory
from app.features.practice.models import TheoryAttempt, TheoryQuestion

ITEM = {
    "id": "theory-c-functions-1",
    "language": "c",
    "difficulty": "medium",
    "question": "Why pass a pointer to a function instead of the value?",
    "model_answer": "The function gets the address, so it can change the caller's variable, "
                    "and a large struct is not copied.",
    "key_points": ["the function receives the variable's address",
                   "it can change the caller's variable through it",
                   "nothing large is copied"],
}


@pytest.fixture
def question(session, user):
    items = [theory_row(ITEM, "functions")]
    assert seed_theory(session, items) == {"theory created": 1}
    return session.query(TheoryQuestion).one()


def judge_says(monkeypatch, *points, feedback="ok"):
    calls = []

    def fake(purpose, prompt, **kwargs):
        calls.append(prompt)
        return GatewayResult(TheoryVerdict(points_present=list(points), feedback=feedback),
                             "ok", "m", 0, 0, 0, 0)

    monkeypatch.setattr(llm_gateway, "invoke", fake)
    return calls


def test_bank_item_seeds_as_one_reviewed_question(question):
    assert question.external_id == "theory-c-functions-1"
    assert len(question.key_points) == 3 and question.reviewed


def test_score_comes_from_key_points_and_only_the_first_answer_counts(
        session, user, question, monkeypatch):
    calls = judge_says(monkeypatch, True, False, False)
    first = grade_theory(session, user.id, question.id, "it gets the address and changes x")
    assert first.score == 0.5 and first.model_answer.startswith("The function")
    assert "<answer>" in calls[0] and "changes x" in calls[0]
    row = session.get(TopicMastery, (user.id, "functions", "c"))
    moved = row.mastery

    judge_says(monkeypatch, True, True, True)
    second = grade_theory(session, user.id, question.id, "now I know the model answer")
    assert second.score == 1.0 and second.mastery_after == moved
    kinds = [k for (k,) in session.query(LearningEvent.kind)]
    assert kinds == ["theory", "theory"]


def test_reseeding_never_rewrites_an_answered_question(session, user, question, monkeypatch):
    judge_says(monkeypatch, True, True, True)
    grade_theory(session, user.id, question.id, "an answer")
    moved = [theory_row({**ITEM, "question": "Why return a pointer from a function?"},
                        "functions")]
    assert seed_theory(session, moved) == {"theory refused: id holds an answered question": 1}
    session.refresh(question)
    assert question.question.startswith("Why pass a pointer")


def test_blank_answer_scores_zero_without_the_judge(session, user, question, monkeypatch):
    calls = judge_says(monkeypatch, True, True, True)
    result = grade_theory(session, user.id, question.id, "   ")
    assert result.score == 0.0 and result.points_present == [False] * 3
    assert calls == []


def test_unreachable_judge_records_nothing(session, user, question, monkeypatch):
    def down(*args, **kwargs):
        raise LLMUnavailable("down")

    monkeypatch.setattr(llm_gateway, "invoke", down)
    with pytest.raises(GraderBusy):
        grade_theory(session, user.id, question.id, "an answer")
    assert session.query(TheoryAttempt).count() == 0
    assert session.query(LearningEvent).count() == 0
