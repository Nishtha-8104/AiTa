"""Find-bug: half for the right line, half for a fix that passes the tests."""

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
    bug_line = item.key["bug_line"]
    fixed_code = item.key["fixed_code"]
    line_ok = answer.get("line") == bug_line
    fix_code = answer.get("fix_code")

    fix_ok, fix_why, note = False, "No fix was submitted.", {}
    if not is_blank(fix_code):
        judgement = run_tests(item, fix_code, provider)
        if judgement is None:
            return skipped(fixed_code, bug_line=bug_line)
        fix_ok, fix_why, note = judgement.all_passed, outcome_line(judgement), compiler_note(judgement)

    score = 0.5 * line_ok + 0.5 * fix_ok
    line_why = "Right line." if line_ok else f"The bug is on line {bug_line}."
    return Grade(score, GRADED_BY, {"correct": score >= 0.5, "expected": fixed_code,
                                    "bug_line": bug_line, "why": f"{line_why} {fix_why}",
                                    **note})
