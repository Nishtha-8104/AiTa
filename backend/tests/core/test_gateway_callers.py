from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from app.core import llm_gateway
from app.core.config import settings
from app.core.exceptions import LLMUnavailable
from app.core.llm_gateway import Gateway, GatewayResult
from app.features.feedback.agent.nodes.synthesise import synthesise
from app.features.feedback.agent.schemas import FeedbackNarrative
from app.features.feedback.agent.state import FeedbackState
from app.features.grading.agent.nodes.explain import explain
from app.features.grading.agent.schemas import Explanation, GeneratedTests
from app.features.grading.agent.state import EvalState
from app.features.grading.models import Language
from app.features.hints.logic.prompts import TEMPLATES
from app.features.hints.service import FailingCase, _ladder_hint
from app.features.practice.logic.assessment.generation import _ask
from app.features.practice.logic.assessment.theory import GraderBusy, TheoryVerdict, _judge
from app.features.problems.logic.generation import _draft
from app.features.problems.logic.schemas import ProblemDraft
from app.features.problems.logic.solution import PortedSolution, _default_porter
from app.features.problems.logic.test_generation.generate_tests import _default_generator


def _explain(db):
    explain(EvalState(db=db, submission_id=1, user_id=7, language=Language.PYTHON))


def _feedback(db):
    synthesise(FeedbackState(
        db=db, user_id=7,
        user_ctx={"username": "u", "skill": "beginner", "languages": [], "weak_areas": []},
        patterns={"errors": [], "weak_concepts": [], "strengths": []},
    ))


def _hint(db):
    return _ladder_hint(db, 2, SimpleNamespace(statement="s", test_cases=[], references=[], id=1),
                        SimpleNamespace(language=Language.PYTHON, code="print(1)"),
                        FailingCase("1\n", "2", "3"), 7, 1, None, None)


def _port(db):
    _default_porter(language=Language.C, statement="s", reference="print(1)",
                    previous=None, failure=None)


def _theory(db):
    question = SimpleNamespace(language="c", question="q", key_points=["a", "b"])
    with pytest.raises(GraderBusy):
        _judge(7, question, "an answer")


def _problem(db):
    with pytest.raises(LLMUnavailable):
        _draft("loops", "easy", None)


CALLERS = [
    ("explain", _explain, Explanation, 7),
    ("feedback", _feedback, FeedbackNarrative, 7),
    ("hint", _hint, None, 7),
    ("assessment_gen", lambda db: _ask(None, "p"), None, None),
    ("problem_gen", _problem, ProblemDraft, None),
    ("test_gen", lambda db: _default_generator(statement="s", count=3), GeneratedTests, None),
    ("solution_port", _port, PortedSolution, None),
    ("theory_judge", _theory, TheoryVerdict, 7),
]


@pytest.mark.parametrize("purpose, drive, schema, user_id", CALLERS,
                         ids=[c[0] for c in CALLERS])
def test_caller_uses_its_purpose(purpose, drive, schema, user_id, session, monkeypatch):
    calls = []

    def record(name, payload, **kwargs):
        calls.append((name, kwargs.get("schema"), kwargs.get("user_id")))
        return GatewayResult(None, "ok", "m", 0, 0, 0, 0)

    monkeypatch.setattr(llm_gateway, "invoke", record)
    drive(session)
    assert calls and set(calls) == {(purpose, schema, user_id)}


def test_real_client_under_the_guard_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "k0")
    monkeypatch.setattr(settings, "REDIS_URL", "")
    monkeypatch.setattr(llm_gateway, "_gateway", Gateway(session_factory=lambda: None))

    with pytest.raises(AssertionError, match="real LLM client"):
        llm_gateway.invoke("hint", "p", template="t")


def test_hint_ladder_falls_back_to_template_when_gateway_fails(session, monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "k0")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY_2", "")
    monkeypatch.setattr(settings, "NVIDIA_FALLBACK_MODEL", "")
    monkeypatch.setattr(settings, "REDIS_URL", "")

    def fail(*args, **kwargs):
        raise Exception("Error code: 429 - rate limit exceeded")

    gateway = Gateway(session_factory=sessionmaker(bind=session.get_bind()),
                      model_factory=fail)
    monkeypatch.setattr(llm_gateway, "_gateway", gateway)

    hint = _hint(session)
    assert (hint.source, hint.text, hint.was_blocked) == ("template", TEMPLATES[2], False)
