"""Static analysis node: lines of code, cyclomatic complexity and style issues, measured
before anything runs."""

from app.features.grading.agent.state import EvalState
from app.features.grading.agent.static_metrics import find_issues, measure


def analyse(state: EvalState) -> EvalState:
    metrics = measure(state.code, state.language)
    state.metrics = metrics
    state.issues = find_issues(state.code, state.language, metrics)
    state.log(
        f"Static analysis: {metrics.lines_of_code} LOC, "
        f"CCN {metrics.cyclomatic_complexity}, {len(state.issues)} issues."
    )
    return state
