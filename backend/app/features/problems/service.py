from sqlalchemy.orm import Session

from app.core.text import statement_hash
from app.features.problems.models import Problem, TestCase


def find_problem_by_statement(db: Session, statement: str) -> Problem | None:
    return (
        db.query(Problem)
        .filter(Problem.statement_hash == statement_hash(statement))
        .first()
    )


def get_or_create_problem(
    db: Session,
    statement: str,
    *,
    source,
    topic: str | None = None,
    difficulty=None,
    constraints: str | None = None,
    external_id: str | None = None,
    created_by_user_id: int | None = None,
    title: str | None = None,
) -> tuple[Problem, bool]:
    existing = find_problem_by_statement(db, statement)
    if existing is not None:
        return existing, False

    problem = Problem(
        source=source,
        statement=statement,
        statement_hash=statement_hash(statement),
        topic=topic,
        difficulty=difficulty,
        constraints=constraints,
        external_id=external_id,
        created_by_user_id=created_by_user_id,
        title=title,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem, True


def fill_title(db: Session, external_id: str, title: str) -> bool:
    """Sets the title on the problem with this external_id; True when it changed."""
    problem = db.query(Problem).filter(Problem.external_id == external_id).first()
    if problem is None or problem.title == title:
        return False
    problem.title = title
    db.commit()
    return True


def has_test_cases(db: Session, problem_id: int) -> bool:
    return (
        db.query(TestCase).filter(TestCase.problem_id == problem_id).first() is not None
    )
