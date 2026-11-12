"""EvalState, the state passed between graph nodes."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.features.grading.agent.schemas import EvalReport
from app.features.grading.agent.static_metrics import Issue, StaticMetrics
from app.features.grading.models import Language


class EvalState(BaseModel):
    """Internal pipeline state. Never returned across a boundary — it holds the
    reference solution and every expected output. `EvalReport` is what leaves."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: Any
    submission_id: int
    user_id: int

    # Injection points. Left None in production; tests supply fakes so the whole
    # graph runs with no Docker and no network.
    provider: Any = None
    generator: Any = None
    explain_runnable: Any = None
    # Chat shows a failing or unverified run as a bare result, so the LLM explanation
    # would be thrown away there.
    explain_failures: bool = True

    language: Optional[Language] = None
    code: str = ""
    problem_id: Optional[int] = None
    problem_statement: Optional[str] = None
    skill_level: str = "beginner"

    mode: str = "verified"
    verification_status: str = "unverified"
    unverified_reason: Optional[str] = None

    test_cases: list[Any] = []
    reference_solution: Optional[str] = None

    compiled: bool = True
    compile_output: Optional[str] = None
    outcomes: list[Any] = []
    split: Any = None
    verdict: Optional[str] = None
    tests_passed: int = 0
    tests_total: int = 0

    metrics: Optional[StaticMetrics] = None
    issues: list[Issue] = []

    explanation: Any = None
    tokens_used: int = 0
    model_used: Optional[str] = None

    steps: list[str] = []
    report: Optional[EvalReport] = None
    halted: bool = False

    def log(self, message: str) -> None:
        self.steps.append(message)
