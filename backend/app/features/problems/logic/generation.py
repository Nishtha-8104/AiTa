"""Generating a problem the system can actually grade.

A generated problem is a real row with real, cross-checked test cases before the
student ever sees it. The alternative — handing over a plausible-looking statement
nothing can mark — is what this replaces.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import llm_gateway
from app.core.exceptions import ExecutorUnavailable, LLMUnavailable
from app.core.llm import invoke_with_retry
from app.core.topics import normalise_topic
from app.features.problems.logic.picker import coerce_difficulty
from app.features.problems.logic.schemas import MAX_HINTS, ProblemDraft
from app.features.problems.logic.test_generation.generate_tests import generate_tests
from app.features.problems.models import Difficulty, Problem, ProblemSource
from app.features.problems.service import get_or_create_problem

logger = logging.getLogger(__name__)

DEFAULT_DIFFICULTY = Difficulty.MEDIUM

GENERATION_PROMPT = """Write one original {difficulty} programming exercise about \
{topic}, for a beginner who is learning to program.

The exercise is solved by a program that reads from standard input and prints to
standard output. There is no function signature and no return value. Do not name a
programming language anywhere in the statement — the student chooses their own.

Write the statement so that it describes a single test case. The grader feeds the
student's program a count of test cases followed by that many input blocks, and the
statement must describe one such block: what it contains, and what the program
prints for it.

State the input format line by line, then the output format. Be exact about
whitespace and about the order of the values. A reader must be able to write a
correct program from the statement alone, without guessing.

Keep it self-contained: no images, no tables, no links, no references to any
website's version of the problem.
"""


@dataclass(frozen=True)
class GeneratedProblem:
    """The persisted row plus the parts of the draft the database has no column for."""

    problem: Problem
    title: str
    hints: list[str]
    ungradeable_reason: str | None


def _draft(topic: str, difficulty: str, runnable) -> ProblemDraft:
    prompt = GENERATION_PROMPT.format(topic=topic, difficulty=difficulty)
    if runnable is None:
        draft = llm_gateway.invoke("problem_gen", prompt, schema=ProblemDraft).value
    else:
        draft, _ = invoke_with_retry(runnable, prompt)
    if draft is None:
        # Structured output that failed to parse is the same situation as no call at
        # all, and the caller must hear about it the same way.
        raise LLMUnavailable("The model returned no usable problem.")
    return draft


def generate_problem(
    db: Session,
    topic: str,
    difficulty: str | None = None,
    *,
    runnable=None,
    generator=None,
    provider=None,
) -> GeneratedProblem:
    """Generate a problem, persist it, and give it test cases immediately."""
    # The row records the level actually generated at, never the one that was asked
    # for, so nothing downstream can label the problem as something it is not.
    level = coerce_difficulty(difficulty) or DEFAULT_DIFFICULTY
    draft = _draft(topic.strip(), level.value, runnable)

    constraints = [line.strip() for line in draft.constraints if line.strip()]
    problem, _ = get_or_create_problem(
        db,
        draft.statement,
        source=ProblemSource.GENERATED,
        topic=normalise_topic(topic) or topic.strip() or None,
        difficulty=level,
        constraints="\n".join(constraints) or None,
        title=draft.title.strip()[:120] or None,
    )

    # The row is worth keeping through either outage: the statement is sound, and a
    # later attempt reuses it through the statement hash instead of paying for it
    # again. Both arrive here rather than escaping, so the caller always hears why
    # the problem is not gradeable instead of the student reading infrastructure text.
    try:
        reason = generate_tests(
            db, problem, generator=generator, provider=provider
        ).unverified_reason
    except LLMUnavailable as exc:
        logger.warning("Test generation unavailable for problem %s: %s",
                       problem.id, exc.detail)
        reason = "tests_unavailable"
    except ExecutorUnavailable as exc:
        logger.warning("Executor unavailable for problem %s: %s",
                       problem.id, exc.detail)
        reason = "executor_unavailable"

    return GeneratedProblem(
        problem=problem,
        title=draft.title.strip(),
        # Capped here rather than trusted to the schema description: a model that
        # writes four hints writes a walkthrough, and the extra ones are the answer.
        hints=[hint.strip() for hint in draft.hints if hint.strip()][:MAX_HINTS],
        ungradeable_reason=reason,
    )
