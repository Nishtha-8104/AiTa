"""HTTP-level wiring. Proves the response actually serialises through FastAPI and
that the leak boundary holds on the real payload a client would receive."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.core.llm_gateway import GatewayResult
from app.features.accounts.models import User


def fake_explain(monkeypatch):
    from app.features.grading.agent.schemas import Explanation

    explanation = Explanation(summary="ok", detailed_feedback="## ok")
    monkeypatch.setattr(
        "app.core.llm_gateway.invoke",
        lambda purpose, payload, **kwargs: GatewayResult(explanation, "ok", "m", 0, 0, 0, 0),
    )


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
    Local = sessionmaker(bind=engine)
    db = Local()

    user = User(email="api@example.com", username="apiuser")
    db.add(user)
    db.commit()

    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user

    # Constructed without `with`, so the lifespan never runs. The lifespan calls
    # Base.metadata.create_all against the real DATABASE_URL, which would make the
    # test suite reach out to the live database on every fixture.
    test_client = TestClient(app)
    yield test_client, db, user

    app.dependency_overrides.clear()
    db.close()


def test_submit_returns_summary_without_eval_status_fields(client):
    test_client, _, _ = client
    response = test_client.post("/api/v1/code-eval/submit", json={
        "language": "python", "code": "print(1)", "title": "t",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "t"
    assert "status" not in body
    assert "eval_count" not in body
    assert "problem_id" in body


def test_submit_generates_a_title_when_missing(client):
    test_client, _, _ = client
    response = test_client.post("/api/v1/code-eval/submit", json={
        "language": "python", "code": "def add_two(a, b):\n    return a + b\n",
    })
    assert response.status_code == 201
    assert "Add Two" in response.json()["title"]


def test_submit_accepts_only_c_cpp_python(client):
    test_client, _, _ = client
    for path in ("/api/v1/code-eval/submit", "/api/v1/code-eval/evaluate"):
        response = test_client.post(path, json={"language": "java", "code": "class A{}"})
        assert response.status_code == 422


def test_list_submissions(client):
    test_client, _, _ = client
    test_client.post("/api/v1/code-eval/submit",
                     json={"language": "python", "code": "print(1)"})
    response = test_client.get("/api/v1/code-eval/submissions")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_missing_submission_returns_404_from_domain_error(client):
    test_client, _, _ = client
    response = test_client.get("/api/v1/code-eval/submissions/4242")
    assert response.status_code == 404
    assert "4242" in response.json()["detail"]


def test_run_executes_the_example_without_saving_anything(client, monkeypatch):
    test_client, db, _ = client

    from app.features.grading.logic.execution.base import ExecResult, ExecStatus
    from app.features.grading.models import CodeSubmission
    from app.features.problems.models import (
        Problem,
        ProblemSource,
        TestCase,
        TestCaseKind,
        TestCaseOrigin,
    )
    from tests.conftest import FakeExecutionProvider

    problem = Problem(source=ProblemSource.DSA, statement="max", statement_hash="r" * 64)
    problem.test_cases = [TestCase(
        kind=TestCaseKind.SAMPLE, stdin="1\n-15\n", expected_stdout="-15",
        stdin_hash="a", origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=0,
    )]
    db.add(problem)
    db.commit()

    provider = FakeExecutionProvider([ExecResult(status=ExecStatus.OK, stdout="0\n")])
    monkeypatch.setattr("app.features.grading.logic.execution.run_code.get_provider", lambda: provider)

    response = test_client.post("/api/v1/code-eval/run", json={
        "problem_id": problem.id, "language": "python", "code": "print(0)",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "Wrong answer on test 1"
    assert body["cases"][0]["expected"] == "-15"
    assert body["cases"][0]["actual"] == "0"
    assert db.query(CodeSubmission).count() == 0


def test_run_rejects_a_language_the_sandbox_cannot_execute(client):
    test_client, db, _ = client

    from app.features.problems.models import (
        Problem,
        ProblemSource,
        TestCase,
        TestCaseKind,
        TestCaseOrigin,
    )

    problem = Problem(source=ProblemSource.DSA, statement="q", statement_hash="s" * 64)
    problem.test_cases = [TestCase(
        kind=TestCaseKind.SAMPLE, stdin="", expected_stdout="1",
        stdin_hash="a", origin=TestCaseOrigin.PROBLEM_SAMPLE, ordinal=0,
    )]
    db.add(problem)
    db.commit()

    response = test_client.post("/api/v1/code-eval/run", json={
        "problem_id": problem.id, "language": "sql", "code": "select 1",
    })
    assert response.status_code == 422


def test_review_mode_evaluation_returns_null_correctness(client, monkeypatch):
    test_client, _, _ = client

    from app.features.grading.logic.execution.base import ExecResult, ExecStatus
    from tests.conftest import FakeExecutionProvider

    provider = FakeExecutionProvider([ExecResult(status=ExecStatus.OK, stdout="1\n")])
    # run_code imported get_provider by name, so the binding to patch lives there.
    monkeypatch.setattr(
        "app.features.grading.logic.execution.run_code.get_provider", lambda: provider
    )

    fake_explain(monkeypatch)

    submit = test_client.post("/api/v1/code-eval/submit",
                              json={"language": "python", "code": "print(1)"})
    submission_id = submit.json()["id"]

    response = test_client.post(
        f"/api/v1/code-eval/submit/{submission_id}/evaluate"
    )
    assert response.status_code == 200
    body = response.json()

    assert body["mode"] == "review"
    assert body["verification_status"] == "unverified"
    assert body["unverified_reason"] == "no_problem_statement"
    assert body["scores"]["correctness"] is None
    assert body["tests_total"] == 0


def test_response_payload_carries_no_answer_material(client, monkeypatch):
    test_client, _, _ = client

    from app.features.grading.logic.execution.base import ExecResult, ExecStatus
    from tests.conftest import FakeExecutionProvider

    provider = FakeExecutionProvider([ExecResult(status=ExecStatus.OK, stdout="1\n")])
    # run_code imported get_provider by name, so the binding to patch lives there.
    monkeypatch.setattr(
        "app.features.grading.logic.execution.run_code.get_provider", lambda: provider
    )

    fake_explain(monkeypatch)

    submit = test_client.post("/api/v1/code-eval/submit",
                              json={"language": "python", "code": "print(1)"})
    response = test_client.post(
        f"/api/v1/code-eval/submit/{submit.json()['id']}/evaluate"
    )
    payload = response.text
    for forbidden in ("reference_solution", "corrected_code"):
        assert forbidden not in payload
