import httpx
import pytest

from app.core.exceptions import ExecutorUnavailable
from app.features.grading.logic.execution.base import ExecLimits, ExecStatus
from app.features.grading.logic.execution.sidecar import SidecarProvider
from app.features.grading.models import Language


def _provider(handler):
    provider = SidecarProvider("http://executor:8080")
    provider._client = httpx.Client(transport=httpx.MockTransport(handler))
    return provider


def _case(**overrides):
    case = {"id": 0, "status": "ok", "stdout": "", "stderr": "",
            "truncated": False, "time_ms": 0, "memory_kb": None, "exit_code": 0}
    case.update(overrides)
    return case


def test_maps_ok_status_and_fields():
    def handler(request):
        return httpx.Response(200, json={
            "results": [_case(stdout="42\n", time_ms=12, memory_kb=900)],
            "compile_output": None,
        })

    results = _provider(handler).run_batch(Language.PYTHON, "print(42)", ["\n"], ExecLimits())
    assert len(results) == 1
    assert results[0].status is ExecStatus.OK
    assert results[0].stdout == "42\n"
    assert results[0].time_ms == 12


def test_compile_error_propagates_to_every_case():
    def handler(request):
        return httpx.Response(200, json={
            "results": [
                _case(id=0, status="compile_error", stderr="boom", exit_code=None),
                _case(id=1, status="compile_error", stderr="boom", exit_code=None),
            ],
            "compile_output": "boom",
        })

    results = _provider(handler).run_batch(Language.CPP, "int main(){", ["", ""], ExecLimits())
    assert [r.status for r in results] == [ExecStatus.COMPILE_ERROR, ExecStatus.COMPILE_ERROR]
    assert results[0].compile_output == "boom"


def test_http_error_raises_executor_unavailable():
    def handler(request):
        return httpx.Response(503, text="saturated")

    with pytest.raises(ExecutorUnavailable):
        _provider(handler).run_batch(Language.PYTHON, "print(1)", [""], ExecLimits())


def test_connection_failure_raises_executor_unavailable():
    def handler(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(ExecutorUnavailable):
        _provider(handler).run_batch(Language.PYTHON, "print(1)", [""], ExecLimits())


def test_non_executable_language_raises():
    def handler(request):
        return httpx.Response(200, json={"results": [], "compile_output": None})

    with pytest.raises(ExecutorUnavailable):
        _provider(handler).run_batch(Language.JAVA, "class A{}", [""], ExecLimits())


def test_payload_indexes_cases_in_order():
    seen = {}

    def handler(request):
        import json
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={
            "results": [_case(id=0), _case(id=1)], "compile_output": None,
        })

    _provider(handler).run_batch(Language.PYTHON, "src", ["a", "b"], ExecLimits())
    assert [c["id"] for c in seen["cases"]] == [0, 1]
    assert [c["stdin"] for c in seen["cases"]] == ["a", "b"]


def test_run_delegates_to_run_batch():
    def handler(request):
        return httpx.Response(200, json={
            "results": [_case(stdout="1")], "compile_output": None,
        })

    result = _provider(handler).run(Language.PYTHON, "print(1)", "", ExecLimits())
    assert result.status is ExecStatus.OK
    assert result.stdout == "1"
