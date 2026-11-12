"""Prompts for drafting the diagnostic bank: one draft call per topic in Python, one port
call per topic into C and C++."""

from app.core.topics import TOPIC_LABELS
from app.features.onboarding.logic.authoring.parse import FIELDS, TOPICS
from app.features.onboarding.logic.walk import WRITE_TOPICS

MEDIUM_KINDS = (("find_bug", "fill_blank"), ("predict_output", "find_bug"),
                ("fill_blank", "predict_output"))

TESTS_SHAPE = """```text
### input
<ONE test case's input, without T>
### output
<exactly what the program prints for it>
### input
...
```"""

FORMATS = {
    "predict_output": """CODE:
```{fence}
<the program>
```
EXPECTED_OUTPUT:
```text
<exactly what it prints>
```""",
    "find_bug": """FIXED:
```{fence}
<the correct program>
```
CHANGE_FROM: <one line of FIXED, copied exactly>
CHANGE_TO: <that line with the mistake planted>""",
    "fill_blank": """CODE:
```{fence}
<the program with exactly one ____>
```
ANSWER: <the exact text that replaces ____>""",
    "write_code": """STARTER:
```{fence}
<the complete program with the function body left as a stub>
```
REFERENCE:
```{fence}
<the same program with the function written>
```""",
    "theory": """QUESTION: <the question>
RUBRIC:
- <key point>
- <key point>
- <key point>
MODEL_ANSWER: <a 1-3 sentence answer containing every key point>""",
}

KIND_RULES = """- predict_output: a short complete program (at most 12 lines) that reads NO input and
  prints 1-5 short lines. The student reads it and types the exact output, so trace it
  carefully. The output must be the same on every run: never print or loop over an
  unordered container (a set, or a dict built from hashed keys; unordered_set or
  unordered_map in C++), and use no randomness, time, memory addresses or undefined
  behaviour.
- find_bug: STATEMENT says in one sentence what the program should do for ONE test case
  (what it reads and what it prints), without hinting at the mistake. Then a correct
  program (FIXED), then ONE line of it (CHANGE_FROM, copied exactly
  and appearing only once in FIXED) and the same line rewritten with a typical beginner
  mistake for this topic (CHANGE_TO, which must differ from CHANGE_FROM). With that one
  line replaced, the program still compiles and runs but prints a wrong answer on at
  least one test. The changed line is never the code that reads T or loops over the
  test cases.
- fill_blank: a correct program with exactly one piece replaced by ____ (four
  underscores): a token, an expression or a whole line that this topic is about. ANSWER
  is the exact text that goes in its place, and the program must not work without it.
  The blank is never in the code that reads T or loops over the test cases.
- write_code: STATEMENT asks for ONE small function (a 3-6 line body) and describes the
  input and output of ONE test case. STARTER is the complete program with the input loop
  already written and the function body left as a stub (`pass`, or a placeholder
  return); REFERENCE is the same program with the function written. At least 3 tests.
- theory: a question answered in 1-3 sentences that checks understanding, not recall.
  RUBRIC lists 3 or 4 key points a good answer contains, one per line."""

INPUT_RULES = """HOW PROGRAMS READ INPUT
Every find_bug, fill_blank and write_code program is a complete program judged on
standard input and output. It first reads one integer T, the number of test cases, then
reads T test cases and prints the answer for each one, in order. Each test input in TESTS
is ONE test case only: never write T in it, the judge adds it. A test case's input and
output may span several lines, and every test case prints at least one non-empty line.
No input line is empty or only spaces: the C and C++ versions read words with scanf and
cin, which skip blank lines."""

DRAFT_PROMPT = """You write items for a short placement test that finds out what a beginner
programmer can already do.

TOPIC: {topic_label}
LANGUAGE: Python 3

Write exactly these items, in this order:
{plan}

{input_rules}

THE KINDS
{kind_rules}

Write no comments in any program. Give every find_bug, fill_blank and write_code item
3-5 tests, including one edge case.

OUTPUT FORMAT
For each item output exactly one block like this and nothing else:

=== ITEM ===
KIND: <kind>
DIFFICULTY: easy | medium
<the sections for that kind, exactly as shown below>
=== END ===

predict_output sections:
{predict_output}

find_bug sections:
STATEMENT: <what the program should do>
{find_bug}
TESTS:
{tests}

fill_blank sections:
{fill_blank}
TESTS:
{tests}

write_code sections:
STATEMENT: <the task>
{write_code}
TESTS:
{tests}

theory sections:
{theory}
"""

PORT_PROMPT = """You port placement-test items for beginner programmers from Python 3 to C
(C11) and C++ (C++17).

TOPIC: {topic_label}

Port EVERY item below into BOTH C and C++. A port must behave exactly like the Python
program: for the same input it prints exactly the same output, character for character
(watch spaces, number formats and newlines). The tests and the find_bug and write_code
statements are shared with the Python item and are not repeated.

{input_rules}

Use only the standard library and write simple code a beginner would write. Write no
comments. Every port is a complete, real program: never a placeholder.
- predict_output: port CODE; EXPECTED_OUTPUT is what your port prints. Like the Python
  program it reads NO input (no T, no scanf, no cin). It must print the same on every
  run: no unordered_set or unordered_map, randomness, time, memory addresses or
  undefined behaviour.
- find_bug: port FIXED, then CHANGE_FROM is one line of YOUR port (copied exactly,
  appearing only once) and CHANGE_TO is that line with the same mistake planted.
- fill_blank: port CODE keeping exactly one ____ in the equivalent place; ANSWER is the
  text for the blank in that language.
- write_code: port STARTER (function body left as a stub that compiles) and REFERENCE.
- theory: rewrite QUESTION, RUBRIC (3 or 4 points) and MODEL_ANSWER for that language:
  a student who only knows C (or C++) must be able to answer it, so it never mentions
  Python, and any Python feature it asks about becomes that language's equivalent.

ITEMS
{items}

OUTPUT FORMAT
For every item and each of the two languages, output exactly one block like this and
nothing else. Copy CONCEPT and KIND from the item; the sections depend on KIND.

=== PORT ===
CONCEPT: <the item's CONCEPT>
KIND: <the item's KIND>
LANGUAGE: c | cpp
<the sections for that kind, exactly as shown below>
=== END ===

predict_output sections:
{predict_output}

find_bug sections:
{find_bug}

fill_blank sections:
{fill_blank}

write_code sections:
{write_code}

theory sections:
{theory}
"""


def _plan(topic: str) -> str:
    medium = MEDIUM_KINDS[TOPICS.index(topic) % len(MEDIUM_KINDS)]
    lines = ["easy predict_output", f"medium {medium[0]}", f"medium {medium[1]}",
             "medium theory"]
    if topic in WRITE_TOPICS:
        lines.append("medium write_code")
    return "\n".join(f"{n}. {line}" for n, line in enumerate(lines, 1))


def draft(topic: str) -> str:
    shapes = {kind: shape.format(fence="python") for kind, shape in FORMATS.items()}
    return DRAFT_PROMPT.format(topic_label=TOPIC_LABELS[topic], plan=_plan(topic),
                               input_rules=INPUT_RULES, kind_rules=KIND_RULES,
                               tests=TESTS_SHAPE, **shapes)


def _render_value(form: str, value) -> str:
    if form == "code":
        return f"\n```python\n{value.rstrip()}\n```"
    if form == "output":
        return f"\n```text\n{value.rstrip()}\n```"
    if form == "list":
        return "".join(f"\n- {point}" for point in value)
    if form == "tests":
        cases = "".join(f"### input\n{t['stdin']}\n### output\n{t['expected_stdout']}\n"
                        for t in value)
        return f"\n```text\n{cases}```"
    return f" {value}"


def render(item: dict) -> str:
    lines = ["=== ITEM ===", f"CONCEPT: {item['concept_key']}", f"KIND: {item['kind']}"]
    for label, part, name, form in FIELDS[item["kind"]]:
        lines.append(f"{label}:{_render_value(form, item[part][name])}")
    lines.append("=== END ===")
    return "\n".join(lines)


def port(topic: str, items: list[dict]) -> str:
    shapes = {kind: shape.format(fence="c or cpp") for kind, shape in FORMATS.items()}
    return PORT_PROMPT.format(topic_label=TOPIC_LABELS[topic], input_rules=INPUT_RULES,
                              items="\n\n".join(render(item) for item in items), **shapes)
