"""Predict-output: the student's text against the stored output, whitespace-tolerant."""

from app.core.text import normalize_output
from app.features.grading.logic.execution.base import ExecutionProvider
from app.features.onboarding.logic.graders.sandbox import is_blank
from app.features.onboarding.logic.types import Grade
from app.features.onboarding.models import DiagnosticItem


def grade(item: DiagnosticItem, answer: dict, provider: ExecutionProvider | None = None) -> Grade:
    expected = item.key["expected_output"]
    text = answer.get("text")
    if is_blank(text):
        score, why = 0.0, "No answer given. This is what the program prints."
    else:
        score = float(normalize_output(text) == normalize_output(expected))
        why = ("Your output matches what the program prints." if score
               else "The program prints this; compare it with yours line by line.")
    return Grade(score, "key", {"correct": score >= 0.5, "expected": expected, "why": why})
