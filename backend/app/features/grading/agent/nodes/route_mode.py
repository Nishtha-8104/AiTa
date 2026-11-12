"""First node: loads the submission and picks the mode. Verified when there is a problem to
test and the language can run; review otherwise."""

from app.core.exceptions import SubmissionNotFound
from app.core.languages import EXECUTABLE_LANGUAGES
from app.features.accounts.models import User
from app.features.grading.agent.state import EvalState
from app.features.grading.models import CodeSubmission
from app.features.problems.models import Problem, ProblemSource
from app.features.problems.service import get_or_create_problem


def route_mode(state: EvalState) -> EvalState:
    submission = (
        state.db.query(CodeSubmission)
        .filter(
            CodeSubmission.id == state.submission_id,
            CodeSubmission.user_id == state.user_id,
        )
        .first()
    )
    if submission is None:
        raise SubmissionNotFound(f"submission {state.submission_id} not found")

    state.language = submission.language
    state.code = submission.code

    user = state.db.query(User).filter(User.id == state.user_id).first()
    if user is not None and user.skill_level is not None:
        state.skill_level = getattr(user.skill_level, "value", str(user.skill_level))

    if submission.language not in EXECUTABLE_LANGUAGES:
        state.mode = "review"
        state.unverified_reason = "language_not_executable"
        state.log(f"Review mode: {submission.language.value} is not executable.")
        return state

    # A bank problem is bound by id, so it keeps its cached test cases instead of
    # being re-fingerprinted from text the student may have edited.
    picked = (
        state.db.query(Problem).filter(Problem.id == submission.problem_id).first()
        if submission.problem_id else None
    )
    if picked is not None:
        state.problem_id = picked.id
        state.problem_statement = picked.statement
        state.mode = "verified"
        state.log(
            f"Verified mode: bank problem {picked.id}, "
            f"{len(picked.test_cases)} cached cases."
        )
        return state

    if not (submission.problem_context or "").strip():
        state.mode = "review"
        state.unverified_reason = "no_problem_statement"
        state.log("Review mode: no problem statement supplied.")
        return state

    problem, created = get_or_create_problem(
        state.db,
        submission.problem_context,
        source=ProblemSource.STUDENT,
        created_by_user_id=state.user_id,
    )
    if submission.problem_id != problem.id:
        submission.problem_id = problem.id
        state.db.commit()

    state.problem_id = problem.id
    state.problem_statement = problem.statement
    state.mode = "verified"
    state.log(
        f"Verified mode: problem {problem.id} "
        f"({'new' if created else 'existing'}), {len(problem.test_cases)} cached cases."
    )
    return state
