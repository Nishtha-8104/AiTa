MCQ_PROMPT = """You write multiple-choice questions for beginner programmers learning Python.

TOPIC: {topic_label}
Write {count} questions. Difficulty mix: {difficulties}.

EVERY question must be answerable by running a tiny piece of Python: ask what a short
snippet prints, or what value an expression has. The distractors must be the answers a
student would give if they held a specific misconception.

MISCONCEPTION TAGS (use exactly one per wrong option, or "none"):
{tags}

For each question, output EXACTLY this block and nothing else:

=== QUESTION ===
DIFFICULTY: easy | medium | hard
STEM:
<the question; put any code in a ```python fenced block```>
OPTIONS:
A) <exact output or value> || correct
B) <exact output or value> || <misconception tag or none>
C) <exact output or value> || <misconception tag or none>
D) <exact output or value> || <misconception tag or none>
VERIFY:
```python
<one or two lines of Python that PRINT exactly the correct option's text>
```
EXPLANATION: <one sentence on why the correct answer is right>
=== END ===

Rules:
- Exactly one option is marked "correct"; put it in a random position, not always A.
- Option text must be exactly what Python prints, e.g. 4 or [1, 2] or True or 'ab' printed as ab.
- VERIFY must be at most two lines and must print exactly the correct option's text.
- Options must all be different from each other.
"""

DEBUG_PROMPT = """You write a debugging exercise for a beginner programmer.

PROBLEM (the program is judged on stdin/stdout):
{statement}

CONSTRAINTS:
{constraints}

LANGUAGE: {language}
THE BUG TO PLANT: {bug_type} - {bug_description}

Step 1. Write a complete, correct {language} program that solves the problem exactly as
stated, reading from standard input and printing to standard output. Write it the way a
careful student would: simple, readable, no clever tricks.

Step 2. Copy that program and change as little as possible - one or two lines - to plant
exactly the bug above. The buggy program must still compile and run, and must give a
wrong answer on at least one valid input. Do NOT add or change any comment in the buggy
program: nothing in it may point at, name or explain the bug.

Output EXACTLY this and nothing else:

CORRECT:
```{fence}
<the correct program>
```
BUGGY:
```{fence}
<the buggy program>
```
"""

BUG_DESCRIPTIONS = {
    "off_by_one": "a loop or index is off by exactly one",
    "empty_input_unhandled": "a case with zero elements or an empty string is mishandled",
    "wrong_initial_value": "an accumulator or best-so-far starts at the wrong value",
    "wrong_comparison_operator": "< and <= (or > and >=) are swapped",
    "integer_division": "integer division is used where true division, or the reverse, is needed",
    "missing_base_case": "a recursive function lacks a base case or has the wrong one",
    "mutate_while_iterating": "a collection is modified while it is being iterated",
    "uninitialised_variable": "a variable is used before it is reset for each test case",
    "wrong_loop_bound": "a loop stops too early or runs too far",
    "return_vs_print": "a value is returned or printed in the wrong place or format",
    "index_out_of_range": "an index can go past the end of a sequence",
    "infinite_loop": "a loop's exit condition can never become true for some input",
}
