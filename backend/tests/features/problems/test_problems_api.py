"""HTTP-level wiring for POST /problems/generate.

Proves the bank is asked first, that both paths serialise through FastAPI with no
answer material on them, and that neither outage reaches the student as raw
infrastructure text.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user, get_current_user
from app.core.exceptions import ExecutorUnavailable
from app.core.llm_gateway import GatewayResult
from app.features.accounts.models import User
from app.features.grading.agent.schemas import GeneratedCase, GeneratedTests
from app.features.grading.logic.execution.base import ExecResult, ExecStatus
from app.features.grading.models import Language
from app.features.problems.logic.schemas import ProblemDraft
from app.features.problems.models import (
    Difficulty,
    IOMode,
    Problem,
    ProblemReference,
    ProblemSource,
    ReferenceStatus,
    TestCase,
    TestCaseKind,
    TestCaseOrigin,
)
from tests.conftest import FakeExecutionProvider

ENDPOINT = "/api/v1/problems/generate"
REFERENCE = "print(sum(map(int, input().split())))"


@pytest.fixture
def client():
    # StaticPool keeps every connection on the same in-memory database; TestClient
    # runs the request on another thread, which would otherwise get an empty one.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    user = User(email="cp@example.com", username="cpuser")
    db.add(user)
    db.commit()

    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user

    # Constructed without `with`, so the lifespan never runs against the real database.
    yield TestClient(app), db

    app.dependency_overrides.clear()
    db.close()


def seed_curated(db, topic="arrays", difficulty=Difficulty.EASY):
    problem = Problem(
        source=ProblemSource.DSA, external_id="dsa-two-sum",
        statement="Read two integers and print their sum.", statement_hash="a" * 64,
        topic=topic, difficulty=difficulty, io_mode=IOMode.STDIN_STDOUT,
    )
    db.add(problem)
    db.commit()
    db.add(TestCase(
        problem_id=problem.id, kind=TestCaseKind.SAMPLE, stdin="1 2\n",
        expected_stdout="3", stdin_hash="b" * 64,
        origin=TestCaseOrigin.CROSS_CHECKED, ordinal=1,
    ))
    db.commit()
    return problem


def fake_statement(monkeypatch, draft=None, parsed=True):
    """Stand in for the structured statement call, without building a model."""
    draft = draft or ProblemDraft(
        title="Sum Two Integers",
        statement="Read two integers on one line and print their sum.",
        constraints=["1 <= a <= 100"],
        hints=["Splitting a line", "The two values always fit in an int"],
    )

    monkeypatch.setattr(
        "app.core.llm_gateway.invoke",
        lambda purpose, payload, **kwargs: GatewayResult(
            draft if parsed else None, "ok", "m", 0, 0, 0, 0),
    )


def fake_tests(monkeypatch, provider):
    """Drive the real generate_tests through its module-level default generator."""
    generated = GeneratedTests(
        reference_solution=REFERENCE,
        cases=[GeneratedCase(kind="normal", stdin=s, expected_stdout=e, rationale="r")
               for s, e in (("1 2\n", "3"), ("4 5\n", "9"), ("0 0\n", "0"))],
    )
    monkeypatch.setattr(
        "app.features.problems.logic.test_generation.generate_tests._default_generator",
        lambda **kwargs: generated,
    )
    monkeypatch.setattr("app.features.grading.logic.execution.run_code.get_provider",
                        lambda: provider)


def ok(stdout):
    return ExecResult(status=ExecStatus.OK, stdout=stdout, time_ms=1)


def no_generation(monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("generation must not run on a bank hit")

    monkeypatch.setattr("app.features.problems.logic.generation.generate_problem", explode)


def test_bank_is_asked_before_anything_is_generated(client, monkeypatch):
    test_client, db = client
    problem = seed_curated(db)
    no_generation(monkeypatch)

    response = test_client.post(ENDPOINT, json={"topic": "arrays",
                                                "difficulty": "easy"})

    assert response.status_code == 200
    body = response.json()
    assert body["origin"] == "bank"
    assert body["problem_id"] == problem.id
    assert body["difficulty"] == "easy"
    assert body["title"] == "Two Sum"
    assert body["examples"]


def test_bank_miss_generates_a_real_problem(client, monkeypatch):
    test_client, db = client
    seed_curated(db, topic="arrays")
    fake_statement(monkeypatch)
    fake_tests(monkeypatch, FakeExecutionProvider([ok("3\n"), ok("9\n"), ok("0\n")]))

    response = test_client.post(ENDPOINT, json={"topic": "graphs",
                                                "difficulty": "medium"})

    assert response.status_code == 200
    body = response.json()
    assert body["origin"] == "generated"
    assert body["title"] == "Sum Two Integers"
    assert body["difficulty"] == "medium"

    stored = db.query(Problem).filter(Problem.id == body["problem_id"]).one()
    assert stored.source is ProblemSource.GENERATED
    assert len(stored.test_cases) == 3


@pytest.mark.parametrize("topic", ["arrays", "graphs"])
def test_neither_path_returns_answer_material(client, monkeypatch, topic):
    test_client, db = client
    seed_curated(db, topic="arrays")
    fake_statement(monkeypatch)
    fake_tests(monkeypatch, FakeExecutionProvider([ok("3\n"), ok("9\n"), ok("0\n")]))

    response = test_client.post(ENDPOINT, json={"topic": topic,
                                                "difficulty": "easy"})

    assert response.status_code == 200
    assert "solution_code" not in response.json()
    assert REFERENCE not in response.text


def test_hints_are_capped_on_the_wire(client, monkeypatch):
    test_client, db = client
    fake_statement(monkeypatch, draft=ProblemDraft(
        title="Sum Two Integers",
        statement="Read two integers on one line and print their sum.",
        constraints=[],
        hints=["A running sum", "The order never matters",
               "Add each element as you pass it", "Print once at the end"],
    ))
    fake_tests(monkeypatch, FakeExecutionProvider([ok("3\n"), ok("9\n"), ok("0\n")]))

    response = test_client.post(ENDPOINT, json={"topic": "graphs"})

    assert response.status_code == 200
    assert response.json()["hints"] == ["A running sum", "The order never matters"]


def test_expert_is_served_and_labelled_as_hard(client, monkeypatch):
    test_client, db = client
    seed_curated(db, topic="arrays", difficulty=Difficulty.HARD)

    response = test_client.post(ENDPOINT, json={"topic": "arrays",
                                                "difficulty": "expert"})

    assert response.status_code == 200
    assert response.json()["difficulty"] == "hard"


def test_statement_outage_is_a_plain_503(client, monkeypatch):
    test_client, _ = client
    fake_statement(monkeypatch, parsed=False)

    response = test_client.post(ENDPOINT, json={"topic": "graphs"})

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "A problem could not be generated right now. Please try again in a moment."
    )


def test_executor_outage_is_a_plain_503_not_infrastructure_text(client, monkeypatch):
    test_client, db = client
    fake_statement(monkeypatch)

    class Exploding(FakeExecutionProvider):
        def __init__(self):
            super().__init__([])

        def run_batch(self, language, source, stdins, limits):
            raise ExecutorUnavailable(
                "executor unreachable: [Errno 11001] getaddrinfo failed"
            )

    fake_tests(monkeypatch, Exploding())

    response = test_client.post(ENDPOINT, json={"topic": "graphs"})

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail == ("A problem was written but no test cases could be verified "
                      "for it. Please try again.")
    assert "getaddrinfo" not in response.text
    assert "executor" not in response.text

    # The row survives the outage so a later attempt reuses it.
    assert db.query(Problem).filter(
        Problem.source == ProblemSource.GENERATED).count() == 1


def test_solution_opens_only_after_a_give_up(client):
    test_client, db = client
    problem = seed_curated(db)
    db.add(ProblemReference(problem_id=problem.id, language=Language.PYTHON,
                            source=REFERENCE, status=ReferenceStatus.VALIDATED))
    db.commit()
    url = f"/api/v1/problems/{problem.id}/solution"

    assert test_client.post("/api/v1/problems/999/solution",
                            json={"language": "python"}).status_code == 404
    assert test_client.post(url, json={"language": "python"}).status_code == 403

    response = test_client.post(url, json={"language": "python", "give_up": True})
    assert response.status_code == 200
    assert response.json() == {"language": "python", "code": REFERENCE}
    assert test_client.post(url, json={"language": "python"}).status_code == 200


@pytest.mark.parametrize("language, marker", [
    ("python", "import sys"),
    ("cpp", "#include <bits/stdc++.h>"),
    ("c", "#include <stdio.h>"),
])
def test_starter_code_follows_the_requested_language(client, monkeypatch, language, marker):
    test_client, db = client
    seed_curated(db)
    no_generation(monkeypatch)

    response = test_client.post(ENDPOINT, json={"topic": "arrays",
                                                "difficulty": "easy",
                                                "language": language})

    assert response.status_code == 200
    assert marker in response.json()["starter_code"]
