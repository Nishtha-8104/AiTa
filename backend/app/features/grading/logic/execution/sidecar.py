"""HTTP client for the executor container's /run-batch; any network or server failure
becomes ExecutorUnavailable."""

import httpx

from app.core.exceptions import ExecutorUnavailable
from app.core.languages import EXECUTABLE_LANGUAGES
from app.features.grading.logic.execution.base import (
    ExecLimits, ExecResult, ExecStatus, ExecutionProvider,
)
from app.features.grading.models import Language


class SidecarProvider(ExecutionProvider):
    def __init__(self, base_url: str, timeout: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def run_batch(self, language: Language, source: str, stdins: list[str],
                  limits: ExecLimits) -> list[ExecResult]:
        if language not in EXECUTABLE_LANGUAGES:
            raise ExecutorUnavailable(f"language not executable: {language.value}")

        payload = {
            "language": language.value,
            "source": source,
            "cases": [{"id": index, "stdin": stdin} for index, stdin in enumerate(stdins)],
            "limits": limits.model_dump(),
        }
        try:
            response = self._client.post(f"{self._base_url}/run-batch", json=payload)
        except httpx.HTTPError as exc:
            raise ExecutorUnavailable(f"executor unreachable: {exc}") from exc

        if response.status_code != 200:
            raise ExecutorUnavailable(
                f"executor returned {response.status_code}: {response.text[:200]}"
            )

        body = response.json()
        compile_output = body.get("compile_output")
        return [
            ExecResult(
                status=ExecStatus(case["status"]),
                stdout=case.get("stdout", ""),
                stderr=case.get("stderr", ""),
                truncated=case.get("truncated", False),
                time_ms=case.get("time_ms", 0),
                memory_kb=case.get("memory_kb"),
                exit_code=case.get("exit_code"),
                compile_output=compile_output,
            )
            for case in body.get("results", [])
        ]
