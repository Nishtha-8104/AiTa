from types import SimpleNamespace

from app.features.grading.agent.multi_test import (
    all_failed, merge_cases, split_actual, verdict_for,
)


def case(stdin, expected, kind="normal", rationale=None):
    return SimpleNamespace(stdin=stdin, expected_stdout=expected,
                           kind=kind, rationale=rationale)


CASES = [
    case("1\n5\n", "5"),
    case("3\n1 2 3\n", "6"),
    case("2\n-4 -6\n", "-10"),
]


def test_merge_prefixes_the_test_count():
    stdin, _ = merge_cases(CASES)
    assert stdin.splitlines()[0] == "3"


def test_merge_concatenates_blocks_in_order():
    stdin, _ = merge_cases(CASES)
    assert stdin == "3\n1\n5\n3\n1 2 3\n2\n-4 -6\n"


def test_merge_adds_missing_newline_between_blocks():
    stdin, _ = merge_cases([case("1\n5", "5"), case("1\n6", "6")])
    assert stdin == "2\n1\n5\n1\n6\n"


def test_merge_builds_expected_output():
    _, expected = merge_cases(CASES)
    assert expected == "5\n6\n-10"


def test_all_correct():
    split = split_actual("5\n6\n-10\n", CASES)
    assert (split.passed, split.total) == (3, 3)
    assert split.first_failing is None
    assert split.extra_output is False


def test_one_wrong_sub_case_scores_partial():
    split = split_actual("5\n99\n-10\n", CASES)
    assert (split.passed, split.total) == (2, 3)
    failing = split.first_failing
    assert failing.ordinal == 2
    assert failing.expected_stdout == "6"
    assert failing.actual_stdout == "99"


def test_trailing_whitespace_is_forgiven():
    split = split_actual("5  \n6\n-10\n\n\n", CASES)
    assert split.passed == 3


def test_missing_output_fails_the_tail():
    split = split_actual("5\n6\n", CASES)
    assert split.passed == 2
    assert split.results[2].passed is False
    assert split.results[2].actual_stdout == ""
    assert split.missing_output is True


def test_extra_output_is_flagged():
    split = split_actual("5\n6\n-10\nbonus\n", CASES)
    assert split.passed == 3
    assert split.extra_output is True


def test_a_stray_first_line_shifts_and_fails_everything():
    # This is the alignment trap the hint has to explain, not a logic bug.
    split = split_actual("hello\n5\n6\n-10\n", CASES)
    assert split.passed == 0
    assert split.first_failing.ordinal == 1


def test_multi_line_expected_output_consumes_the_right_span():
    multi = [case("1\n", "a\nb"), case("2\n", "c")]
    split = split_actual("a\nb\nc\n", multi)
    assert split.passed == 2
    assert split.results[0].actual_stdout == "a\nb"
    assert split.results[1].actual_stdout == "c"


def test_multi_line_mismatch_is_isolated_to_its_case():
    multi = [case("1\n", "a\nb"), case("2\n", "c")]
    split = split_actual("a\nX\nc\n", multi)
    assert split.results[0].passed is False
    assert split.results[1].passed is True


def test_empty_output_fails_everything():
    split = split_actual("", CASES)
    assert split.passed == 0


def test_rationale_and_kind_survive_the_split():
    tagged = [case("1\n", "5", kind="edge", rationale="empty list")]
    split = split_actual("5\n", tagged)
    assert split.results[0].kind == "edge"
    assert split.results[0].rationale == "empty list"


def test_all_failed_marks_every_sub_case():
    split = all_failed(CASES)
    assert (split.passed, split.total) == (0, 3)
    assert all(not r.passed for r in split.results)


def test_verdicts():
    assert verdict_for("ok", split_actual("5\n6\n-10\n", CASES)) == "Accepted"
    assert verdict_for("ok", split_actual("5\n99\n-10\n", CASES)) == "Wrong answer on test 2"
    assert verdict_for("timeout", all_failed(CASES)) == "Time limit exceeded"
    assert verdict_for("runtime_error", all_failed(CASES)) == "Runtime error"
    assert verdict_for("compile_error", None) == "Compilation error"
    assert verdict_for("memory_exceeded", all_failed(CASES)) == "Memory limit exceeded"


def test_display_statement_prepends_the_batch_convention():
    from app.features.grading.agent.multi_test import MULTI_TEST_PREAMBLE, display_statement

    shown = display_statement("The first line contains an integer n.")
    assert shown.startswith(MULTI_TEST_PREAMBLE)
    assert shown.endswith("The first line contains an integer n.")
    assert "T" in shown


def test_display_statement_passes_through_empty():
    from app.features.grading.agent.multi_test import display_statement

    assert display_statement(None) is None
    assert display_statement("") == ""


def test_a_program_that_prints_nothing_says_so():
    # The uninitialised-loop-counter case: it compiles, runs, and prints nothing.
    # "Wrong answer on test 1" would send the student hunting a logic bug.
    split = split_actual("", CASES)
    assert split.produced_nothing is True
    assert verdict_for("ok", split) == "No output"


def test_partial_output_is_still_a_wrong_answer():
    split = split_actual("5\n6\n", CASES)
    assert split.produced_nothing is False
    assert verdict_for("ok", split) == "Wrong answer on test 3"


def test_a_wrong_first_line_is_not_reported_as_no_output():
    split = split_actual("99\n6\n-10\n", CASES)
    assert split.produced_nothing is False
    assert verdict_for("ok", split) == "Wrong answer on test 1"


def test_crashes_keep_their_own_verdict():
    # all_failed also leaves every actual_stdout empty, but the status wins.
    assert verdict_for("timeout", all_failed(CASES)) == "Time limit exceeded"
    assert verdict_for("runtime_error", all_failed(CASES)) == "Runtime error"


def test_extra_output_is_not_accepted():
    split = split_actual("5\n6\n-10\nextra\n", CASES)
    assert verdict_for("ok", split) == "Wrong answer (extra output)"
