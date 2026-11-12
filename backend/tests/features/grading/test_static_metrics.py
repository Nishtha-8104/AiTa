from app.features.grading.agent.static_metrics import find_issues, measure
from app.features.grading.models import Language

SIMPLE = "n = int(input())\nprint(n * 2)\n"

BRANCHY = """
def classify(value):
    if value > 100:
        return "big"
    elif value > 50:
        return "medium"
    elif value > 10:
        return "small"
    elif value > 0:
        return "tiny"
    elif value == 0:
        return "zero"
    else:
        return "negative"
"""

CPP = """
#include <iostream>
// doubles the input
int main() {
    int n;
    std::cin >> n;
    std::cout << n * 2 << std::endl;
    return 0;
}
"""


def test_measures_python_lines_and_complexity():
    metrics = measure(SIMPLE, Language.PYTHON)
    assert metrics.lines_of_code == 2
    assert metrics.cyclomatic_complexity >= 1


def test_branching_raises_cyclomatic_complexity():
    simple = measure(SIMPLE, Language.PYTHON)
    branchy = measure(BRANCHY, Language.PYTHON)
    assert branchy.cyclomatic_complexity > simple.cyclomatic_complexity
    assert branchy.function_count == 1


def test_measures_cpp():
    metrics = measure(CPP, Language.CPP)
    assert metrics.lines_of_code > 0
    assert metrics.function_count == 1


def test_measures_c_complexity():
    code = "int sign(int x) {\n    if (x > 0) return 1;\n    if (x < 0) return -1;\n    return 0;\n}\n"
    metrics = measure(code, Language.C)
    assert metrics.function_count == 1
    assert metrics.cyclomatic_complexity == 3


def test_comment_ratio_counts_language_comment_prefix():
    python_metrics = measure("# a comment\nprint(1)\n", Language.PYTHON)
    assert python_metrics.comment_ratio > 0

    cpp_metrics = measure(CPP, Language.CPP)
    assert cpp_metrics.comment_ratio > 0


def test_non_executable_language_still_measures_lines():
    metrics = measure("class A {}\n// note\n", Language.JAVA)
    assert metrics.lines_of_code == 1
    assert metrics.comment_ratio > 0


def test_simple_correct_code_produces_no_issues():
    metrics = measure(SIMPLE, Language.PYTHON)
    assert find_issues(SIMPLE, Language.PYTHON, metrics) == []


def test_long_line_flagged_once():
    code = "x = " + "1 + " * 60 + "1\n"
    metrics = measure(code, Language.PYTHON)
    issues = find_issues(code, Language.PYTHON, metrics)
    assert sum(1 for i in issues if i.category == "style") == 1


def test_bare_except_flagged():
    code = "try:\n    x = 1\nexcept Exception:\n    pass\n"
    metrics = measure(code, Language.PYTHON)
    issues = find_issues(code, Language.PYTHON, metrics)
    assert any(i.category == "logic" for i in issues)


def test_lowercase_class_name_flagged():
    code = "class myThing:\n    pass\n"
    metrics = measure(code, Language.PYTHON)
    issues = find_issues(code, Language.PYTHON, metrics)
    assert any(i.category == "naming" for i in issues)


def test_todo_marker_flagged():
    code = "# TODO: finish this\nprint(1)\n"
    metrics = measure(code, Language.PYTHON)
    issues = find_issues(code, Language.PYTHON, metrics)
    assert any(i.category == "quality" for i in issues)


def test_high_complexity_flagged():
    metrics = measure(BRANCHY, Language.PYTHON)
    metrics.cyclomatic_complexity = 20
    issues = find_issues(BRANCHY, Language.PYTHON, metrics)
    assert any("complexity" in i.category for i in issues)


def test_no_security_category_remains():
    code = "eval(input())\n"
    metrics = measure(code, Language.PYTHON)
    issues = find_issues(code, Language.PYTHON, metrics)
    assert all(i.category != "security" for i in issues)
