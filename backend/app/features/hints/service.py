"""One hint ladder shared by Code Eval (L1, template) and Feedback (L2-L4, LLM).

Ladder position is measured in evaluation ids, not wall-clock time: a hint belongs to
the evaluation it was about, and a fully passing evaluation resets the ladder."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import String, and_, cast, func, literal, or_
from sqlalchemy.orm import Session

from app.core import llm_gateway
from app.core.exceptions import LLMUnavailable, PetError, ProblemNotFound
from app.core.llm import invoke_with_retry
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.hints.logic import guardrail
from app.features.hints.logic.prompts import (
    APPROACH_CODE_BLOCK,
    APPROACH_HAS_CODE,
    APPROACH_LEVEL_INSTRUCTIONS,
    APPROACH_NO_CODE,
    APPROACH_PROMPT,
    APPROACH_TEMPLATES,
    HINT_PROMPT,
    LEVEL_INSTRUCTIONS,
    TEMPLATES,
)
from app.features.hints.models import HintEvent
from app.features.learner_model.logic.personalisation import style_line
from app.features.learner_model.models import LearningEvent
from app.features.learner_model.service import top_misconceptions
from app.features.practice import service as lifecycle
from app.features.problems.models import (
    ExecRole,
    ExecutionResult,
    Problem,
    ReferenceStatus,
    TestCase,
)

logger = logging.getLogger(__name__)

MAX_LEVEL = 4
_CRASH_STATUSES = ("runtime_error", "timeout", "memory_exceeded")
HintSource = Literal["practice", "chat"]


class NoHintAvailable(PetError):
    status_code = 409


@dataclass
class FailingCase:
    stdin: str
    expected: str
    actual: str
    rationale: str | None = None
    status: str = "wrong_answer"


@dataclass
class Hint:
    level: int
    text: str
    source: str
    was_blocked: bool
    evaluation_id: int | None
    problem_id: int


def _evaluations(db: Session, user_id: int, problem_id: int):
    return (
        db.query(CodeEvaluation)
        .join(CodeSubmission, CodeSubmission.id == CodeEvaluation.submission_id)
        .filter(CodeEvaluation.user_id == user_id, CodeSubmission.problem_id == problem_id)
    )


def _passed(evaluation: CodeEvaluation) -> bool:
    return bool(evaluation.tests_total) and evaluation.tests_passed == evaluation.tests_total


def last_pass_id(db: Session, user_id: int, problem_id: int, before: int | None = None) -> int:
    """Only a Practice pass (one that reached Profiling) resets the ladder; a chat run
    of the same code must not wipe the hint discount."""
    emitted = db.query(LearningEvent.id).filter(
        LearningEvent.user_id == user_id,
        LearningEvent.source_ref == literal("evaluation:") + cast(CodeEvaluation.id, String),
    ).exists()
    query = _evaluations(db, user_id, problem_id).filter(
        CodeEvaluation.tests_total > 0,
        CodeEvaluation.tests_passed == CodeEvaluation.tests_total,
        emitted,
    )
    if before is not None:
        query = query.filter(CodeEvaluation.id < before)
    return query.with_entities(func.max(CodeEvaluation.id)).scalar() or 0


def highest_level(db: Session, user_id: int, problem_id: int, before: int | None = None,
                  sources: tuple[HintSource, ...] | None = None) -> int:
    """Highest hint level seen on this problem since the last full pass. With `before`,
    only hints about evaluations earlier than that one count; with `sources`, only hints
    from those sources."""
    query = db.query(func.max(HintEvent.level)).filter(
        HintEvent.user_id == user_id,
        HintEvent.problem_id == problem_id,
        HintEvent.evaluation_id > last_pass_id(db, user_id, problem_id, before),
    )
    if sources is not None:
        query = query.filter(HintEvent.source.in_(sources))
    if before is not None:
        query = query.filter(HintEvent.evaluation_id < before)
    return query.scalar() or 0


def next_level(db: Session, user_id: int, problem_id: int) -> int:
    """Practice ladder position. Chat hints never move this ladder or mastery; they
    still show in feedback via highest_level."""
    return min(MAX_LEVEL, highest_level(db, user_id, problem_id, sources=("practice",)) + 1)


def l1_text(case: FailingCase) -> str:
    if case.status in _CRASH_STATUSES:
        return (
            f"Your program stopped early ({case.status.replace('_', ' ')}) on this input:\n"
            f"{case.stdin.rstrip()}\n"
            "What does your code do with it just before it stops?"
        )
    checks = f" This case checks: {case.rationale.rstrip('.')}." if case.rationale else ""
    return (
        f"Your code fails on this input:\n{case.stdin.rstrip()}\n"
        f"Expected `{case.expected}`, but it printed `{case.actual}`.{checks} "
        "Trace your code by hand on it: what value does each variable hold at the end?"
    )


def log_hint(db: Session, *, user_id: int, problem_id: int, evaluation_id: int | None,
             level: int, was_blocked: bool = False,
             source: HintSource = "practice") -> HintEvent:
    event = HintEvent(user_id=user_id, problem_id=problem_id, evaluation_id=evaluation_id,
                      level=level, was_blocked=was_blocked, source=source)
    db.add(event)
    db.commit()
    return event


def leak_rate(db: Session) -> tuple[int, int]:
    """(blocked, total) over LLM-written hints: every L2+ hint, plus approach hints at
    any level (chat, no evaluation). L1 about an evaluation is a template and cannot leak,
    whichever surface logged it."""
    rows = (db.query(HintEvent.was_blocked)
            .filter(or_(HintEvent.level >= 2,
                        and_(HintEvent.source == "chat", HintEvent.evaluation_id.is_(None))))
            .all())
    return sum(1 for (blocked,) in rows if blocked), len(rows)


def reference_sources(problem: Problem | None) -> list[str]:
    """Validated references, for the guardrail's prose check only. Never returned."""
    if problem is None:
        return []
    return [r.source for r in problem.references if r.status is ReferenceStatus.VALIDATED]


def failing_case(db: Session, evaluation: CodeEvaluation) -> FailingCase | None:
    rows = (
        db.query(ExecutionResult)
        .filter(ExecutionResult.evaluation_id == evaluation.id,
                ExecutionResult.role == ExecRole.STUDENT)
        .order_by(ExecutionResult.id)
        .all()
    )
    for row in rows:
        if row.status == "ok":
            continue
        case = db.get(TestCase, row.test_case_id) if row.test_case_id else None
        return FailingCase(
            stdin=case.stdin if case else "",
            expected=case.expected_stdout if case else "",
            actual=row.stdout or "",
            rationale=case.rationale if case else None,
            status=row.status,
        )
    return None


def _llm_hint(prompt: str, template: str, runnable, user_id: int) -> str | None:
    if runnable is None:
        result = llm_gateway.invoke("hint", prompt, user_id=user_id, template=template)
        if result.status == "template":
            return None
        message = result.value
    else:
        message, _ = invoke_with_retry(runnable, prompt)
    return (getattr(message, "content", message) or "").strip()


def _guarded_hint(level, prompt, template, *, problem, language, student_code,
                  evaluation_id, user_id, runnable, provider, fix_check: bool = False) -> Hint:
    """fix_check: a hint about the student's code also goes past the LLM judge, which
    catches a fix told in plain words. Approach hints without code have no bug to give
    away."""
    tests = list(problem.test_cases) if problem else []
    references = reference_sources(problem)
    problem_id = problem.id if problem else None

    blocked = False
    try:
        for _ in range(2):
            text = _llm_hint(prompt, template, runnable, user_id)
            if text is None:
                break
            verdict = guardrail.check(text, level, language, tests, provider,
                                      references=references, student_code=student_code)
            if (text and not verdict.blocked and fix_check and guardrail.states_fix(
                    text, statement=problem.statement if problem else "",
                    language=language.value, code=student_code, user_id=user_id)):
                verdict = guardrail.GuardVerdict(True, "states_fix")
            if text and not verdict.blocked:
                return Hint(level, text, "llm", blocked, evaluation_id, problem_id)
            blocked = blocked or verdict.blocked
    except LLMUnavailable:
        pass
    return Hint(level, template, "template", blocked, evaluation_id, problem_id)


def _misconceptions(db: Session, user_id: int) -> str:
    seen = [tag for tag, _ in top_misconceptions(db, user_id)[:3]]
    return ", ".join(seen) or "none recorded"


def _style(db: Session, user_id: int) -> str:
    return style_line(db, user_id) or "not recorded"


def _clamp(level: int) -> int:
    return max(1, min(MAX_LEVEL, int(level)))


def request_hint(db: Session, user_id: int, problem_id: int, *, level: int | None = None,
                 source: HintSource = "practice", runnable=None, provider=None) -> Hint:
    evaluation = _evaluations(db, user_id, problem_id).order_by(CodeEvaluation.id.desc()).first()
    if evaluation is None:
        raise NoHintAvailable("Submit an attempt at this problem first.")
    if _passed(evaluation):
        raise NoHintAvailable("Your last attempt passed every test. No hint needed.")

    problem = db.get(Problem, problem_id)
    submission = db.get(CodeSubmission, evaluation.submission_id)
    case = failing_case(db, evaluation) or FailingCase(stdin="", expected="", actual="")
    level = next_level(db, user_id, problem_id) if level is None else _clamp(level)

    if level == 1:
        hint = Hint(1, l1_text(case), "template", False, evaluation.id, problem_id)
    else:
        hint = _ladder_hint(db, level, problem, submission, case, user_id, evaluation.id,
                            runnable, provider)

    event = log_hint(db, user_id=user_id, problem_id=problem_id, evaluation_id=evaluation.id,
                     level=hint.level, was_blocked=hint.was_blocked, source=source)
    try:
        lifecycle.attach_hint(db, event, datetime.now(timezone.utc))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("practice session attach failed for hint on problem %s", problem_id)
    return hint


def _ladder_hint(db, level, problem, submission, case, user_id, evaluation_id,
                 runnable, provider) -> Hint:
    prompt = HINT_PROMPT.format(
        level_instruction=LEVEL_INSTRUCTIONS[level],
        max_lines=guardrail.max_code_lines(level),
        statement=problem.statement if problem else "",
        language=submission.language.value,
        code=submission.code,
        stdin=case.stdin.rstrip() or "(empty)",
        expected=case.expected.rstrip() or "(nothing)",
        actual=case.actual.rstrip() or "(nothing)",
        misconceptions=_misconceptions(db, user_id),
        style=_style(db, user_id),
    )
    return _guarded_hint(level, prompt, TEMPLATES[level], problem=problem,
                         language=submission.language, student_code=submission.code,
                         evaluation_id=evaluation_id, user_id=user_id,
                         runnable=runnable, provider=provider, fix_check=True)


def approach_hint(db: Session, user_id: int, problem_id: int, *, level: int,
                  language: Language, has_code: bool = False, runnable=None,
                  provider=None) -> Hint:
    """A hint built from the problem statement, for a student with no code yet or with
    code that has no tests to run against (has_code: their latest submission is shown).
    Always logged as a chat hint, so it never moves the Practice ladder."""
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise ProblemNotFound(f"Problem {problem_id} not found.")
    code = ""
    if has_code:
        latest = (db.query(CodeSubmission.code)
                  .filter(CodeSubmission.user_id == user_id,
                          CodeSubmission.problem_id == problem_id)
                  .order_by(CodeSubmission.id.desc()).first())
        code = latest.code if latest else ""
    level = _clamp(level)
    prompt = APPROACH_PROMPT.format(
        situation=APPROACH_HAS_CODE if code else APPROACH_NO_CODE,
        code_block=APPROACH_CODE_BLOCK.format(language=language.value, code=code) if code else "",
        level_instruction=APPROACH_LEVEL_INSTRUCTIONS[level],
        max_lines=guardrail.max_code_lines(level),
        statement=problem.statement,
        language=language.value,
        misconceptions=_misconceptions(db, user_id),
        style=_style(db, user_id),
    )
    hint = _guarded_hint(level, prompt, APPROACH_TEMPLATES[level], problem=problem,
                         language=language, student_code=code, evaluation_id=None,
                         user_id=user_id, runnable=runnable, provider=provider,
                         fix_check=bool(code))
    log_hint(db, user_id=user_id, problem_id=problem_id, evaluation_id=None,
             level=hint.level, was_blocked=hint.was_blocked, source="chat")
    return hint
