# Endpoints, under /api/v1/problems:
#   POST /generate                serve a bank problem, or generate a new one if none fits
#   POST /{problem_id}/solution   the model answer, once the student passed or gave up

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import LLMUnavailable
from app.features.accounts.models import User
from app.features.problems.logic import generation
from app.features.problems.logic.listing import to_summary
from app.features.problems.logic.picker import pick_problem, resolve_difficulty
from app.features.problems.logic.solution import SolutionLocked, reveal
from app.features.problems.models import Problem
from app.features.problems.schemas import (
    GenerateProblemRequest,
    GenerateProblemResponse,
    ProblemSummary,
    SolutionRequest,
    SolutionResponse,
)

router = APIRouter(prefix="/problems", tags=["Problems"])


# Every problem is graded through the same harness, so every skeleton does the same
# thing: read the test count, then solve one block at a time. Only the languages the
# sandbox can compile and run get one — anything else would be graded in review mode.
STARTER_CODE = {
    "python": """import sys


def solve():
    # Read this test case's input and print its answer.
    pass


for _ in range(int(sys.stdin.readline())):
    solve()
""",
    "cpp": """#include <bits/stdc++.h>
using namespace std;

void solve() {
    // Read this test case's input and print its answer.
}

int main() {
    int t;
    cin >> t;
    while (t--) solve();
    return 0;
}
""",
    "c": """#include <stdio.h>

void solve(void) {
    // Read this test case's input and print its answer.
}

int main(void) {
    int t;
    if (scanf("%d", &t) != 1) return 0;
    while (t--) solve();
    return 0;
}
""",
}

DEFAULT_STARTER_LANGUAGE = "python"


def starter_code_for(language: str | None) -> str:
    return STARTER_CODE.get(
        (language or "").strip().lower(), STARTER_CODE[DEFAULT_STARTER_LANGUAGE]
    )


def _to_response(
    summary: ProblemSummary,
    *,
    origin: str,
    language: str | None = None,
    title: str | None = None,
    hints: list | None = None,
) -> GenerateProblemResponse:
    examples = []
    if summary.sample_input is not None:
        examples.append({
            "input": summary.sample_input,
            "output": summary.sample_output,
            "explanation": "One worked example, in the exact shape your program is run with.",
        })
    return GenerateProblemResponse(
        problem_id=summary.id,
        origin=origin,
        # The difficulty the problem has, never the one that was asked for.
        difficulty=summary.difficulty or "",
        title=title or summary.title,
        description=summary.statement,
        examples=examples,
        constraints=[c.strip() for c in (summary.constraints or "").splitlines() if c.strip()],
        hints=hints or [],
        starter_code=starter_code_for(language),
    )


@router.post("/generate", response_model=GenerateProblemResponse)
def generate_problem(
    body: GenerateProblemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve a curated problem when the bank has one, otherwise generate a real one.

    Plain `def` on purpose: the generation path is synchronous and blocking, so
    FastAPI must run it in a worker thread rather than on the event loop.
    """
    # Resolved once, at the boundary, so the pick and the generation agree on it.
    difficulty = resolve_difficulty(body.difficulty)

    picked = pick_problem(
        db,
        topic=body.topic,
        difficulty=difficulty,
        exclude_ids=body.exclude_ids,
    )
    if picked is not None:
        return _to_response(to_summary(picked), origin="bank", language=body.language)

    try:
        result = generation.generate_problem(db, topic=body.topic,
                                             difficulty=difficulty)
    except LLMUnavailable:
        raise HTTPException(503, "A problem could not be generated right now. "
                                 "Please try again in a moment.")

    if result.ungradeable_reason:
        # The row survives for a later attempt, but an ungradeable problem is not
        # something to put in front of a student.
        raise HTTPException(503, "A problem was written but no test cases could be "
                                 "verified for it. Please try again.")

    return _to_response(to_summary(result.problem), origin="generated",
                        language=body.language, title=result.title, hints=result.hints)


@router.post("/{problem_id}/solution", response_model=SolutionResponse)
def problem_solution(
    problem_id: int,
    body: SolutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The model answer, once the student passed or gave up. `give_up` records the
    give-up first. Plain `def`: a first C or C++ reveal ports and runs it in the sandbox."""
    problem = db.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(404, "Problem not found.")
    try:
        solution = reveal(db, current_user.id, problem, body.language, give_up=body.give_up)
    except SolutionLocked:
        raise HTTPException(403, "The solution opens when you pass every test or give up.")
    return SolutionResponse(language=solution.language, code=solution.code)
