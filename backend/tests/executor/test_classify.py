from executor.runner import _classify


def test_clean_exit_is_ok():
    assert _classify(0, "") == "ok"


def test_sigkill_from_cpu_limit_is_timeout_not_memory():
    assert _classify(-9, "") == "timeout"


def test_sigxcpu_is_timeout():
    assert _classify(-24, "") == "timeout"


def test_python_memory_error_is_memory_exceeded():
    assert _classify(1, "MemoryError") == "memory_exceeded"


def test_cpp_bad_alloc_is_memory_exceeded():
    assert _classify(-6, "terminate called: std::bad_alloc") == "memory_exceeded"


def test_memory_marker_wins_over_signal():
    assert _classify(-9, "MemoryError: out of memory") == "memory_exceeded"


def test_ordinary_nonzero_exit_is_runtime_error():
    assert _classify(1, "ValueError: boom") == "runtime_error"
