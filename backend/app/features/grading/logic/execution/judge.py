"""Grades code against test cases the way submissions are graded: one run over all cases
merged into one stdin, then a per-case split."""

from dataclasses import dataclass

from app.features.grading.agent.multi_test import SplitReport, all_failed, merge_cases, split_actual
from app.features.grading.logic.execution.base import ExecStatus, ExecutionProvider
from app.features.grading.logic.execution.run_code import run_code
from app.features.grading.models import Language


@dataclass
class Judgement:
    compiled: bool
    status: str
    split: SplitReport
    stderr: str = ""
    compile_output: str | None = None

    @property
    def all_passed(self) -> bool:
        return self.compiled and self.split.total > 0 and self.split.passed == self.split.total


def judge(language: Language, code: str, test_cases,
          provider: ExecutionProvider | None = None) -> Judgement:
    """Run once over every case merged into one stdin, the way graded submissions run,
    and score each case. Raises ExecutorUnavailable when the sandbox is down."""
    cases = list(test_cases)
    stdin, expected = merge_cases(cases)
    report = run_code(language, code, [(stdin, expected)], provider=provider)
    outcome = report.outcomes[0]
    if not report.compiled:
        return Judgement(False, ExecStatus.COMPILE_ERROR.value, all_failed(cases),
                         compile_output=report.compile_output)
    if outcome.status not in (ExecStatus.OK, ExecStatus.WRONG_ANSWER):
        return Judgement(True, outcome.status.value, all_failed(cases), outcome.stderr)
    return Judgement(True, outcome.status.value, split_actual(outcome.actual_stdout, cases),
                     outcome.stderr)
