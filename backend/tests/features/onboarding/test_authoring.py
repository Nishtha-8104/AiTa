"""Offline diagnostic-bank authoring: parsing, verification by execution, and loading."""

import copy
from collections import Counter

import pytest

from app.features.grading.logic.execution.base import ExecStatus
from app.features.onboarding.logic.authoring import build, parse, verify
from app.features.onboarding.models import DiagnosticItem, DiagnosticResponse
from app.features.practice.logic.assessment.generation import RawCache
from scripts.seed.seed_diagnostic import load
from scripts.tools.review_diagnostic import reject
from tests.conftest import FakeExecutionProvider, failing, ok

DRAFT = """Here are the items.
=== ITEM ===
KIND: predict_output
DIFFICULTY: easy
CODE:
```python
print(1 + 2)
```
EXPECTED_OUTPUT:
```text
3
```
=== END ===
=== ITEM ===
KIND: essay
DIFFICULTY: easy
=== END ===
"""

PORT = """=== PORT ===
CONCEPT: basics_io:1
LANGUAGE: C
CODE:
```c
#include <stdio.h>
int main(void) { printf("%d\\n", 1 + 2); return 0; }
EXPECTED_OUTPUT:
```text
3
```
=== END ===
"""

LOOP_DRAFT = """=== ITEM ===
KIND: find_bug
DIFFICULTY: medium
STATEMENT: Read n and print 0 + 1 + ... + n.
FIXED:
```python
t = int(input())
for _ in range(t):
    n = int(input())
    print(sum(range(n + 1)))
```
CHANGE_FROM: `print(sum(range(n + 1)))`
CHANGE_TO: `print(sum(range(n)))`
TESTS:
### input
3
### output
6
### input
1
### output
1
=== END ===
=== ITEM ===
KIND: theory
DIFFICULTY: medium
LANGUAGE_SPECIFIC: no
QUESTION: Why does a loop need a condition that eventually becomes false?
RUBRIC:
- the loop stops when the condition is false
- otherwise it runs forever
- the body must change what the condition tests
MODEL_ANSWER: The body must move the condition towards false, or the loop never ends.
"""

FIXED_C = """#include <stdio.h>
int main(void) {
    int t, n;
    scanf("%d", &t);
    while (t--) { scanf("%d", &n); int s = 0; for (int i = 0; i <= n; i++) s += i; printf("%d\\n", s); }
    return 0;
}
"""

LOOP_PORT = f"""=== PORT ===
CONCEPT: loops:1
KIND: find_bug
LANGUAGE: c
FIXED:
```c
...code...
```
CHANGE_FROM: ...
CHANGE_TO: ...
=== END ===
=== PORT ===
CONCEPT: loops:1
KIND: find_bug
LANGUAGE: c
FIXED:
```c
{FIXED_C}```
CHANGE_FROM: while (t--) {{ scanf("%d", &n); int s = 0; for (int i = 0; i <= n; i++) s += i; printf("%d\\n", s); }}
CHANGE_TO: while (t--) {{ scanf("%d", &n); int s = 0; for (int i = 0; i < n; i++) s += i; printf("%d\\n", s); }}
=== END ===
=== PORT ===
CONCEPT: loops:1
KIND: predict_output
LANGUAGE: C++
CODE:
```cpp
int main() {{ return 0; }}
```
=== END ===
"""

TESTS = [{"stdin": "3", "expected_stdout": "6"}, {"stdin": "1", "expected_stdout": "1"}]
FIXED = "t = int(input())\nfor _ in range(t):\n    n = int(input())\n    print(sum(range(n + 1)))\n"
BUGGY = FIXED.replace("n + 1", "n")
FILL = ("t = int(input())\nfor _ in range(t):\n    n = int(input())\n"
        "    print(sum(range(____)))\n")


class ByCode(FakeExecutionProvider):
    """One result per program text, so a fixed and a buggy program can disagree."""

    def __init__(self, by_source: dict, default):
        super().__init__([default])
        self.by_source = by_source

    def run_batch(self, language, source, stdins, limits):
        self.calls.append({"language": language, "source": source, "stdins": list(stdins)})
        return [self.by_source.get(source, self.results[0])] * len(stdins)


def code_item(kind, body, key, language="python"):
    return {"concept_key": "loops:1", "topic": "loops", "tier": 2, "kind": kind,
            "difficulty": "medium", "language": language, "body": body, "key": key}


def find_bug_item(code, bug_line):
    return code_item("find_bug", {"statement": "Print 0 + 1 + ... + n.", "code": code},
                     {"bug_line": bug_line, "fixed_code": FIXED, "tests": TESTS})


def test_predict_output_stores_real_output(tmp_path):
    prompts_seen = []

    def ask(prompt):
        prompts_seen.append(prompt)
        if "Basics & I/O" not in prompt:
            return ""
        return PORT if "=== PORT ===" in prompt else DRAFT

    provider = FakeExecutionProvider([ok("4\n"), ok("4\n")])
    result = build.generate(RawCache(tmp_path / "raw.json"), provider, ask=ask)

    assert [i["language"] for i in result["items"]] == ["python", "c"]
    assert result["items"][1]["body"]["code"].endswith("return 0; }\n")
    assert all(i["key"]["expected_output"] == "4" for i in result["items"])
    assert {i["concept_key"] for i in result["items"]} == {"basics_io:1"}
    assert result["log"]["mismatch_fixed"] == 2
    assert result["log"]["unknown_kind"] == 1
    assert len(prompts_seen) == 13


def test_predict_output_rejects_nondeterministic():
    item = code_item("predict_output", {"code": "print({'b', 'a'})"}, {"expected_output": ""})
    check = verify.check(item, FakeExecutionProvider([ok("{'a', 'b'}\n"), ok("{'b', 'a'}\n")]))
    assert (check.ok, check.reason) == (False, "nondeterministic")


@pytest.mark.parametrize("buggy,bug_line,reason", [
    (BUGGY, 3, "bug_line_mismatch"),
    (BUGGY, 4, ""),
    (BUGGY.replace("t = int(input())", "t = int(input())   "), 4, ""),
    (BUGGY.replace("range(t)", "range(t + 0)"), 4, "bug_line_mismatch"),
])
def test_find_bug_rejects_wrong_line(buggy, bug_line, reason):
    provider = ByCode({FIXED: ok("6\n1\n")}, ok("3\n0\n"))
    check = verify.check(find_bug_item(buggy, bug_line), provider)
    assert (check.ok, check.reason) == (not reason, reason)


def test_find_bug_rejects_when_buggy_passes():
    provider = FakeExecutionProvider([ok("6\n1\n")])
    check = verify.check(find_bug_item(BUGGY, 4), provider)
    assert (check.ok, check.reason) == (False, "buggy_passes")
    assert provider.calls[0]["stdins"] == ["2\n3\n1\n"]


def test_fill_blank_rejects_blank_not_needed():
    item = code_item("fill_blank", {"code_with_blank": FILL, "blank_marker": "____"},
                     {"answer": "n + 1", "tests": TESTS})
    completed = FILL.replace("____", "n + 1")

    check = verify.check(item, FakeExecutionProvider([ok("6\n1\n")]))
    assert (check.ok, check.reason) == (False, "blank_not_required")

    provider = ByCode({completed: ok("6\n1\n")}, failing(ExecStatus.RUNTIME_ERROR))
    assert verify.check(item, provider).ok
    assert provider.calls[1]["source"] == FILL.replace("____", "")

    twice = copy.deepcopy(item)
    twice["body"]["code_with_blank"] = FILL + "# ____\n"
    assert verify.check(twice, provider).reason == "marker_count"

    item["key"]["tests"] = TESTS[:1]
    assert verify.check(item, provider).reason == "too_few_tests"


@pytest.mark.parametrize("reference_out,starter,reason", [
    ("6\n1\n10\n", ok("0\n0\n0\n"), ""),
    ("6\n1\n9\n", ok("0\n0\n0\n"), "reference_fails"),
    ("6\n1\n10\n", ok("6\n1\n10\n"), "starter_passes"),
    ("6\n1\n10\n", failing(ExecStatus.COMPILE_ERROR), "starter_does_not_compile"),
])
def test_write_code_reference_must_pass(reference_out, starter, reason):
    tests = TESTS + [{"stdin": "4", "expected_stdout": "10"}]
    item = code_item("write_code", {"statement": "Print 0 + 1 + ... + n.", "starter_code": "x"},
                     {"reference": FIXED, "tests": tests})

    check = verify.check(item, ByCode({FIXED: ok(reference_out)}, starter))
    assert (check.ok, check.reason) == (not reason, reason)
    item["key"]["tests"] = TESTS
    assert verify.check(item, ByCode({}, ok(""))).reason == "too_few_tests"


def test_empty_expected_output_rejected():
    draft = """=== ITEM ===
KIND: write_code
DIFFICULTY: medium
STATEMENT: Print n.
STARTER:
```python
x
```
REFERENCE:
```python
y
```
TESTS:
```text
###  Input:
3
### OUTPUT :
3
### input
4
### output:
### input
5
### output
5
```
=== END ===
"""
    [item] = parse.parse_topic_draft(draft, "loops")
    assert item["key"]["tests"] == [{"stdin": "3", "expected_stdout": "3"},
                                    {"stdin": "4", "expected_stdout": ""},
                                    {"stdin": "5", "expected_stdout": "5"}]
    check = verify.check(item, FakeExecutionProvider([ok("")]))
    assert (check.ok, check.reason) == (False, "empty_expected")


@pytest.mark.parametrize("points,passes", [(2, False), (3, True), (4, True), (5, False)])
def test_theory_rubric_size(points, passes):
    item = {**code_item("theory", {"question": "Why?"},
                        {"rubric": [f"point {n}" for n in range(points)],
                         "model_answer": "Because."}), "language": "any"}
    check = verify.check(item, None)
    assert check.ok is passes
    assert check.reason == ("" if passes else "rubric_size")


def test_find_bug_planted_from_one_changed_line():
    items = parse.parse_topic_draft(LOOP_DRAFT, "loops")
    assert [(i["kind"], i["language"], i["concept_key"]) for i in items] == [
        ("find_bug", "python", "loops:1"), ("theory", "python", "loops:2")]
    assert items[0]["key"]["tests"] == TESTS
    assert (items[0]["body"]["code"], items[0]["key"]["bug_line"]) == (BUGGY, 4)

    line = "    print(sum(range(n + 1)))\n"
    [unplanted, _] = parse.parse_topic_draft(LOOP_DRAFT.replace(line, line * 2, 1), "loops")
    assert verify.check(unplanted, None).reason == "bug_not_planted"


def test_port_keeps_first_verified_candidate():
    items = parse.parse_topic_draft(LOOP_DRAFT, "loops")
    ported = parse.parse_port(LOOP_PORT, items)
    assert len(ported["c"]) == 2 and ported["cpp"] == []

    provider = ByCode({FIXED_C: ok("6\n1\n")}, ok("3\n0\n"))
    [c] = build.keep_verified(ported["c"] * 2, provider, Counter())
    assert (c["concept_key"], c["language"], c["tier"], c["key"]["bug_line"]) == ("loops:1", "c", 2, 5)
    assert c["key"]["tests"] == items[0]["key"]["tests"]
    assert c["body"]["statement"] == items[0]["body"]["statement"]
    assert "i < n;" in c["body"]["code"]


def test_load_upserts_and_keeps_review(session):
    items = [code_item("predict_output", {"code": "print(4)"}, {"expected_output": "4"}, lang)
             for lang in ("python", "c", "cpp")]

    assert load(session, items)["inserted"] == 3
    rows = {r.language: r for r in session.query(DiagnosticItem)}
    rows["python"].reviewed = rows["c"].reviewed = True
    session.commit()

    items[1]["body"] = {"code": 'printf("4");'}
    items[2]["key"] = {"expected_output": "5"}
    report = load(session, items)
    assert report == {"unchanged": 1, "updated_was_reviewed": 1, "updated": 1}
    assert session.query(DiagnosticItem).count() == 3
    for row in rows.values():
        session.refresh(row)
    assert rows["python"].reviewed is True
    assert rows["c"].reviewed is False and rows["c"].body == {"code": 'printf("4");'}
    assert rows["cpp"].reviewed is False and rows["cpp"].key == {"expected_output": "5"}


def test_reject_deletes_only_unreviewed_unanswered(session):
    load(session, [code_item("theory", {"question": "q"}, {"rubric": [], "model_answer": "a"},
                             lang) for lang in ("python", "c", "cpp")])
    rows = {r.language: r for r in session.query(DiagnosticItem)}
    rows["python"].reviewed = True
    session.add(DiagnosticResponse(user_id=1, item_id=rows["c"].id, order=1, phase="theory",
                                   language="c", answer={}, graded_by="llm", ms_taken=1))
    session.commit()
    ids = [rows["python"].id, rows["c"].id, rows["cpp"].id]

    deleted, refused = reject(session, ids + [999])

    assert deleted == [rows["cpp"].id]
    assert refused == {ids[0]: "reviewed", ids[1]: "answered", 999: "not found"}
    assert {r.language for r in session.query(DiagnosticItem)} == {"python", "c"}
