from app.features.grading.logic.execution.base import ExecStatus
from app.features.grading.logic.execution.run_code import run_code
from app.features.grading.models import Language
from tests.conftest import FakeExecutionProvider, failing, ok


def test_all_pass():
    provider = FakeExecutionProvider([ok("6\n"), ok("10\n")])
    report = run_code(Language.PYTHON, "src", [("3\n", "6"), ("5\n", "10")], provider=provider)
    assert report.compiled is True
    assert (report.passed, report.total) == (2, 2)
    assert all(o.passed for o in report.outcomes)


def test_trailing_newline_still_passes():
    provider = FakeExecutionProvider([ok("42\n\n")])
    report = run_code(Language.PYTHON, "src", [("", "42")], provider=provider)
    assert report.passed == 1


def test_mismatch_becomes_wrong_answer():
    provider = FakeExecutionProvider([ok("7\n")])
    report = run_code(Language.PYTHON, "src", [("3\n", "6")], provider=provider)
    assert report.outcomes[0].status is ExecStatus.WRONG_ANSWER
    assert report.outcomes[0].passed is False
    assert report.passed == 0


def test_runtime_error_is_not_relabelled():
    provider = FakeExecutionProvider([failing(ExecStatus.RUNTIME_ERROR, stderr="boom")])
    report = run_code(Language.PYTHON, "src", [("", "6")], provider=provider)
    assert report.outcomes[0].status is ExecStatus.RUNTIME_ERROR
    assert report.outcomes[0].passed is False


def test_compile_error_sets_compiled_false():
    provider = FakeExecutionProvider([
        failing(ExecStatus.COMPILE_ERROR, compile_output="line 1: error"),
        failing(ExecStatus.COMPILE_ERROR, compile_output="line 1: error"),
    ])
    report = run_code(Language.CPP, "src", [("", "1"), ("", "2")], provider=provider)
    assert report.compiled is False
    assert report.compile_output == "line 1: error"
    assert report.passed == 0


def test_smoke_run_without_expected_output_never_wrong_answer():
    provider = FakeExecutionProvider([ok("anything at all\n")])
    report = run_code(Language.PYTHON, "src", [("", None)], provider=provider)
    outcome = report.outcomes[0]
    assert outcome.status is ExecStatus.OK
    assert outcome.passed is True
    assert outcome.expected_stdout is None


def test_provider_receives_one_call_for_all_cases():
    provider = FakeExecutionProvider([ok("1"), ok("2"), ok("3")])
    run_code(Language.PYTHON, "src", [("a", "1"), ("b", "2"), ("c", "3")], provider=provider)
    assert len(provider.calls) == 1
    assert provider.calls[0]["stdins"] == ["a", "b", "c"]


def test_empty_case_list_is_a_no_op():
    provider = FakeExecutionProvider([])
    report = run_code(Language.PYTHON, "src", [], provider=provider)
    assert (report.passed, report.total) == (0, 0)
    assert report.outcomes == []
