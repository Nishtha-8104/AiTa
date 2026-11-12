from app.features.practice.logic.assessment.sanitize import reveals_bug, strip_bug_annotations

FIXED_PY = "n = int(input())\nfor i in range(2, n + 1):  # every candidate\n    print(i)\n"
BUGGY_PY = ("n = int(input())\nfor i in range(2, n):  # Bug: missing +1, loop stops too early\n"
            "    print(i)\n")


def test_annotation_on_the_bug_line_is_removed():
    cleaned = strip_bug_annotations(BUGGY_PY, FIXED_PY, "python")
    assert cleaned == "n = int(input())\nfor i in range(2, n):\n    print(i)\n"
    assert not reveals_bug(cleaned, FIXED_PY, "python")


def test_shared_comments_are_kept():
    buggy = FIXED_PY.replace("n + 1", "n")
    assert "# every candidate" not in strip_bug_annotations(buggy, FIXED_PY, "python")
    assert strip_bug_annotations(FIXED_PY + "x = 1\n", FIXED_PY, "python").count("# every") == 1


def test_added_comment_only_lines_are_dropped_and_strings_are_safe():
    fixed = 'int main() {\n  cout << "a//b";\n}\n'
    buggy = 'int main() {\n  // BUG: prints the wrong thing\n  cout << "a//c";\n}\n'
    cleaned = strip_bug_annotations(buggy, fixed, "cpp")
    assert cleaned == 'int main() {\n  cout << "a//c";\n}\n'


def test_reveals_bug_only_looks_at_changed_lines():
    fixed = "x = 0  # handle the error case\n"
    buggy = "x = 1  # handle the error case\n"
    assert reveals_bug(buggy, fixed, "python")
    assert not reveals_bug(fixed + "y = 2\n", fixed, "python")
