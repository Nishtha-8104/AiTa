import time

from app.core.text import ellipsize
from app.features.feedback.agent.state import FeedbackState
from app.features.feedback.models import FeedbackReport

HEADLINE_LIMIT = 300


def persist(state: FeedbackState) -> FeedbackState:
    narrative = state.narrative.model_dump()

    # The learner profile belongs to the Profiling Agent; this report is read-only
    # with respect to it. concept_map stays on the report as the model's own view.
    state.profile_updates = {}

    duration = int(time.time() * 1000) - state.started_ms
    state.log(f"Done in {duration}ms")

    report = FeedbackReport(
        user_id=state.user_id,
        evaluation_id=state.evaluation_id,
        feedback_type=state.feedback_type,
        tone=state.tone,
        # The only bounded column in the row: an over-long headline must not discard
        # the report.
        headline=ellipsize(narrative["headline"], HEADLINE_LIMIT),
        summary=narrative["summary"],
        strengths=narrative["strengths"],
        errors=narrative["errors"],
        misconceptions=narrative["misconceptions"],
        action_items=narrative["action_items"],
        concept_map=narrative["concept_map"],
        next_topics=narrative["next_topics"],
        motivational=narrative["motivational"],
        profile_updates=state.profile_updates,
        agent_steps=state.steps,
        tokens_used=state.tokens_used,
        latency_ms=duration,
        pattern_only=state.pattern_only,
    )
    state.db.add(report)
    state.db.commit()
    state.db.refresh(report)
    state.report = report
    return state
