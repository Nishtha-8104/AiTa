"""Makes sure the problem has trusted test cases: cached ones, or LLM-generated ones checked
against a reference solution. No trusted tests means review mode."""

from app.core.exceptions import LLMUnavailable
from app.features.grading.agent.state import EvalState
from app.features.problems.logic.test_generation.generate_tests import generate_tests
from app.features.problems.models import Problem


def ensure_tests(state: EvalState) -> EvalState:
    if state.mode != "verified":
        return state

    problem = state.db.query(Problem).filter(Problem.id == state.problem_id).first()
    if problem is None:
        state.mode = "review"
        state.unverified_reason = "no_problem_statement"
        return state

    try:
        suite = generate_tests(state.db, problem, generator=state.generator,
                               provider=state.provider)
    except LLMUnavailable:
        state.mode = "review"
        state.unverified_reason = "test_generation_failed"
        state.log("Test generation unavailable; falling back to review mode.")
        return state

    if suite.unverified_reason:
        state.mode = "review"
        state.unverified_reason = suite.unverified_reason
        state.log(f"Cannot verify: {suite.unverified_reason}.")
        return state

    state.test_cases = list(problem.test_cases)
    state.reference_solution = suite.reference_solution
    state.log(
        f"{len(state.test_cases)} test cases ready "
        f"({suite.dropped} dropped by cross-check, attempt {suite.attempts})."
        if suite.attempts
        else f"{len(state.test_cases)} cached test cases loaded."
    )
    return state
