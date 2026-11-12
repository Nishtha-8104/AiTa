import pytest

from app.core import content
from app.features.grading.models import Language
from app.features.practice.logic.assessment.content import load_practice
from app.features.practice.logic.assessment.verify import verify_debug, verify_mcq
from tests.features.practice.assessment.conftest import (
    BUGGY,
    FIXED,
    ScriptedProvider,
    debug_item,
    mcq,
    standard_provider,
)


def test_mcq_proven_by_execution_passes():
    assert verify_mcq(mcq(), standard_provider()).ok


@pytest.mark.parametrize("overrides, reason", [
    ({"answer_index": 0}, "the correct option carries a misconception tag"),
    ({"topic": "graphs"}, "unknown topic"),
    ({"verify_code": "a = 1\nb = 2\nprint(4)"}, "verify_code must be 1-2 lines"),
    ({"options": [{"text": "4"}, {"text": "4 "}, {"text": "3"}]}, "options must be non-empty and distinct"),
    ({"answer_index": 7}, "answer_index out of range"),
])
def test_mcq_structural_failures(overrides, reason):
    assert verify_mcq(mcq(**overrides), standard_provider()).reason == reason


def test_mcq_whose_key_disagrees_with_execution_is_rejected():
    provider = ScriptedProvider({"print(len(range(1, 5)))": "5\n"})
    check = verify_mcq(mcq(), provider)
    assert not check.ok and "printed '5'" in check.reason


@pytest.mark.parametrize("code", ['print("4")', "print(4)", "x = 4\nprint(x)"])
def test_mcq_whose_verify_code_just_quotes_the_answer_is_rejected(code):
    provider = ScriptedProvider({code: "4\n"})
    assert verify_mcq(mcq(verify_code=code), provider).reason == "verify_code hardcodes the answer"


def test_mcq_with_code_in_the_stem_is_proven_by_that_code():
    stem = "What does this print?\n```python\nage = 17\nprint('adult' if age >= 18 else 'minor')\n```"
    snippet = "age = 17\nprint('adult' if age >= 18 else 'minor')\n"
    item = mcq(stem=stem, verify_code='print("minor")', answer_index=1, options=[
        {"text": "adult", "misconception": "wrong_comparison_operator"},
        {"text": "minor", "misconception": None},
        {"text": "17", "misconception": None},
    ])
    assert verify_mcq(item, ScriptedProvider({snippet: "minor\n"})).ok
    wrong = verify_mcq(item, ScriptedProvider({snippet: "adult\n"}))
    assert wrong.reason == "stem code printed 'adult', key says 'minor'"


def test_silent_stem_code_falls_back_to_verify_code():
    stem = "After this runs, what is x?\n```python\nx = len(range(1, 5))\n```"
    item = mcq(stem=stem)
    provider = ScriptedProvider({"x = len(range(1, 5))\n": "", "print(len(range(1, 5)))": "4\n"})
    assert verify_mcq(item, provider).ok


def test_mcq_whose_verify_code_crashes_is_rejected():
    check = verify_mcq(mcq(verify_code="print(undefined)"), standard_provider())
    assert not check.ok and "did not run cleanly" in check.reason


def test_debug_challenge_proven_both_ways(bank_problem):
    assert verify_debug(debug_item(), bank_problem.test_cases, standard_provider()).ok


def test_debug_rejected_when_the_fix_fails(bank_problem):
    provider = ScriptedProvider({FIXED: "3\n0\n", BUGGY: "3\n0\n"})
    check = verify_debug(debug_item(), bank_problem.test_cases, provider)
    assert check.reason.startswith("fixed code does not pass")


def test_debug_rejected_when_the_bug_is_harmless(bank_problem):
    provider = ScriptedProvider({FIXED: "3\n-4\n", BUGGY: "3\n-4\n"})
    check = verify_debug(debug_item(), bank_problem.test_cases, provider)
    assert check.reason == "buggy code passes every test"


def test_debug_rejects_unknown_language_and_tag(bank_problem):
    provider = standard_provider()
    assert verify_debug(debug_item(language="java"), bank_problem.test_cases, provider).reason \
        == "language must be python, c or cpp"
    assert verify_debug(debug_item(bug_type="typo"), bank_problem.test_cases, provider).reason \
        == "unknown bug_type"


C_PROGRAM = '#include <stdio.h>\nint main(void) { printf("3\\n"); return 0; }\n'
C_STEM = f"What does this program print?\n```c\n{C_PROGRAM}```"
AUTHORED = {
    "problems": [{
        "id": "pet-sum", "title": "Sum of Two", "difficulty": "easy",
        "statement": "Read two integers and print their sum.", "constraints": "small.",
        "reference": {"language": "python", "code": ["print(1)", ""]},
        "tests": [{"input": ["1 2"], "output": ["3"]}, {"input": ["0"], "output": ["0"]}],
    }],
    "mcq": [{
        "id": "mcq-c-loops-1", "language": "c", "difficulty": "easy",
        "stem": content.lines(C_STEM),
        "options": [{"text": "4", "misconception": "off_by_one"},
                    {"text": "3", "misconception": None},
                    {"text": "5", "misconception": None}],
        "answer_index": 1, "explanation": "It prints 3.",
    }, {
        "id": "concept-loops-1", "language": "any", "difficulty": "easy",
        "stem": ["How many times does a loop from 0 while less than 3 run?"],
        "options": [{"text": "3 times", "misconception": None},
                    {"text": "2 times", "misconception": "off_by_one"},
                    {"text": "4 times", "misconception": "off_by_one"}],
        "answer_index": 0, "explanation": "0, 1 and 2.",
    }],
    "debug": [{
        "id": "debug-c-pet-sum", "language": "c", "problem_id": "pet-sum",
        "bug_type": "off_by_one", "fixed_code": ["good", ""], "buggy_code": ["bad", ""],
    }],
}


class LanguageProvider(ScriptedProvider):
    def run_batch(self, language, source, stdins, limits):
        self.calls.append(language)
        return super().run_batch(language, source, stdins, limits)


def test_authored_bank_runs_c_stems_as_c_and_keeps_concepts_code_free(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.CONTENT_DIR", tmp_path)
    for kind, rows in AUTHORED.items():
        content.write("loops", kind, rows)
    bank = load_practice("loops")
    c_item, concept = bank["mcqs"]

    assert [p["external_id"] for p in bank["problems"]] == ["pet-sum"]
    assert [t["kind"] for t in bank["problems"][0]["tests"]] == ["sample", "normal"]
    assert bank["problems"][0]["tests"][1]["stdin"] == "0\n"
    assert bank["problems"][0]["reference"] == "print(1)\n"
    assert c_item["stem"] == C_STEM and c_item["verify_code"] == ""
    assert (c_item["external_id"], c_item["answer_index"]) == ("mcq-c-loops-1", 1)
    assert concept["external_id"] == "concept-loops-1"
    assert bank["debug"] == [{
        "external_id": "debug-c-pet-sum", "problem_external_id": "pet-sum", "language": "c",
        "bug_type": "off_by_one", "fixed_code": "good\n", "buggy_code": "bad\n"}]

    provider = LanguageProvider({C_PROGRAM: "3\n"})
    assert verify_mcq(c_item, provider).ok
    assert Language.C in provider.calls
    assert verify_mcq(concept, None).ok
    assert verify_mcq({**concept, "stem": c_item["stem"]}, None).reason == \
        "a concept question has no code"
    assert verify_mcq({**c_item, "stem": "What does it print?"}, None).reason == \
        "stem needs the whole program"
    python_fence = c_item["stem"].replace("```c", "```python")
    assert verify_mcq({**c_item, "stem": python_fence}, None).reason == \
        "stem code is fenced as 'python', not c"
