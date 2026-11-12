"""Write-code: the share of tests the student's code passes."""

from app.features.grading.logic.execution.base import ExecutionProvider
from app.features.onboarding.logic.graders.sandbox import (
    GRADED_BY,
    compiler_note,
    is_blank,
    outcome_line,
    run_tests,
    skipped,
)
from app.features.onboarding.logic.types import Grade
from app.features.onboarding.models import DiagnosticItem


def grade(item: DiagnosticItem, answer: dict, provider: ExecutionProvider | None = None) -> Grade:
    expected = item.key["reference"]
    code = answer.get("code")
    if is_blank(code):
        return Grade(0.0, GRADED_BY, {"correct": False, "expected": expected,
                                      "why": "No code was submitted."})
    judgement = run_tests(item, code, provider)
    if judgement is None:
        return skipped(expected)
    split = judgement.split
    score = split.passed / split.total if split.total else 0.0
    return Grade(score, GRADED_BY, {"correct": score >= 0.5, "expected": expected,
                                    "passed": split.passed, "total": split.total,
                                    "why": outcome_line(judgement),
                                    **compiler_note(judgement)})
