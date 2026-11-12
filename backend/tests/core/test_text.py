from app.core.text import normalize_output, normalize_statement, statement_hash, truncate


def test_trailing_newline_does_not_change_output():
    assert normalize_output("6\n") == normalize_output("6")


def test_trailing_blank_lines_dropped():
    assert normalize_output("1\n2\n\n\n") == "1\n2"


def test_trailing_spaces_per_line_stripped():
    assert normalize_output("a   \nb\t\n") == "a\nb"


def test_crlf_treated_as_newline():
    assert normalize_output("1\r\n2\r\n") == "1\n2"


def test_interior_blank_lines_preserved():
    assert normalize_output("a\n\nb") == "a\n\nb"


def test_empty_input():
    assert normalize_output("") == ""
    assert normalize_output("\n\n") == ""


def test_statement_hash_stable_across_whitespace():
    a = statement_hash("Print the  sum\nof two numbers.")
    b = statement_hash("print the sum of two numbers.")
    assert a == b
    assert len(a) == 64


def test_statement_hash_differs_on_content():
    assert statement_hash("sum two numbers") != statement_hash("sum three numbers")


def test_normalize_statement_collapses_whitespace():
    assert normalize_statement("  Read   N\n then print  ") == "read n then print"


def test_truncate_under_limit_untouched():
    text, was_truncated = truncate("hello", 1)
    assert text == "hello"
    assert was_truncated is False


def test_truncate_over_limit_flags():
    text, was_truncated = truncate("x" * 3000, 1)
    assert was_truncated is True
    assert len(text.encode("utf-8")) <= 1024


def test_truncate_does_not_split_multibyte():
    text, was_truncated = truncate("é" * 2000, 1)
    assert was_truncated is True
    text.encode("utf-8")
