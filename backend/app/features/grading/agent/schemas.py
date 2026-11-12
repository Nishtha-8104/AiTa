"""The agent's data shapes: the LLM's structured outputs (generated tests, explanation) and
the EvalReport that leaves the agent, which never carries the answer key."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.features.gamification.schemas import AwardOut
from app.features.grading.models import Language


class GeneratedCase(BaseModel):
    kind: Literal["normal", "edge"]
    stdin: str = Field(description="Exact bytes fed to stdin, with real newlines")
    expected_stdout: str = Field(description="Exact expected stdout, with real newlines")
    rationale: str = Field(description="Why this case matters, one short sentence")


class GeneratedTests(BaseModel):
    reference_solution: str = Field(
        description="A correct Python 3 program that reads stdin and prints the answer"
    )
    cases: list[GeneratedCase]


class Explanation(BaseModel):
    summary: str = Field(description="Two or three sentences, warm and specific")
    detailed_feedback: str = Field(description="Markdown feedback with ## headings")
    time_complexity: Optional[str] = Field(default=None, description="Big-O, e.g. O(n log n)")
    space_complexity: Optional[str] = Field(default=None, description="Big-O")
    key_improvements: list[str] = []
    learning_points: list[str] = []
    best_practices_used: list[str] = []
    anti_patterns: list[str] = []
    suggested_resources: list[str] = []
    # Free strings rather than a Literal: one unknown tag would otherwise fail the
    # whole structured parse and lose the explanation. Filtered after parsing.
    misconceptions: list[str] = Field(
        default=[],
        description="Tags from the MISCONCEPTION TAGS list that explain the failures; "
                    "empty when every test passed",
    )


class CaseReport(BaseModel):
    """One test case as the student is allowed to see it."""
    ordinal: int
    kind: str
    status: str
    passed: bool
    time_ms: int


class FailingCaseReport(CaseReport):
    """The first failing case only — the one case whose data is revealed."""
    stdin: str
    expected_stdout: str
    actual_stdout: str
    stderr: str = ""
    rationale: Optional[str] = None


class HintReport(BaseModel):
    level: int
    text: str


class ScoreBreakdown(BaseModel):
    overall: float = 0.0
    correctness: Optional[float] = None
    complexity: float = 0.0
    efficiency: float = 0.0
    style: float = 0.0


class QualityMetrics(BaseModel):
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    cyclomatic_complexity: Optional[int] = None
    max_function_length: Optional[int] = None
    max_parameter_count: Optional[int] = None
    lines_of_code: Optional[int] = None
    comment_ratio: Optional[float] = None
    slowest_case_ms: Optional[int] = None


class IssueReport(BaseModel):
    line: Optional[int] = None
    severity: str
    category: str
    message: str
    suggestion: str


class EvalReport(BaseModel):
    """The projection that crosses every boundary — HTTP response and, in Month 2,
    the chatbot tool return. It must never carry the reference solution, and never
    the expected output of any case beyond the first failing one."""

    evaluation_id: Optional[int] = None
    submission_id: Optional[int] = None
    problem_id: Optional[int] = None
    language: Optional[Language] = None

    mode: str = "verified"
    verification_status: str = "unverified"
    unverified_reason: Optional[str] = None

    verdict: Optional[str] = None
    extra_output: bool = False
    missing_output: bool = False

    compiled: bool = True
    compile_output: Optional[str] = None

    tests_passed: int = 0
    tests_total: int = 0
    cases: list[CaseReport] = []
    first_failing_case: Optional[FailingCaseReport] = None

    scores: ScoreBreakdown = ScoreBreakdown()
    metrics: QualityMetrics = QualityMetrics()
    issues: list[IssueReport] = []

    summary: Optional[str] = None
    detailed_feedback: Optional[str] = None
    key_improvements: list[str] = []
    learning_points: list[str] = []
    best_practices_used: list[str] = []
    anti_patterns: list[str] = []
    suggested_resources: list[str] = []
    misconceptions: list[str] = []
    hint: Optional[HintReport] = None
    awards: list[AwardOut] = []

    agent_steps: list[str] = []
    tokens_used: int = 0
    latency_ms: int = 0
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        protected_namespaces = ()


FORBIDDEN_REPORT_FIELDS = frozenset({
    "reference_solution",
    "reference",
    "corrected_code",
    "solution",
    "test_cases",
    "expected_outputs",
})
