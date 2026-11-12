from app.features.feedback.agent.state import FeedbackState
from app.features.feedback.logic.patterns import analyse_patterns as _analyse


def analyse_patterns(state: FeedbackState) -> FeedbackState:
    state.log("Analysing error patterns and concept gaps.")
    state.patterns = _analyse(state.eval_ctx, state.activity_ctx)
    state.log(f"{len(state.patterns['errors'])} errors, "
              f"{len(state.patterns['weak_concepts'])} weak concepts found.")
    return state
