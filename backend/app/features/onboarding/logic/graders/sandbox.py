"""Shared pieces of the Sandbox-backed graders: run an answer against an item's tests and
put the outcome in one line."""

from types import SimpleNamespace

from app.core.exceptions import ExecutorUnavailable
from app.features.grading.logic.execution.base import ExecStatus, ExecutionProvider
from app.features.grading.logic.execution.judge import Judgement, judge
from app.features.onboarding.logic.bank import language_of
from app.features.onboarding.logic.types import Grade
from app.features.onboarding.models import DiagnosticItem

GRADED_BY = "sandbox"
SKIPPED_WHY = "The code runner is unavailable right now, so this one was not scored."
STATUS_WHY = {
    ExecStatus.TIMEOUT.value: "Your code timed out; it probably loops forever.",
    ExecStatus.RUNTIME_ERROR.value: "Your code crashed while running.",
    ExecStatus.MEMORY_EXCEEDED.value: "Your code used too much memory.",
    ExecStatus.INTERNAL_ERROR.value: "Your code could not be run.",
}


def is_blank(value) -> bool:
    return not isinstance(value, str) or not value.strip()


def run_tests(item: DiagnosticItem, code: str,
              provider: ExecutionProvider | None) -> Judgement | None:
    cases = [SimpleNamespace(stdin=t["stdin"], expected_stdout=t["expected_stdout"])
             for t in item.key["tests"]]
    try:
        return judge(language_of(item.language), code, cases, provider)
    except ExecutorUnavailable:
        return None


def outcome_line(judgement: Judgement) -> str:
    if not judgement.compiled:
        return "Your code did not compile."
    if judgement.status in STATUS_WHY:
        return STATUS_WHY[judgement.status]
    split = judgement.split
    if judgement.all_passed:
        return f"All {split.total} tests passed."
    return f"{split.passed} of {split.total} tests passed."


COMPILE_OUTPUT_CHARS = 1500


def compiler_note(judgement: Judgement) -> dict:
    if judgement.compiled or not judgement.compile_output:
        return {}
    return {"compile_output": judgement.compile_output.strip()[:COMPILE_OUTPUT_CHARS]}


def skipped(expected, **extra) -> Grade:
    return Grade(None, "skipped",
                 {"correct": None, "expected": expected, **extra, "why": SKIPPED_WHY})
