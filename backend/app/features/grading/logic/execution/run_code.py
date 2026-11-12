"""Runs code over several stdins through the provider and marks each case passed or not by
comparing normalized output."""

from pydantic import BaseModel

from app.core.text import normalize_output
from app.features.grading.logic.execution.base import ExecLimits, ExecStatus, ExecutionProvider
from app.features.grading.logic.execution.registry import get_provider
from app.features.grading.models import Language


class CaseOutcome(BaseModel):
    stdin: str
    expected_stdout: str | None
    actual_stdout: str
    status: ExecStatus
    stderr: str = ""
    time_ms: int = 0
    memory_kb: int | None = None
    passed: bool


class RunReport(BaseModel):
    compiled: bool
    compile_output: str | None
    outcomes: list[CaseOutcome]
    passed: int
    total: int


def run_code(
    language: Language,
    source: str,
    cases: list[tuple[str, str | None]],
    provider: ExecutionProvider | None = None,
    limits: ExecLimits | None = None,
) -> RunReport:
    if not cases:
        return RunReport(compiled=True, compile_output=None, outcomes=[], passed=0, total=0)

    provider = provider or get_provider()
    limits = limits or ExecLimits()
    results = provider.run_batch(language, source, [stdin for stdin, _ in cases], limits)

    compiled = not any(r.status is ExecStatus.COMPILE_ERROR for r in results)
    compile_output = next((r.compile_output for r in results if r.compile_output), None)

    outcomes: list[CaseOutcome] = []
    for (stdin, expected), result in zip(cases, results):
        status = result.status
        if status is ExecStatus.OK and expected is not None:
            if normalize_output(result.stdout) != normalize_output(expected):
                status = ExecStatus.WRONG_ANSWER
        outcomes.append(CaseOutcome(
            stdin=stdin,
            expected_stdout=expected,
            actual_stdout=result.stdout,
            status=status,
            stderr=result.stderr,
            time_ms=result.time_ms,
            memory_kb=result.memory_kb,
            passed=status is ExecStatus.OK,
        ))

    return RunReport(
        compiled=compiled,
        compile_output=compile_output,
        outcomes=outcomes,
        passed=sum(1 for o in outcomes if o.passed),
        total=len(outcomes),
    )
