"""The EvalReport is the only object that crosses a boundary — HTTP response now,
chatbot tool return in Month 2. If the reference solution or the full answer key can
reach it, the Month 2 hint guardrail is decorative: it inspects the reply, but the
answer would already be in the model's context."""

from app.features.grading.agent.schemas import (
    FORBIDDEN_REPORT_FIELDS, CaseReport, EvalReport, FailingCaseReport,
)
from app.features.grading.agent.state import EvalState


def test_report_declares_no_forbidden_field():
    fields = set(EvalReport.model_fields)
    assert fields.isdisjoint(FORBIDDEN_REPORT_FIELDS), (
        f"EvalReport must not expose {fields & FORBIDDEN_REPORT_FIELDS}"
    )


def test_report_has_no_corrected_code():
    assert "corrected_code" not in EvalReport.model_fields


def test_case_report_carries_no_expected_output():
    fields = set(CaseReport.model_fields)
    assert "expected_stdout" not in fields
    assert "stdin" not in fields
    assert "actual_stdout" not in fields


def test_only_the_failing_case_reveals_data():
    revealed = set(FailingCaseReport.model_fields) - set(CaseReport.model_fields)
    assert revealed == {"stdin", "expected_stdout", "actual_stdout", "stderr", "rationale"}


def test_state_holds_the_reference_but_report_does_not():
    assert "reference_solution" in EvalState.model_fields
    assert "reference_solution" not in EvalReport.model_fields


def test_serialised_report_never_contains_the_reference_string():
    secret = "THE_REFERENCE_SOLUTION_BODY"
    report = EvalReport(
        submission_id=1,
        tests_passed=1,
        tests_total=2,
        cases=[CaseReport(ordinal=1, kind="normal", status="ok", passed=True, time_ms=1),
               CaseReport(ordinal=2, kind="edge", status="wrong_answer",
                          passed=False, time_ms=1)],
        first_failing_case=FailingCaseReport(
            ordinal=2, kind="edge", status="wrong_answer", passed=False, time_ms=1,
            stdin="", expected_stdout="0", actual_stdout="1",
        ),
        summary="You are close.",
    )
    assert secret not in report.model_dump_json()


def test_report_exposes_at_most_one_expected_output():
    report = EvalReport(
        cases=[CaseReport(ordinal=i, kind="normal", status="wrong_answer",
                          passed=False, time_ms=1) for i in range(1, 6)],
        first_failing_case=FailingCaseReport(
            ordinal=1, kind="normal", status="wrong_answer", passed=False, time_ms=1,
            stdin="in", expected_stdout="out", actual_stdout="nope",
        ),
    )
    payload = report.model_dump()
    expected_values = [c.get("expected_stdout") for c in payload["cases"]
                       if isinstance(c, dict) and "expected_stdout" in c]
    assert expected_values == []
    assert payload["first_failing_case"]["expected_stdout"] == "out"


def test_hint_payloads_declare_no_forbidden_field():
    from app.features.feedback.schemas import HintResponse
    from app.features.grading.agent.schemas import HintReport

    for model in (HintReport, HintResponse):
        assert set(model.model_fields).isdisjoint(FORBIDDEN_REPORT_FIELDS)


def test_l1_hint_is_built_from_the_failing_case_only():
    from app.features.grading.agent.nodes.hint_l1 import hint_l1

    state = EvalState(db=None, submission_id=1, user_id=1,
                      reference_solution="THE_REFERENCE_SOLUTION_BODY")
    state.report = EvalReport(
        verification_status="verified",
        first_failing_case=FailingCaseReport(
            ordinal=2, kind="edge", status="wrong_answer", passed=False, time_ms=1,
            stdin="1\n-7\n", expected_stdout="-7", actual_stdout="0",
        ),
    )
    hint_l1(state)
    assert state.report.hint.level == 1
    assert "THE_REFERENCE_SOLUTION_BODY" not in state.report.model_dump_json()
