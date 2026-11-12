"""The editor's Run button: the student's code against the shown example only.

No scoring, no persistence, no LLM. Hidden cases are never executed here, so their
data cannot leak through a Run response.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import LanguageNotExecutable, ProblemNotFound
from app.core.languages import EXECUTABLE_LANGUAGES
from app.features.grading.agent.multi_test import all_failed, merge_cases, split_actual, verdict_for
from app.features.grading.logic.execution.base import ExecStatus, ExecutionProvider
from app.features.grading.logic.execution.run_code import run_code
from app.features.grading.models import Language
from app.features.grading.schemas import RunCase, RunCodeResult
from app.features.problems.logic.listing import sample_case
from app.features.problems.models import Problem


def run_sample(
    db: Session,
    problem_id: int,
    language: Language,
    code: str,
    provider: ExecutionProvider | None = None,
) -> RunCodeResult:
    problem = db.get(Problem, problem_id)
    case = sample_case(problem) if problem is not None else None
    if case is None:
        raise ProblemNotFound(f"problem {problem_id} has no runnable example")
    if language not in EXECUTABLE_LANGUAGES:
        raise LanguageNotExecutable(f"{language.value} cannot be run")

    cases = [case]
    stdin, expected = merge_cases(cases)
    report = run_code(language, code, [(stdin, expected)], provider=provider)
    outcome = report.outcomes[0]

    ran = report.compiled and outcome.status in (ExecStatus.OK, ExecStatus.WRONG_ANSWER)
    status = outcome.status.value if report.compiled else ExecStatus.COMPILE_ERROR.value
    split = split_actual(outcome.actual_stdout, cases) if ran else all_failed(cases)

    return RunCodeResult(
        verdict=verdict_for(status, split),
        status=status,
        compile_output=report.compile_output,
        stderr=outcome.stderr,
        passed=split.passed,
        total=split.total,
        cases=[
            RunCase(
                input=stdin,
                expected=result.expected_stdout,
                actual=result.actual_stdout if ran else outcome.actual_stdout,
                passed=result.passed,
            )
            for result in split.results
        ],
    )
