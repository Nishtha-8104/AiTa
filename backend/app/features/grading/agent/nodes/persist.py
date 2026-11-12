"""Saves the evaluation, its per-case execution results and a history entry."""

import time

from app.core.text import ellipsize
from app.features.grading.agent.state import EvalState
from app.features.grading.models import CodeEvaluation, EvalHistoryEntry
from app.features.problems.models import ExecRole, ExecutionResult


def persist(state: EvalState, *, started_ms: int | None = None) -> EvalState:
    report = state.report
    if report is None:
        return state

    attempt = (
        state.db.query(CodeEvaluation)
        .filter(CodeEvaluation.submission_id == state.submission_id)
        .count()
    ) + 1

    latency_ms = int(time.time() * 1000) - started_ms if started_ms else 0

    evaluation = CodeEvaluation(
        submission_id=state.submission_id,
        user_id=state.user_id,
        overall_score=report.scores.overall,
        correctness_score=report.scores.correctness,
        complexity_score=report.scores.complexity,
        efficiency_score=report.scores.efficiency,
        style_score=report.scores.style,
        mode=report.mode,
        verification_status=report.verification_status,
        unverified_reason=report.unverified_reason,
        tests_total=report.tests_total,
        tests_passed=report.tests_passed,
        status="done",
        attempt_number=attempt,
        issues=[i.model_dump() for i in report.issues],
        time_complexity=ellipsize(report.metrics.time_complexity, 120),
        space_complexity=ellipsize(report.metrics.space_complexity, 120),
        cyclomatic_complexity=report.metrics.cyclomatic_complexity,
        lines_of_code=report.metrics.lines_of_code,
        comment_ratio=report.metrics.comment_ratio,
        summary=report.summary,
        detailed_feedback=report.detailed_feedback,
        key_improvements=report.key_improvements,
        learning_points=report.learning_points,
        best_practices_used=report.best_practices_used,
        anti_patterns=report.anti_patterns,
        suggested_resources=report.suggested_resources,
        agent_steps=report.agent_steps,
        tokens_used=report.tokens_used,
        latency_ms=latency_ms,
        model_used=ellipsize(report.model_used, 100),
        static_tool_used="lizard",
    )
    state.db.add(evaluation)
    state.db.flush()

    run = state.outcomes[0] if state.outcomes else None

    if state.split is not None and state.split.total:
        # One merged execution, but the record is per sub-case so a failure can be
        # traced to a test case. Timing belongs to the whole run, so it is carried on
        # the evaluation's latency rather than attributed to any single sub-case.
        for index, result in enumerate(state.split.results):
            test_case_id = (
                state.test_cases[index].id if index < len(state.test_cases) else None
            )
            state.db.add(ExecutionResult(
                evaluation_id=evaluation.id,
                test_case_id=test_case_id,
                role=ExecRole.STUDENT,
                status="ok" if result.passed else "wrong_answer",
                stdout=result.actual_stdout,
                stderr="",
                time_ms=0,
                memory_kb=None,
            ))
    elif run is not None:
        state.db.add(ExecutionResult(
            evaluation_id=evaluation.id,
            test_case_id=None,
            role=ExecRole.STUDENT,
            status=run.status.value,
            stdout=run.actual_stdout,
            stderr=run.stderr,
            time_ms=run.time_ms,
            memory_kb=run.memory_kb,
        ))

    state.db.add(EvalHistoryEntry(
        user_id=state.user_id,
        submission_id=state.submission_id,
        evaluation_id=evaluation.id,
        overall_score=report.scores.overall,
        language=state.language,
        eval_number=attempt,
    ))
    state.db.commit()

    report.evaluation_id = evaluation.id
    report.created_at = evaluation.created_at
    report.latency_ms = latency_ms
    return state
