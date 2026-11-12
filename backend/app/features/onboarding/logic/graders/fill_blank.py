"""Fill-blank: the student's text goes into the blank and the completed code must pass
every test."""

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
    expected = item.key["answer"]
    text = answer.get("text")
    if is_blank(text):
        return Grade(0.0, GRADED_BY, {"correct": False, "expected": expected,
                                      "why": "Nothing was filled in."})
    code = item.body["code_with_blank"].replace(item.body["blank_marker"], text, 1)
    judgement = run_tests(item, code, provider)
    if judgement is None:
        return skipped(expected)
    score = 1.0 if judgement.all_passed else 0.0
    return Grade(score, GRADED_BY, {"correct": score >= 0.5, "expected": expected,
                                    "why": outcome_line(judgement),
                                    **compiler_note(judgement)})
