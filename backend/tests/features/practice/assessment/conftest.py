import pytest

from app.features.accounts.models import User
from app.features.grading.logic.execution.base import ExecResult, ExecStatus, ExecutionProvider
from app.features.problems.models import (
    Problem,
    ProblemSource,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)

FIXED = "fixed program"
BUGGY = "buggy program"


class ScriptedProvider(ExecutionProvider):
    """Answers by source text: {source: stdout | ExecResult}. Unknown sources crash."""

    def __init__(self, outputs: dict):
        self.outputs = outputs
        self.calls = []

    def run_batch(self, language, source, stdins, limits):
        self.calls.append(source)
        out = self.outputs.get(source)
        if isinstance(out, ExecResult):
            return [out for _ in stdins]
        if out is None:
            return [ExecResult(status=ExecStatus.RUNTIME_ERROR, stderr="boom") for _ in stdins]
        return [ExecResult(status=ExecStatus.OK, stdout=out) for _ in stdins]


@pytest.fixture
def user(session):
    u = User(email="a@example.com", username="assessed")
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def bank_problem(session):
    p = Problem(source=ProblemSource.DSA, external_id="dsa-demo", statement="largest",
                statement_hash="q" * 64, topic="arrays")
    p.test_cases = [
        TestCase(kind=TestCaseKind.SAMPLE, stdin="3 1 2\n", expected_stdout="3",
                 stdin_hash="a", origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=0),
        TestCase(kind=TestCaseKind.EDGE, stdin="-4 -9\n", expected_stdout="-4",
                 stdin_hash="b", origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1),
    ]
    session.add(p)
    session.commit()
    return p


def mcq(**overrides) -> dict:
    item = {
        "external_id": "mcq-loops-1",
        "topic": "loops",
        "difficulty": "easy",
        "stem": "What does `print(len(range(1, 5)))` print?",
        "options": [
            {"text": "5", "misconception": "off_by_one"},
            {"text": "4", "misconception": None},
            {"text": "3", "misconception": "wrong_loop_bound"},
        ],
        "answer_index": 1,
        "verify_code": "print(len(range(1, 5)))",
        "explanations": ["range stops before its end"],
    }
    item.update(overrides)
    return item


def debug_item(**overrides) -> dict:
    item = {
        "external_id": "debug-python-dsa-demo",
        "problem_external_id": "dsa-demo",
        "topic": "arrays",
        "difficulty": "easy",
        "language": "python",
        "statement": "largest",
        "fixed_code": FIXED,
        "buggy_code": BUGGY,
        "bug_type": "wrong_initial_value",
    }
    item.update(overrides)
    return item


def standard_provider() -> ScriptedProvider:
    return ScriptedProvider({
        "print(len(range(1, 5)))": "4\n",
        FIXED: "3\n-4\n",
        BUGGY: "3\n0\n",
    })
