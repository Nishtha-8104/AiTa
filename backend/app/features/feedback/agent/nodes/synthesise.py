import json
import logging

from app.core import llm_gateway
from app.core.exceptions import LLMUnavailable
from app.core.llm import invoke_with_retry
from app.features.feedback.agent.prompts import (
    ACTIVITY_BLOCK,
    EVAL_BLOCK,
    LEARNING_BLOCK,
    PATTERN_BLOCK,
    PATTERN_ONLY_HEADLINE,
    PATTERN_ONLY_MOTIVATIONAL,
    SYSTEM_PROMPT,
    TONE_INSTRUCTIONS,
)
from app.features.feedback.agent.schemas import FeedbackNarrative
from app.features.feedback.agent.state import FeedbackState
from app.features.feedback.logic.activity import references_for
from app.features.grading.models import Language
from app.features.hints.logic import guardrail

logger = logging.getLogger(__name__)

# `steps` is persisted and shown to the student, so the failure step says only what a
# student can act on. The provider's own error text — which can carry the host, the
# model id and an API error body — goes to the log instead.
PATTERN_ONLY_STEP = ("Detailed feedback could not be generated. "
                     "Reporting the pattern analysis on its own.")
WITHHELD_STEP = ("Detailed feedback was withheld because it gave away the solution. "
                 "Reporting the pattern analysis on its own.")


def _score(value) -> str:
    return "n/a" if value is None else f"{value:.0f}"


def _fmt_correctness(eval_ctx: dict) -> str:
    score = eval_ctx.get("correctness")
    if score is None:
        return f"unverified ({eval_ctx.get('verification', 'unknown')})"
    return f"{score:.0f} ({eval_ctx.get('tests_passed', 0)}/{eval_ctx.get('tests_total', 0)} tests)"


def _system(state: FeedbackState) -> str:
    ctx = state.user_ctx
    return SYSTEM_PROMPT.format(
        username=ctx["username"],
        skill=ctx["skill"],
        languages=", ".join(ctx["languages"]) or "general",
        style=ctx.get("style") or "not recorded",
        weak_areas=", ".join(ctx["weak_areas"]) or "none yet",
        tone_instruction=TONE_INSTRUCTIONS[state.tone],
    )


def _context(state: FeedbackState) -> str:
    patterns = state.patterns
    parts = []
    if state.eval_ctx:
        e = state.eval_ctx
        parts.append(EVAL_BLOCK.format(
            overall=_score(e["overall"]),
            correctness=_fmt_correctness(e),
            complexity=_score(e["complexity"]),
            efficiency=_score(e["efficiency"]),
            issues=json.dumps(patterns["errors"]),
            learning_points=json.dumps(e["learning_points"][:5]),
            anti_patterns=json.dumps(e["anti_patterns"][:4]),
            summary=e["summary"],
        ))
        learning = e["learning"]
        case = learning["failing_case"]
        parts.append(LEARNING_BLOCK.format(
            topic=learning["topic_label"] or "unclassified",
            mastery="n/a" if learning["mastery"] is None else f"{learning['mastery']:.2f}",
            evidence=learning["evidence"],
            failing=(f"input {case['stdin']!r}, expected {case['expected']!r}, "
                     f"got {case['actual']!r}") if case else "none - every test passed",
            statuses=", ".join(learning["case_statuses"]) or "n/a",
            this_attempt=", ".join(learning["this_attempt_misconceptions"]) or "none",
            counts=json.dumps(learning["misconception_counts"]),
            hint_level=learning["hint_level"],
            recent=json.dumps(learning["recent_events"]),
        ))
    if state.activity_ctx:
        a = state.activity_ctx
        parts.append(ACTIVITY_BLOCK.format(
            count=len(a["items"]),
            items=json.dumps(a["items"]),
            topics=json.dumps(a["topics"]),
            hints=json.dumps({f"L{level}": n for level, n in a["hints"].items()}),
            mistakes=json.dumps(a["mistakes"]),
        ))
    parts.append(PATTERN_BLOCK.format(
        errors=json.dumps(patterns["errors"]),
        weak_concepts=json.dumps(patterns["weak_concepts"]),
        strengths=json.dumps(patterns["strengths"]),
    ))
    return "\n\n".join(parts)


def _from_patterns(patterns: dict) -> FeedbackNarrative:
    """The degraded narrative. It says outright that it is not the real analysis —
    the previous implementation returned this shape silently and the UI showed it
    as if a model had written it."""
    return FeedbackNarrative(
        headline=PATTERN_ONLY_HEADLINE,
        summary=(
            "This comes from automatic pattern analysis only, because detailed "
            "feedback could not be generated. Patterns found: "
            f"{', '.join(patterns['errors'][:2]) or 'none'}."
        ),
        strengths=patterns["strengths"],
        errors=patterns["errors"],
        misconceptions=[],
        action_items=[f"Review: {c}" for c in patterns["weak_concepts"][:3]],
        concept_map={c: 0.3 for c in patterns["weak_concepts"]},
        next_topics=patterns["weak_concepts"][:3],
        motivational=PATTERN_ONLY_MOTIVATIONAL,
    )


def _narrative_text(narrative: FeedbackNarrative) -> str:
    return "\n".join([narrative.headline, narrative.summary, narrative.motivational or "",
                      *narrative.strengths, *narrative.errors, *narrative.misconceptions,
                      *narrative.action_items, *narrative.next_topics,
                      *narrative.concept_map])


def _leaks(state: FeedbackState, narrative: FeedbackNarrative) -> str | None:
    """The per-problem guardrail every hint passes through when the report is built
    around one evaluation, and the no-code multi-item check across every recent item."""
    text = _narrative_text(narrative)
    if state.eval_ctx:
        learning = state.eval_ctx["learning"]
        try:
            language = Language(state.eval_ctx["language"])
        except ValueError:
            language = Language.PYTHON
        verdict = guardrail.check(
            text, 3, language, learning["test_cases"],
            references=learning["references"], student_code=state.eval_ctx["code"],
        )
        if verdict.blocked:
            return verdict.reason
    if state.activity_ctx:
        verdict = guardrail.check_multi_item(text, references_for(state.db, state.events))
        if verdict.blocked:
            return verdict.reason
    return None


def _fall_back(state: FeedbackState, step: str) -> FeedbackState:
    state.pattern_only = True
    state.narrative = _from_patterns(state.patterns)
    state.log(step)
    return state


def _narrate(state: FeedbackState) -> tuple[FeedbackNarrative | None, int]:
    payload = [("system", _system(state)), ("human", _context(state))]
    if state.synthesise_runnable is not None:
        narrative, usage = invoke_with_retry(state.synthesise_runnable, payload)
        return narrative, usage.tokens
    result = llm_gateway.invoke("feedback", payload, schema=FeedbackNarrative,
                                user_id=state.user_id)
    return result.value, result.tokens


def synthesise(state: FeedbackState) -> FeedbackState:
    state.log("Synthesising personalised feedback.")
    try:
        for attempt in range(2):
            narrative, tokens = _narrate(state)
            if narrative is None:
                # Structured output that failed to parse is the same situation as no
                # call at all, and must be labelled the same way.
                logger.warning("Feedback synthesis returned no parsed narrative for user %s",
                               state.user_id)
                return _fall_back(state, PATTERN_ONLY_STEP)
            state.tokens_used += tokens
            leak = _leaks(state, narrative)
            if leak is None:
                state.narrative = narrative
                state.log(f"Feedback synthesised ({state.tokens_used} tokens).")
                return state
            logger.warning("Feedback for user %s blocked by the guardrail: %s",
                           state.user_id, leak)
    except LLMUnavailable as exc:
        logger.warning("Feedback synthesis unavailable for user %s: %s",
                       state.user_id, exc.detail)
        return _fall_back(state, PATTERN_ONLY_STEP)
    return _fall_back(state, WITHHELD_STEP)
