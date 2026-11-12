"""The model answer, shown only after a student passes or gives up.

Validated references are Python. A C or C++ student gets a port of it, kept only when it
passes every stored test of the problem, so the answer they read is one the grader
accepts. Anything short of that falls back to the Python reference."""

import logging
from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import llm_gateway
from app.core.exceptions import ExecutorUnavailable, LLMUnavailable
from app.features.grading.agent.prompts import SOLUTION_PORT_PROMPT, SOLUTION_PORT_RETRY
from app.features.grading.logic.execution.judge import judge
from app.features.grading.models import Language
from app.features.hints.service import highest_level
from app.features.learner_model.agent.graph import ingest
from app.features.learner_model.logic.mastery import GIVE_UP_REF, is_solved
from app.features.learner_model.models import LearningEvent
from app.features.learner_model.service import EventInput
from app.features.problems.models import Problem, ProblemReference, ReferenceStatus

logger = logging.getLogger(__name__)

PORT_ATTEMPTS = 2

_PORT_TARGETS = {
    Language.C: ("C (C11)", "Use only the C standard library. Read with scanf, print with printf."),
    Language.CPP: ("C++ (C++17)", "Use only the C++ standard library. Read with cin, print with cout."),
}


class PortedSolution(BaseModel):
    code: str


@dataclass
class Solution:
    language: str
    code: str


class SolutionLocked(Exception):
    pass


def _code_events(db: Session, user_id: int, problem_id: int) -> list[LearningEvent]:
    return (db.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.kind == "code",
                    LearningEvent.item_id == problem_id)
            .all())


def _gave_up(events: list[LearningEvent]) -> bool:
    return any(e.source_ref == GIVE_UP_REF for e in events)


def record_give_up(db: Session, user_id: int, problem: Problem, language: str) -> None:
    if _gave_up(_code_events(db, user_id, problem.id)):
        return
    ingest(db, EventInput(
        user_id=user_id, kind="code", score=0.0, raw_topic=problem.topic,
        item_id=problem.id,
        hint_level=highest_level(db, user_id, problem.id, sources=("practice",)),
        source_ref=GIVE_UP_REF, language=language,
    ))


def _reference(problem: Problem, language: Language,
               status: ReferenceStatus = ReferenceStatus.VALIDATED) -> ProblemReference | None:
    return next((r for r in problem.references
                 if r.language is language and r.status is status), None)


def _default_porter(*, language: Language, statement: str, reference: str,
                    previous: str | None, failure: str | None) -> str:
    name, rules = _PORT_TARGETS[language]
    prompt = SOLUTION_PORT_PROMPT.format(language_name=name, language_rules=rules,
                                         statement=statement, reference=reference)
    if previous:
        prompt += SOLUTION_PORT_RETRY.format(failure=failure, previous=previous)
    result = llm_gateway.invoke("solution_port", prompt, schema=PortedSolution).value
    return result.code if result else ""


def _failure(judgement) -> str:
    if not judgement.compiled:
        return f"it did not compile:\n{(judgement.compile_output or '')[:800]}"
    return (f"it passed {judgement.split.passed} of {judgement.split.total} tests "
            f"(status {judgement.status})")


def _port(db: Session, problem: Problem, language: Language, reference: str,
          porter, provider) -> str | None:
    """None means "show the Python reference instead". Only a port that ran and failed is
    cached as failed; an outage says nothing about the problem and is retried next time."""
    previous = failure = None
    for attempt in range(1, PORT_ATTEMPTS + 1):
        try:
            code = porter(language=language, statement=problem.statement, reference=reference,
                          previous=previous, failure=failure)
            if not code.strip():
                raise LLMUnavailable("empty port")
            judgement = judge(language, code, problem.test_cases, provider=provider)
        except (LLMUnavailable, ExecutorUnavailable):
            logger.warning("solution port for problem %s (%s) unavailable",
                           problem.id, language.value, exc_info=True)
            return None
        if judgement.all_passed:
            db.add(ProblemReference(problem_id=problem.id, language=language, source=code,
                                    status=ReferenceStatus.VALIDATED, attempts=attempt))
            db.commit()
            return code
        previous, failure = code, _failure(judgement)
    db.add(ProblemReference(problem_id=problem.id, language=language, source=previous or "",
                            status=ReferenceStatus.FAILED, attempts=PORT_ATTEMPTS))
    db.commit()
    return None


def solution_for(db: Session, problem: Problem, language: str, *,
                 porter=None, provider=None) -> Solution:
    python = _reference(problem, Language.PYTHON)
    fallback = Solution(Language.PYTHON.value, python.source if python else "")
    target = Language(language)
    cached = _reference(problem, target)
    if cached is not None:
        return Solution(target.value, cached.source)
    if (target not in _PORT_TARGETS or python is None or not problem.test_cases
            or _reference(problem, target, ReferenceStatus.FAILED) is not None):
        return fallback
    code = _port(db, problem, target, python.source, porter or _default_porter, provider)
    return Solution(target.value, code) if code else fallback


def reveal(db: Session, user_id: int, problem: Problem, language: str, *, give_up: bool,
           porter=None, provider=None) -> Solution:
    if give_up:
        record_give_up(db, user_id, problem, language)
    else:
        events = _code_events(db, user_id, problem.id)
        if not (_gave_up(events) or any(is_solved(e.score, e.hint_level_used) for e in events)):
            raise SolutionLocked()
    return solution_for(db, problem, language, porter=porter, provider=provider)
