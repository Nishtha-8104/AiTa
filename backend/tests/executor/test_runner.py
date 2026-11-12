import sys

import pytest

from executor.runner import RunLimits, run_batch

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="runner uses POSIX rlimits; exercised inside the executor container",
)

LIMITS = RunLimits()


def test_python_clean_run():
    batch = run_batch("python", "n = int(input())\nprint(n * 2)",
                      [{"id": 1, "stdin": "21\n"}], LIMITS)
    result = batch.results[0]
    assert result.status == "ok"
    assert result.stdout.strip() == "42"
    assert result.exit_code == 0


def test_python_syntax_error_is_compile_error_for_every_case():
    batch = run_batch("python", "def broken(:\n    pass",
                      [{"id": 1, "stdin": ""}, {"id": 2, "stdin": ""}], LIMITS)
    assert [r.status for r in batch.results] == ["compile_error", "compile_error"]
    assert batch.compile_output


def test_python_runtime_error():
    batch = run_batch("python", "raise SystemExit(3)", [{"id": 1, "stdin": ""}], LIMITS)
    assert batch.results[0].status == "runtime_error"
    assert batch.results[0].exit_code == 3


def test_timeout():
    limits = RunLimits(wall_seconds=1.0, cpu_seconds=5)
    batch = run_batch("python", "while True:\n    pass", [{"id": 1, "stdin": ""}], limits)
    assert batch.results[0].status == "timeout"


def test_output_truncated_and_flagged():
    limits = RunLimits(output_kb=1)
    batch = run_batch("python", "print('x' * 5000)", [{"id": 1, "stdin": ""}], limits)
    result = batch.results[0]
    assert result.truncated is True
    assert len(result.stdout.encode("utf-8")) <= 1024


def test_cpp_compiles_once_and_runs_all_cases():
    src = ("#include <iostream>\n"
           "int main(){int n; std::cin >> n; std::cout << n * 2 << std::endl;}")
    cases = [{"id": 1, "stdin": "3\n"}, {"id": 2, "stdin": "5\n"}]
    batch = run_batch("cpp", src, cases, LIMITS)
    assert [r.status for r in batch.results] == ["ok", "ok"]
    assert [r.stdout.strip() for r in batch.results] == ["6", "10"]


def test_cpp_compile_error():
    batch = run_batch("cpp", "int main(){ return", [{"id": 1, "stdin": ""}], LIMITS)
    assert batch.results[0].status == "compile_error"
    assert "error" in batch.compile_output.lower()


def test_c_sums_two_ints():
    src = ("#include <stdio.h>\n"
           "int main(void){int a, b; scanf(\"%d %d\", &a, &b); printf(\"%d\\n\", a + b); return 0;}")
    batch = run_batch("c", src, [{"id": 1, "stdin": "2 40\n"}], LIMITS)
    assert batch.results[0].status == "ok"
    assert batch.results[0].stdout.strip() == "42"


def test_c_compile_error():
    batch = run_batch("c", "int main(void){ return", [{"id": 1, "stdin": ""}], LIMITS)
    assert batch.results[0].status == "compile_error"
    assert "error" in batch.compile_output.lower()


def test_unknown_language_is_internal_error():
    batch = run_batch("brainfuck", "+++", [{"id": 1, "stdin": ""}], LIMITS)
    assert batch.results[0].status == "internal_error"
