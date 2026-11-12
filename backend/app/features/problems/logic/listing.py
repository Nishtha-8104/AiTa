"""The problem bank as the picker sees it."""

from sqlalchemy.orm import Session

from app.core.topics import TOPIC_LABELS
from app.features.grading.agent.multi_test import display_statement, merge_cases
from app.features.problems.models import Problem, ProblemSource, TestCaseKind
from app.features.problems.schemas import ProblemSummary

_PREFIXES = ("dsa-", "mbpp-")

CURATED_SOURCES = (ProblemSource.DSA, ProblemSource.MBPP)


def is_curated(problem: Problem) -> bool:
    return problem.source in CURATED_SOURCES


def _title(problem: Problem) -> str:
    """The stored title, else a readable one made up for rows seeded before titles.

    Slug ids like `dsa-two-sum` carry a real name; numeric ones like `mbpp-231`
    do not, and fall back to the topic.
    """
    if problem.title:
        return problem.title
    ext = problem.external_id or ""
    for prefix in _PREFIXES:
        if ext.startswith(prefix):
            rest = ext[len(prefix):]
            if not rest.isdigit():
                return rest.replace("-", " ").title()
    topic = TOPIC_LABELS.get(problem.topic) or (problem.topic or "problem").replace("_", " ").title()
    return f"{topic} #{problem.id}"


def sample_case(problem: Problem):
    """The one case the student is shown. Run executes exactly this, so nothing
    hidden ever reaches the client."""
    cases = sorted(problem.test_cases, key=lambda c: c.ordinal or 0)
    if not cases:
        return None
    return next((c for c in cases if c.kind is TestCaseKind.SAMPLE), cases[0])


def _sample(problem: Problem) -> tuple[str | None, str | None]:
    case = sample_case(problem)
    if case is None:
        return None, None
    # Shown as the program actually receives it: a test count, then the block.
    stdin, expected = merge_cases([case])
    return stdin, expected


def to_summary(problem: Problem) -> ProblemSummary:
    sample_input, sample_output = _sample(problem)
    return ProblemSummary(
        id=problem.id,
        title=_title(problem),
        statement=display_statement(problem.statement) or "",
        source=getattr(problem.source, "value", str(problem.source)),
        topic=problem.topic,
        difficulty=(getattr(problem.difficulty, "value", problem.difficulty)
                    if problem.difficulty else None),
        constraints=problem.constraints,
        test_count=len(problem.test_cases),
        sample_input=sample_input,
        sample_output=sample_output,
    )


def list_bank_problems(db: Session) -> list[ProblemSummary]:
    """Only curated problems that can actually be graded, i.e. that have test cases."""
    problems = (
        db.query(Problem)
        .filter(Problem.source.in_(CURATED_SOURCES))
        .order_by(Problem.id)
        .all()
    )
    return [to_summary(p) for p in problems if p.test_cases]


def get_bank_problem(db: Session, problem_id: int) -> ProblemSummary | None:
    problem = (
        db.query(Problem)
        .filter(Problem.id == problem_id, Problem.source.in_(CURATED_SOURCES))
        .first()
    )
    return to_summary(problem) if problem is not None else None
