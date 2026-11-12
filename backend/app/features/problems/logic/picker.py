"""Choosing a curated problem out of the bank, before anything is generated."""

from collections.abc import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.topics import normalise_topic
from app.features.problems.logic.listing import CURATED_SOURCES
from app.features.problems.models import Difficulty, Problem

# The UI offers four difficulty buttons, but the bank and the Difficulty column stop at "hard".
# A request for "expert" is a request for the hardest thing that exists, not a typo.
_ALIASES = {"expert": Difficulty.HARD}


def coerce_difficulty(value) -> Difficulty | None:
    """The API speaks strings and the column is an enum. Unknown values come back as
    None rather than raising: a student typing nonsense is not a server error."""
    if value is None or isinstance(value, Difficulty):
        return value
    try:
        return Difficulty(str(value).strip().lower())
    except ValueError:
        return None


def requested_difficulty(value) -> Difficulty | None:
    """`coerce_difficulty`, plus the levels the UI can ask for that the bank does not
    model. Still None for anything genuinely unknown."""
    if isinstance(value, str):
        aliased = _ALIASES.get(value.strip().lower())
        if aliased is not None:
            return aliased
    return coerce_difficulty(value)


def resolve_difficulty(value):
    """What to search the bank with, given whatever the UI asked for.

    A level the UI can ask for but the bank does not model becomes the level it will
    really be served at; anything unrecognised is passed through untouched, so it
    matches no problem rather than quietly widening the search.
    """
    level = requested_difficulty(value)
    return level if level is not None else value


def pick_problem(
    db: Session,
    topic: str | None = None,
    difficulty: str | Difficulty | None = None,
    exclude_ids: Iterable[int] = (),
) -> Problem | None:
    """The lowest-numbered curated problem matching the filters, or None.

    Matching is exact, not fuzzy. The bank holds thirteen topics; a similarity search
    over that would mostly be a way to return the wrong topic confidently.
    """
    query = db.query(Problem).filter(
        Problem.source.in_(CURATED_SOURCES),
        # An ungradeable problem is not servable, whatever else matches.
        Problem.test_cases.any(),
    )

    if topic:
        wanted = {topic.strip().lower()}
        canonical = normalise_topic(topic)
        if canonical:
            wanted.add(canonical)
        query = query.filter(func.lower(Problem.topic).in_(wanted))

    if difficulty is not None:
        level = coerce_difficulty(difficulty)
        if level is None:
            # Widening to every difficulty would answer a question nobody asked.
            return None
        query = query.filter(Problem.difficulty == level)

    excluded = {int(pid) for pid in exclude_ids}
    if excluded:
        query = query.filter(Problem.id.notin_(excluded))

    return query.order_by(Problem.id).first()
