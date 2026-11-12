import json
import pathlib

from app.core.config import settings
from app.features.grading.agent.schemas import GeneratedCase, GeneratedTests
from app.features.grading.logic.execution.base import ExecResult, ExecStatus
from app.features.problems.models import Problem
from scripts.seed.ingest_problems import DATA, ingest
from tests.conftest import FakeExecutionProvider

ROWS = [
    {"external_id": "dsa-a", "source": "dsa",
     "statement": "Read n on the first line and print n.",
     "constraints": "", "topic": "io", "difficulty": "easy"},
    {"external_id": "dsa-b", "source": "dsa",
     "statement": "Read n on the first line and print n plus one.",
     "constraints": "", "topic": "io", "difficulty": "easy"},
]


def generated():
    return GeneratedTests(
        reference_solution="print(input())",
        cases=[GeneratedCase(kind="normal", stdin=f"{i}\n", expected_stdout=str(i),
                             rationale="r") for i in (1, 2, 3)],
    )


def ok_provider():
    return FakeExecutionProvider([
        ExecResult(status=ExecStatus.OK, stdout="1\n"),
        ExecResult(status=ExecStatus.OK, stdout="2\n"),
        ExecResult(status=ExecStatus.OK, stdout="3\n"),
    ])


def test_creates_problems_and_cases(session):
    report = ingest(session, ROWS, generator=lambda **k: generated(),
                    provider=ok_provider(), pause=0)
    assert report.created == 2
    assert report.generated == 2
    assert session.query(Problem).count() == 2


def test_rerun_is_idempotent(session):
    ingest(session, ROWS, generator=lambda **k: generated(),
           provider=ok_provider(), pause=0)

    def explode(**kwargs):
        raise AssertionError("must not call the generator on a rerun")

    report = ingest(session, ROWS, generator=explode, provider=ok_provider(), pause=0)
    assert report.created == 0
    assert report.skipped == 2
    assert session.query(Problem).count() == 2


def test_limit_stops_early(session):
    report = ingest(session, ROWS, generator=lambda **k: generated(),
                    provider=ok_provider(), limit=1, pause=0)
    assert report.seen == 1
    assert session.query(Problem).count() == 1


def test_unverified_problems_are_reported_not_fatal(session):
    bad = FakeExecutionProvider([
        ExecResult(status=ExecStatus.OK, stdout="9\n"),
        ExecResult(status=ExecStatus.OK, stdout="9\n"),
        ExecResult(status=ExecStatus.OK, stdout="9\n"),
    ])
    report = ingest(session, ROWS[:1], generator=lambda **k: generated(),
                    provider=bad, pause=0)
    assert report.unverified == ["dsa-a"]
    assert report.generated == 0


def test_shipped_bank_is_valid():
    rows = json.loads(pathlib.Path(DATA).read_text(encoding="utf-8"))
    assert len(rows) == 25
    assert len({r["external_id"] for r in rows}) == 25
    for row in rows:
        assert row["source"] in ("mbpp", "dsa")
        assert row["difficulty"] in ("easy", "medium", "hard")
        lowered = row["statement"].lower()
        assert "print" in lowered, row["external_id"]
        assert "line" in lowered, row["external_id"]


def test_every_shipped_problem_carries_its_own_tests():
    rows = json.loads(pathlib.Path(DATA).read_text(encoding="utf-8"))
    for row in rows:
        ext = row["external_id"]
        assert row.get("reference"), ext
        cases = row.get("tests") or []
        assert len(cases) >= settings.TEST_CASES_MIN, ext
        for case in cases:
            assert case["kind"] in ("sample", "normal", "edge"), ext
            assert case["stdin"].endswith("\n"), ext
            # A case expecting no output consumes no lines when the batch output is
            # split, so it can never fail. Those must not reach the bank.
            assert case["expected_stdout"].strip(), ext


def test_shipped_cases_have_distinct_stdin():
    rows = json.loads(pathlib.Path(DATA).read_text(encoding="utf-8"))
    for row in rows:
        stdins = [c["stdin"] for c in row["tests"]]
        assert len(set(stdins)) == len(stdins), row["external_id"]


class CuratedReferenceProvider(FakeExecutionProvider):
    """Stands in for the sandbox: replays each case's authored expected output."""

    def __init__(self, rows):
        super().__init__([])
        # One run_batch call per problem, in row order — the same stdin block can
        # appear in two problems, so it cannot be used as a key.
        self.rows = list(rows)
        self.index = 0

    def run_batch(self, language, source, stdins, limits):
        row = self.rows[self.index]
        self.index += 1
        assert len(stdins) == len(row["tests"]), row["external_id"]
        return [ExecResult(status=ExecStatus.OK, stdout=c["expected_stdout"] + "\n")
                for c in row["tests"]]


def test_shipped_bank_ingests_without_an_llm(session):
    rows = json.loads(pathlib.Path(DATA).read_text(encoding="utf-8"))

    def explode(**kwargs):
        raise AssertionError("the shipped bank must not call the generator")

    report = ingest(session, rows, generator=explode,
                    provider=CuratedReferenceProvider(rows), pause=0)
    assert report.created == 25
    assert report.curated == 25
    assert report.generated == 0
    assert report.unverified == []
    assert session.query(Problem).count() == 25
