from types import SimpleNamespace

from app.features.practice.logic.assessment import generation
from app.features.practice.logic.assessment.generation import RawCache, generate
from app.features.practice.logic.assessment.parsing import parse_debug, parse_mcqs
from tests.features.practice.assessment.conftest import BUGGY, FIXED, ScriptedProvider

GOOD = """=== QUESTION ===
DIFFICULTY: easy
STEM:
What does this print?
```python
print(len(range(1, 5)))
```
OPTIONS:
A) 5 || off_by_one
B) 4 || correct
C) 3 || wrong_loop_bound
VERIFY:
```python
print(len(range(1, 5)))
```
EXPLANATION: range stops before its end.
=== END ==="""

WRONG_KEY = GOOD.replace("A) 5 || off_by_one", "A) 5 || correct").replace(
    "B) 4 || correct", "B) 4 || none")


def test_parse_mcq_block():
    [item] = parse_mcqs("chatter\n" + GOOD + "\ntrailing")
    assert item["difficulty"] == "easy"
    assert "print(len(range(1, 5)))" in item["stem"]
    assert item["answer_index"] == 1
    assert item["options"][0] == {"text": "5", "misconception": "off_by_one"}
    assert item["options"][1]["misconception"] is None
    assert item["verify_code"] == "print(len(range(1, 5)))"
    assert item["explanation"] == "range stops before its end."


def test_two_correct_marks_make_the_item_invalid():
    doubled = GOOD.replace("A) 5 || off_by_one", "A) 5 || correct")
    assert parse_mcqs(doubled)[0]["answer_index"] == -1


def test_parse_debug_reply():
    reply = f"CORRECT:\n```python\n{FIXED}\n```\nBUGGY:\n```python\n{BUGGY}\n```"
    assert parse_debug(reply) == (FIXED + "\n", BUGGY + "\n")
    assert parse_debug("no fences here") is None


class FakeLLM:
    def __init__(self, reply_for):
        self.reply_for = reply_for
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        return SimpleNamespace(content=self.reply_for(prompt))


def test_generate_keeps_only_executed_items_and_caches_replies(session, bank_problem,
                                                              tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "TOPICS", ("loops",))
    monkeypatch.setattr(generation, "DIAGNOSTIC_TOPICS", ("loops",))
    monkeypatch.setattr(generation, "DEBUG_PLAN", (("dsa-demo", "python", "wrong_initial_value"),))

    def reply(prompt):
        if "debugging exercise" in prompt:
            return f"CORRECT:\n```python\n{FIXED}\n```\nBUGGY:\n```python\n{BUGGY}\n```"
        return GOOD + "\n" + WRONG_KEY

    provider = ScriptedProvider({
        "print(len(range(1, 5)))\n": "4\n", FIXED + "\n": "3\n-4\n", BUGGY + "\n": "3\n0\n",
    })
    llm = FakeLLM(reply)
    cache = RawCache(tmp_path / "raw.json")

    bank = generate(session, cache, runnable=llm, provider=provider)

    assert [m["external_id"] for m in bank["mcqs"]] == ["mcq-loops-1"]
    assert bank["diagnostic"][0]["external_id"] == "diag-loops"
    assert bank["diagnostic"][0]["is_diagnostic"] is True
    assert bank["debug"][0]["external_id"] == "debug-python-dsa-demo"
    assert bank["log"] == {"mcq dropped: stem code": 1}

    calls = llm.calls
    generate(session, RawCache(tmp_path / "raw.json"), runnable=llm, provider=provider)
    assert llm.calls == calls
