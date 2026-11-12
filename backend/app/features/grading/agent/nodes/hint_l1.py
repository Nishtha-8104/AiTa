"""The level-1 hint, a template over the first failing case (no LLM), and the log that it
was shown."""

from app.features.grading.agent.schemas import HintReport
from app.features.grading.agent.state import EvalState
from app.features.hints.service import FailingCase, HintSource, l1_text, log_hint


def hint_l1(state: EvalState) -> EvalState:
    """The first rung of the ladder, from the failing case alone. No LLM."""
    report = state.report
    failing = report.first_failing_case if report else None
    if failing is None or report.verification_status != "verified":
        return state
    report.hint = HintReport(level=1, text=l1_text(FailingCase(
        stdin=failing.stdin,
        expected=failing.expected_stdout,
        actual=failing.actual_stdout,
        rationale=failing.rationale,
        status=failing.status,
    )))
    return state


def log_l1(state: EvalState, source: HintSource = "practice") -> EvalState:
    report = state.report
    if report is None or report.hint is None or report.evaluation_id is None:
        return state
    log_hint(state.db, user_id=state.user_id, problem_id=state.problem_id,
             evaluation_id=report.evaluation_id, level=1, source=source)
    return state
