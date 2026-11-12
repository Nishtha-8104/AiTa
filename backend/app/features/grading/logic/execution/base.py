"""The sandbox contract: run statuses, resource limits, the result shape, and the
ExecutionProvider interface every backend implements."""

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from app.core.config import settings
from app.features.grading.models import Language


class ExecStatus(str, Enum):
    OK = "ok"
    WRONG_ANSWER = "wrong_answer"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"
    COMPILE_ERROR = "compile_error"
    INTERNAL_ERROR = "internal_error"


class ExecLimits(BaseModel):
    wall_seconds: float = Field(default_factory=lambda: settings.EXEC_WALL_SECONDS)
    cpu_seconds: int = Field(default_factory=lambda: settings.EXEC_CPU_SECONDS)
    memory_mb: int = Field(default_factory=lambda: settings.EXEC_MEMORY_MB)
    max_processes: int = Field(default_factory=lambda: settings.EXEC_MAX_PROCESSES)
    output_kb: int = Field(default_factory=lambda: settings.EXEC_OUTPUT_KB)
    compile_seconds: int = Field(default_factory=lambda: settings.EXEC_COMPILE_SECONDS)


class ExecResult(BaseModel):
    status: ExecStatus
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False
    time_ms: int = 0
    memory_kb: int | None = None
    exit_code: int | None = None
    compile_output: str | None = None


class ExecutionProvider(ABC):
    @abstractmethod
    def run_batch(self, language: Language, source: str, stdins: list[str],
                  limits: ExecLimits) -> list[ExecResult]:
        ...

    def run(self, language: Language, source: str, stdin: str,
            limits: ExecLimits) -> ExecResult:
        return self.run_batch(language, source, [stdin], limits)[0]
