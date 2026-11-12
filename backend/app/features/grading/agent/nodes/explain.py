"""The LLM explanation of a run, from the code, the first failing case and the static issues,
pitched at the student's level and style. Scores never depend on it."""

from app.core import llm_gateway
from app.core.exceptions import LLMUnavailable
from app.core.llm import invoke_with_retry
from app.features.grading.agent.prompts import (
    ALIGNMENT_NOTE, CRASH_BLOCK, EXPLANATION_PROMPT, FAILURE_BLOCK, NO_FAILURE_BLOCK,
)
from app.features.grading.agent.schemas import Explanation
from app.features.grading.agent.state import EvalState
from app.features.learner_model.logic.personalisation import style_line

_CRASH_VERDICTS = ("Runtime error", "Time limit exceeded", "Memory limit exceeded")


def _summarise_failures(split) -> str:
    lines = []
    for r in split.results:
        if r.passed:
            continue
        lines.append(
            f"  #{r.ordinal} ({r.kind}) input={r.stdin.strip()!r} "
            f"expected={r.expected_stdout!r} got={r.actual_stdout!r}"
            + (f" — checks {r.rationale}" if r.rationale else "")
        )
    return "\n".join(lines) or "  (none)"


def _failure_block(state: EvalState) -> str:
    split = state.split
    if split is None or split.total == 0:
        return NO_FAILURE_BLOCK

    if state.verdict in _CRASH_VERDICTS:
        stderr = state.outcomes[0].stderr if state.outcomes else ""
        return CRASH_BLOCK.format(
            verdict=state.verdict,
            total_count=split.total,
            stderr_block=f"ERROR OUTPUT:\n{stderr[:800]}\n" if stderr else "",
        )

    failing = split.first_failing
    if failing is None:
        return NO_FAILURE_BLOCK

    note = ""
    if split.missing_output:
        note = ALIGNMENT_NOTE.format(problem="fewer lines than expected")
    elif split.extra_output:
        note = ALIGNMENT_NOTE.format(problem="more lines than expected")

    return FAILURE_BLOCK.format(
        verdict=state.verdict or "Wrong answer",
        failed_count=split.total - split.passed,
        total_count=split.total,
        failed_summary=_summarise_failures(split),
        stdin=repr(failing.stdin),
        expected=repr(failing.expected_stdout),
        actual=repr(failing.actual_stdout),
        rationale=failing.rationale or "boundary behaviour",
        alignment_note=note,
    )


def explain(state: EvalState, *, runnable=None) -> EvalState:
    issues = "\n".join(
        f"- [{i.severity}] {i.category}: {i.message}" for i in state.issues[:10]
    ) or "No static issues found."

    prompt = EXPLANATION_PROMPT.format(
        skill_level=state.skill_level,
        style=style_line(state.db, state.user_id) or "not recorded",
        language=state.language.value,
        code=state.code,
        tests_passed=state.tests_passed,
        tests_total=state.tests_total,
        failure_block=_failure_block(state),
        issues=issues,
    )

    try:
        runnable = runnable or state.explain_runnable
        if runnable is not None:
            explanation, usage = invoke_with_retry(runnable, prompt)
            tokens, model = usage.tokens, usage.model
        else:
            result = llm_gateway.invoke("explain", prompt, schema=Explanation,
                                        user_id=state.user_id)
            explanation, tokens, model = result.value, result.tokens, result.model
    except LLMUnavailable as exc:
        state.log(f"Explanation unavailable: {exc.detail}. Scores still returned.")
        return state

    state.explanation = explanation
    state.tokens_used += tokens
    state.model_used = model
    state.log(f"Explanation generated ({tokens} tokens).")
    return state
