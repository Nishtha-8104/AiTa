"""Runs the student's code in the sandbox: every test case in one batched stdin, scored per
case. Without trusted tests, one smoke run in review mode."""

from app.core.exceptions import ExecutorUnavailable
from app.features.grading.agent.multi_test import (
    all_failed, merge_cases, split_actual, verdict_for,
)
from app.features.grading.agent.state import EvalState
from app.features.grading.logic.execution.base import ExecStatus
from app.features.grading.logic.execution.run_code import run_code


def _review_mode(state: EvalState) -> EvalState:
    """No problem statement, or a language we cannot run. One smoke run with empty
    stdin, purely to find out whether the code compiles and starts."""
    try:
        report = run_code(state.language, state.code, [("", None)], provider=state.provider)
    except ExecutorUnavailable as exc:
        state.unverified_reason = "executor_unavailable"
        state.compiled = False
        state.halted = True
        state.log(f"Executor unavailable: {exc.detail}")
        return state

    state.compiled = report.compiled
    state.compile_output = report.compile_output
    state.outcomes = report.outcomes
    state.tests_passed = 0
    state.tests_total = 0

    if not report.compiled:
        state.verdict = "Compilation error"
        state.halted = True
        state.log("Compilation failed; stopping before any LLM call.")
        return state

    crashed = bool(report.outcomes) and not report.outcomes[0].passed
    state.verdict = "Ran, not verified"
    state.log("Ran once with empty stdin: "
              + ("crashed." if crashed else "compiled and ran successfully."))
    return state


def execute_student(state: EvalState) -> EvalState:
    """The student's program runs ONCE against every sub-case merged into one stdin,
    the way a competitive-programming judge feeds it. Scoring stays per sub-case: the
    single output stream is split back apart using each sub-case's expected length."""
    if state.mode != "verified":
        return _review_mode(state)

    cases = state.test_cases
    merged_stdin, merged_expected = merge_cases(cases)

    try:
        report = run_code(
            state.language, state.code,
            [(merged_stdin, merged_expected)],
            provider=state.provider,
        )
    except ExecutorUnavailable as exc:
        state.mode = "review"
        state.unverified_reason = "executor_unavailable"
        state.compiled = False
        state.halted = True
        state.log(f"Executor unavailable: {exc.detail}")
        return state

    state.compiled = report.compiled
    state.compile_output = report.compile_output
    state.outcomes = report.outcomes

    outcome = report.outcomes[0] if report.outcomes else None
    status = outcome.status.value if outcome else ExecStatus.INTERNAL_ERROR.value

    if not report.compiled:
        state.split = all_failed(cases)
        state.verdict = verdict_for("compile_error", state.split)
        state.tests_passed, state.tests_total = 0, len(cases)
        state.halted = True
        state.log("Compilation failed; stopping before any LLM call.")
        return state

    # A crash or timeout kills the whole batch — every sub-case after the failure
    # never ran, so none of them can be credited.
    if outcome is None or status not in (ExecStatus.OK.value, ExecStatus.WRONG_ANSWER.value):
        state.split = all_failed(cases, actual=outcome.actual_stdout if outcome else "")
        state.verdict = verdict_for(status, state.split)
        state.tests_passed, state.tests_total = 0, len(cases)
        state.verification_status = "verified"
        state.log(f"{state.verdict} — no sub-case could be credited.")
        return state

    split = split_actual(outcome.actual_stdout, cases)
    state.split = split
    state.verdict = verdict_for(status, split)
    state.tests_passed = split.passed
    state.tests_total = split.total
    state.verification_status = "verified"

    note = ""
    if split.extra_output:
        note = " (extra output printed)"
    elif split.missing_output:
        note = " (output ended early)"
    state.log(f"{state.verdict}: {split.passed}/{split.total} sub-cases passed{note}.")
    return state
