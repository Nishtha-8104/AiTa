"""One grade function per code item kind, all with the same interface."""

from collections.abc import Callable

from app.features.grading.logic.execution.base import ExecutionProvider
from app.features.onboarding.logic.graders import fill_blank, find_bug, predict_output, write_code
from app.features.onboarding.logic.types import Grade
from app.features.onboarding.models import DiagnosticItem

GRADERS: dict[str, Callable[[DiagnosticItem, dict, ExecutionProvider | None], Grade]] = {
    "predict_output": predict_output.grade,
    "find_bug": find_bug.grade,
    "fill_blank": fill_blank.grade,
    "write_code": write_code.grade,
}
