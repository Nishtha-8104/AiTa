"""Bank access and the four code graders, with a fake Sandbox."""

import json

import pytest

from app.core.exceptions import ExecutorUnavailable
from app.features.grading.logic.execution.base import ExecStatus, ExecutionProvider
from app.features.onboarding.logic import bank
from app.features.onboarding.logic.graders import GRADERS
from app.features.onboarding.logic.types import ItemRef
from app.features.onboarding.models import DiagnosticItem
from tests.conftest import FakeExecutionProvider, failing, ok

FILL_CODE = ('#include <stdio.h>\nint main(void) {\n    int n;\n    scanf("%d", &n);\n'
             '    for (int i = 0; i < n; ____) printf("%d ", i);\n    return 0;\n}\n')
BUGGY = 'int n;\nscanf("%d", &n);\nfor (int i = 0; i <= n; i++)\n    printf("%d\\n", i);\n'
FIXED = 'int n;\nscanf("%d", &n);\nfor (int k = 0; k < n; k++)\n    printf("%d\\n", k);\n'
SQUARE_TESTS = [{"stdin": "11", "expected_stdout": "121"}, {"stdin": "12", "expected_stdout": "144"},
                {"stdin": "13", "expected_stdout": "169"}, {"stdin": "14", "expected_stdout": "196"}]

ITEMS = {
    "predict_output": ({"code": 'for (int i = 0; i < 3; i++) printf("%d ", i);'},
                       {"expected_output": "0 1 2\n"}),
    "find_bug": ({"code": BUGGY},
                 {"bug_line": 3, "fixed_code": FIXED,
                  "tests": [{"stdin": "23", "expected_stdout": "zero to twenty-two"}]}),
    "fill_blank": ({"code_with_blank": FILL_CODE, "blank_marker": "____"},
                   {"answer": "i++", "tests": [{"stdin": "37", "expected_stdout": "0 1 2 ... 36"}]}),
    "write_code": ({"statement": "Read n and print its square.", "starter_code": "int square(int n) {\n}\n"},
                   {"reference": "int square(int n) { return n * n; }", "tests": SQUARE_TESTS}),
    "theory": ({"question": "Why does a recursive function need a stopping condition?"},
               {"rubric": ["names the base case", "without it the calls never end",
                           "the stack overflows"],
                "model_answer": "A base case stops the recursion before the call stack runs out."}),
}
BLANK = {"predict_output": {"text": "  \n"}, "find_bug": {"line": None, "fix_code": " "},
         "fill_blank": {"text": ""}, "write_code": {"code": "\n\t"}}


def make(db, kind, language="c", topic="loops", reviewed=True, difficulty="easy"):
    body, key = ITEMS[kind]
    item = DiagnosticItem(external_id=f"{topic}-{kind}-{language}-{reviewed}-{difficulty}",
                          kind=kind, topic=topic, tier=1, difficulty=difficulty, language=language,
                          concept_key="k", body=body, key=key, reviewed=reviewed)
    db.add(item)
    db.commit()
    return item


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for inner in value.values():
            yield from strings(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from strings(inner)


class DownProvider(ExecutionProvider):
    def run_batch(self, language, source, stdins, limits):
        raise ExecutorUnavailable("executor unreachable")


def test_payload_never_contains_key(session):
    for kind in ITEMS:
        item = make(session, kind, language="any" if kind == "theory" else "c")
        payload = bank.payload(item)
        dumped = json.dumps(payload)
        assert "key" not in payload
        assert payload["body"] == item.body
        for secret in strings(item.key):
            assert json.dumps(secret.strip())[1:-1] not in dumped, (kind, secret)


def test_fetch_language_then_any(session):
    make(session, "theory", language="python", topic="recursion", reviewed=False)
    shared = make(session, "theory", language="any", topic="recursion")
    own = make(session, "theory", language="python", topic="recursion", difficulty="medium")
    make(session, "theory", language="any", topic="recursion", difficulty="medium")
    easy = ItemRef("recursion", "theory", "easy", "theory")
    medium = ItemRef("recursion", "theory", "medium", "theory")

    assert bank.fetch(session, easy, "c", set()).id == shared.id
    assert bank.fetch(session, easy, "python", set()).id == shared.id
    assert bank.fetch(session, easy, "c", {shared.id}) is None
    assert bank.fetch(session, medium, "python", set()).id == own.id
    assert ("recursion", "theory", "easy") in bank.bank_index(session, "c")
    with pytest.raises(ValueError):
        bank.fetch(session, easy, "java", set())


def test_predict_output_whitespace_tolerant(session):
    item = make(session, "predict_output")
    grade = GRADERS["predict_output"](item, {"text": "0 1 2"}, None)
    assert (grade.score, grade.graded_by) == (1.0, "key")
    assert grade.reveal["expected"] == "0 1 2\n" and grade.reveal["correct"] is True
    assert GRADERS["predict_output"](item, {"text": "012"}, None).score == 0.0


@pytest.mark.parametrize("line,passes,score", [(3, True, 1.0), (3, False, 0.5), (2, True, 0.5)])
def test_find_bug_line_and_fix(session, line, passes, score):
    item = make(session, "find_bug")
    provider = FakeExecutionProvider([ok("zero to twenty-two\n" if passes else "wrong\n")])
    grade = GRADERS["find_bug"](item, {"line": line, "fix_code": "fixed"}, provider)
    assert (grade.score, grade.graded_by) == (score, "sandbox")
    assert grade.reveal["bug_line"] == 3


def test_fill_blank_substitutes_and_runs(session):
    item = make(session, "fill_blank")
    provider = FakeExecutionProvider([ok("0 1 2 ... 36\n")])
    grade = GRADERS["fill_blank"](item, {"text": "i++"}, provider)
    assert grade.score == 1.0
    assert provider.calls[0]["source"] == FILL_CODE.replace("____", "i++")
    assert provider.calls[0]["stdins"] == ["1\n37\n"]


def test_write_code_pass_rate(session):
    item = make(session, "write_code")
    provider = FakeExecutionProvider([ok("121\n0\n169\n0\n")])
    grade = GRADERS["write_code"](item, {"code": "int square(int n) { return n + n; }"}, provider)
    assert grade.score == 0.5


@pytest.mark.parametrize("kind,answer", [("write_code", {"code": "while (1) {}"}),
                                         ("fill_blank", {"text": "i--"}),
                                         ("find_bug", {"line": 3, "fix_code": "while (1) {}"})])
@pytest.mark.parametrize("status,phrase", [(ExecStatus.TIMEOUT, "timed out"),
                                           (ExecStatus.COMPILE_ERROR, "did not compile")])
def test_timeout_scores_zero_not_skipped(session, kind, answer, status, phrase):
    item = make(session, kind)
    result = failing(status, compile_output="main.c:3: error: expected ';'")
    grade = GRADERS[kind](item, answer, FakeExecutionProvider([result]))
    assert grade.score == (0.5 if kind == "find_bug" else 0.0)
    assert grade.graded_by == "sandbox"
    assert phrase in grade.reveal["why"]
    compiled = status is not ExecStatus.COMPILE_ERROR
    assert grade.reveal.get("compile_output") == (None if compiled else "main.c:3: error: expected ';'")


@pytest.mark.parametrize("kind,answer", [("write_code", {"code": "x"}), ("fill_blank", {"text": "i++"}),
                                         ("find_bug", {"line": 3, "fix_code": "x"})])
def test_executor_down_is_skipped(session, kind, answer):
    grade = GRADERS[kind](make(session, kind), answer, DownProvider())
    assert (grade.score, grade.graded_by) == (None, "skipped")


def test_empty_answers_score_zero_without_calls(session):
    provider = FakeExecutionProvider([ok("")])
    for kind, answer in BLANK.items():
        grade = GRADERS[kind](make(session, kind), answer, provider)
        assert grade.score == 0.0, kind
        assert "yours" not in grade.reveal["why"], kind
    assert provider.calls == []
