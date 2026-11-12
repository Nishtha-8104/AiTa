import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from pydantic import BaseModel

SPECS = {
    "python": {
        "extension": ".py",
        "compile_cmd": ["python", "-m", "py_compile", "{src}"],
        "run_cmd": ["python", "{src}"],
    },
    "cpp": {
        "extension": ".cpp",
        "compile_cmd": ["g++", "-O2", "-std=c++17", "{src}", "-o", "{bin}"],
        "run_cmd": ["{bin}"],
    },
    "c": {
        "extension": ".c",
        "compile_cmd": ["gcc", "-O2", "-std=c17", "{src}", "-o", "{bin}", "-lm"],
        "run_cmd": ["{bin}"],
    },
}


class RunLimits(BaseModel):
    wall_seconds: float = 2.0
    cpu_seconds: int = 2
    memory_mb: int = 256
    max_processes: int = 64
    output_kb: int = 64
    compile_seconds: int = 10


class CaseResult(BaseModel):
    id: int
    status: str
    stdout: str = ""
    stderr: str = ""
    truncated: bool = False
    time_ms: int = 0
    memory_kb: int | None = None
    exit_code: int | None = None


class BatchResult(BaseModel):
    results: list[CaseResult]
    compile_output: str | None = None


def _truncate(text: str, limit_kb: int) -> tuple[str, bool]:
    limit = limit_kb * 1024
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore"), True


def _limiter(limits: RunLimits):
    import os
    import resource

    def apply():
        # Soft below hard so SIGXCPU is delivered first and stays distinguishable
        # from an OOM kill; equal values escalate straight to SIGKILL.
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds + 1))
        memory_bytes = limits.memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_NPROC, (limits.max_processes, limits.max_processes))
        file_bytes = 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))
        os.setsid()

    return apply


def _peak_memory_kb() -> int:
    try:
        import resource
    except ImportError:
        return 0
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss


_MEMORY_MARKERS = ("MemoryError", "bad_alloc", "Cannot allocate memory")


def _classify(returncode: int, stderr: str) -> str:
    if returncode == 0:
        return "ok"
    # RLIMIT_AS surfaces as an allocation failure in the language runtime, not as a
    # signal. Signals mean the CPU or wall clock ran out, so check stderr first --
    # otherwise an infinite loop killed by SIGKILL reads as a memory error.
    if any(marker in stderr for marker in _MEMORY_MARKERS):
        return "memory_exceeded"
    if returncode in (-24, -14, -9):
        return "timeout"
    return "runtime_error"


def _uniform(cases: list[dict], status: str, message: str = "") -> BatchResult:
    return BatchResult(
        results=[CaseResult(id=c["id"], status=status, stderr=message) for c in cases],
        compile_output=message or None,
    )


def run_batch(language: str, source: str, cases: list[dict], limits: RunLimits) -> BatchResult:
    spec = SPECS.get(language)
    if spec is None:
        return _uniform(cases, "internal_error", f"unsupported language: {language}")

    workdir = tempfile.mkdtemp(prefix="run-")
    try:
        src_path = Path(workdir) / f"main{spec['extension']}"
        src_path.write_text(source, encoding="utf-8")
        bin_path = Path(workdir) / "main"

        def render(argv: list[str]) -> list[str]:
            return [a.format(src=str(src_path), bin=str(bin_path)) for a in argv]

        compile_output = None
        if spec["compile_cmd"]:
            try:
                compiled = subprocess.run(
                    render(spec["compile_cmd"]),
                    cwd=workdir, capture_output=True, text=True,
                    timeout=limits.compile_seconds,
                )
            except subprocess.TimeoutExpired:
                return _uniform(cases, "compile_error", "compilation timed out")
            compile_output = (compiled.stderr or compiled.stdout).strip()
            if compiled.returncode != 0:
                return _uniform(cases, "compile_error", compile_output or "compilation failed")

        run_cmd = render(spec["run_cmd"])
        results: list[CaseResult] = []
        for case in cases:
            started = time.monotonic()
            memory_before = _peak_memory_kb()
            try:
                completed = subprocess.run(
                    run_cmd, cwd=workdir, input=case.get("stdin", ""),
                    capture_output=True, text=True,
                    timeout=limits.wall_seconds, preexec_fn=_limiter(limits),
                )
                status = _classify(completed.returncode, completed.stderr)
                stdout, out_cut = _truncate(completed.stdout, limits.output_kb)
                stderr, err_cut = _truncate(completed.stderr, limits.output_kb)
                exit_code = completed.returncode
            except subprocess.TimeoutExpired:
                status, stdout, stderr = "timeout", "", ""
                out_cut = err_cut = False
                exit_code = None

            memory_after = _peak_memory_kb()
            results.append(CaseResult(
                id=case["id"], status=status, stdout=stdout, stderr=stderr,
                truncated=out_cut or err_cut,
                time_ms=int((time.monotonic() - started) * 1000),
                memory_kb=max(memory_after - memory_before, 0) or None,
                exit_code=exit_code,
            ))

        return BatchResult(results=results, compile_output=compile_output)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
