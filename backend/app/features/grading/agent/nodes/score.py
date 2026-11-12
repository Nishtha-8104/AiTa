"""Builds the EvalReport: weighted scores, per-case pass/fail without expected outputs, the
one revealed failing case, issues and misconceptions."""

from app.core.topics import clean_misconceptions
from app.features.grading.agent import scoring
from app.features.grading.agent.schemas import (
    CaseReport, EvalReport, FailingCaseReport, IssueReport, QualityMetrics,
)
from app.features.grading.agent.state import EvalState
from app.features.grading.agent.static_metrics import StaticMetrics


def _case_reports(state: EvalState) -> list[CaseReport]:
    """Per-sub-case status only. Never the stdin or the expected output — a student
    who can read every expected output has been handed the answer key."""
    if state.split is None:
        return []
    return [
        CaseReport(
            ordinal=r.ordinal,
            kind=r.kind,
            status="ok" if r.passed else "wrong_answer",
            passed=r.passed,
            time_ms=0,
        )
        for r in state.split.results
    ]


def _failing_report(state: EvalState) -> FailingCaseReport | None:
    """The single exception to the rule above: the first failing sub-case is revealed,
    because a hint that cannot name the input teaches nothing."""
    if state.split is None:
        return None
    failing = state.split.first_failing
    if failing is None:
        return None
    return FailingCaseReport(
        ordinal=failing.ordinal,
        kind=failing.kind,
        status="wrong_answer",
        passed=False,
        time_ms=0,
        stdin=failing.stdin,
        expected_stdout=failing.expected_stdout,
        actual_stdout=failing.actual_stdout,
        stderr=state.outcomes[0].stderr if state.outcomes else "",
        rationale=failing.rationale,
    )


def score(state: EvalState) -> EvalState:
    metrics = state.metrics or StaticMetrics()
    explanation = state.explanation
    time_complexity = getattr(explanation, "time_complexity", None)
    verified = state.verification_status == "verified" and state.tests_total > 0

    scores = scoring.build_scores(
        tests_passed=state.tests_passed,
        tests_total=state.tests_total,
        metrics=metrics,
        issues=state.issues,
        time_complexity=time_complexity,
        verified=verified,
    )

    slowest = max((o.time_ms for o in state.outcomes), default=None)

    state.report = EvalReport(
        submission_id=state.submission_id,
        problem_id=state.problem_id,
        language=state.language,
        mode=state.mode,
        verification_status="verified" if verified else "unverified",
        unverified_reason=None if verified else state.unverified_reason,
        verdict=state.verdict,
        extra_output=bool(state.split and state.split.extra_output),
        missing_output=bool(state.split and state.split.missing_output),
        compiled=state.compiled,
        compile_output=state.compile_output,
        tests_passed=state.tests_passed,
        tests_total=state.tests_total,
        cases=_case_reports(state),
        first_failing_case=_failing_report(state),
        scores=scores,
        metrics=QualityMetrics(
            time_complexity=time_complexity,
            space_complexity=getattr(explanation, "space_complexity", None),
            cyclomatic_complexity=metrics.cyclomatic_complexity,
            max_function_length=metrics.max_function_length,
            max_parameter_count=metrics.max_parameter_count,
            lines_of_code=metrics.lines_of_code,
            comment_ratio=metrics.comment_ratio,
            slowest_case_ms=slowest,
        ),
        issues=[IssueReport(**i.model_dump()) for i in state.issues],
        summary=getattr(explanation, "summary", None),
        detailed_feedback=getattr(explanation, "detailed_feedback", None),
        key_improvements=getattr(explanation, "key_improvements", []) or [],
        learning_points=getattr(explanation, "learning_points", []) or [],
        best_practices_used=getattr(explanation, "best_practices_used", []) or [],
        anti_patterns=getattr(explanation, "anti_patterns", []) or [],
        suggested_resources=getattr(explanation, "suggested_resources", []) or [],
        misconceptions=(
            clean_misconceptions(getattr(explanation, "misconceptions", []))
            if state.tests_passed < state.tests_total else []
        ),
        agent_steps=list(state.steps),
        tokens_used=state.tokens_used,
        model_used=state.model_used,
    )
    return state
