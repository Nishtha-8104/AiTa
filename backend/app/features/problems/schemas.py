from typing import List, Literal, Optional

from pydantic import BaseModel


class ProblemSummary(BaseModel):
    """One row in the problem picker."""
    id:          int
    title:       str
    statement:   str            # already carries the multi-test preamble
    source:      str
    topic:       Optional[str] = None
    difficulty:  Optional[str] = None
    constraints: Optional[str] = None
    test_count:  int = 0
    # One worked example, so a student can see the exact shape of stdin and stdout.
    sample_input:  Optional[str] = None
    sample_output: Optional[str] = None


class GenerateProblemRequest(BaseModel):
    topic: str
    difficulty: str = "medium"
    language: Literal["c", "cpp", "python"] = "python"
    exclude_titles: list = []   # titles already shown — don't repeat these
    exclude_ids: List[int] = []  # problem ids already shown this session


class GenerateProblemResponse(BaseModel):
    problem_id: int
    origin: Literal["bank", "generated"]
    title: str
    difficulty: str
    description: str
    examples: list = []
    constraints: list = []
    hints: list = []
    starter_code: str = ""


class SolutionRequest(BaseModel):
    language: Literal["c", "cpp", "python"]
    give_up: bool = False


class SolutionResponse(BaseModel):
    language: str
    code: str   # empty when the problem has no validated reference at all
