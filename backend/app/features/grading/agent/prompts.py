"""Prompt templates: test-case generation, reference-solution retry, porting a solution to
C/C++, and the student-facing explanation with its failure and crash blocks."""

from app.core.topics import MISCONCEPTIONS

TEST_GENERATION_PROMPT = """You prepare test cases for a beginner programming exercise.

PROBLEM STATEMENT (this describes ONE test case):
{statement}

CONSTRAINTS:
{constraints}

INPUT FORMAT THE SOLUTION MUST HANDLE:
The program reads an integer T on the very first line, the number of test cases.
T test case blocks follow, each in the format described by the problem statement.
The program prints the answer for every block, in order.

Produce two things.

1. A reference solution: a complete, correct Python 3 program that reads T from the
   first line, loops T times reading one block per iteration, and prints each answer.
   No imports of unavailable packages, no argument parsing, no prompt text printed.
   It must run unchanged.

2. Exactly {count} test cases covering the problem.
   - Each case's `stdin` is ONE BLOCK ONLY. Do NOT put the test count T inside it.
     The blocks are concatenated behind a single T line by the grader.
   - Each case's `expected_stdout` is the output for that one block only.
   - Mark a case "normal" for a typical input drawn from the constraints.
   - Mark a case "edge" for boundary behaviour. Include as many of these as the
     problem admits: the smallest legal input, a single element, all elements
     identical, the minimum and maximum permitted values, negative numbers,
     duplicate values.
   - Do not produce very large inputs. Nothing above a few hundred elements.

Rules for stdin and expected_stdout:
   - Write real newline characters. Never write a backslash followed by the letter n.
   - End every `stdin` block with a newline.
   - expected_stdout must be exactly what the reference prints for that one block,
     with no leading or trailing blank lines.
   - Give every case a one-sentence rationale explaining what it checks.
"""

REFERENCE_RETRY_PROMPT = """Your previous reference solution for this problem was wrong.

PROBLEM STATEMENT (this describes ONE test case):
{statement}

PREVIOUS ATTEMPT:
{previous}

WHAT WENT WRONG:
{failure}

Write a corrected reference solution and a fresh set of test cases.

The solution must read an integer T on the first line, loop T times reading one test
case block per iteration, and print each answer in order. It must run unchanged.

Each test case's `stdin` is ONE BLOCK ONLY, without the T line, ending in a newline.
Use real newline characters, never a backslash followed by the letter n.
"""

SOLUTION_PORT_PROMPT = """Translate this correct Python 3 program into {language_name}.
A beginner who just gave up on the problem will read your version as the model answer.

PROBLEM STATEMENT (this describes ONE test case):
{statement}

CORRECT PYTHON PROGRAM:
{reference}

Rules:
- Keep the exact input and output behaviour. The program reads an integer T on the first
  line, then T test case blocks, and prints the answer for every block, in order.
- {language_rules}
- Plain, readable code a beginner can follow: clear names, no clever tricks, short
  comments only where a step is not obvious.
- No prompt text, no extra output, no argument parsing. It must compile and run unchanged.
- Write real newline characters in `code`. Never write a backslash followed by the letter n
  as a line break.
"""

SOLUTION_PORT_RETRY = """

Your previous version failed: {failure}
Previous version:
{previous}
"""

EXPLANATION_PROMPT = """You are the Code Evaluation Agent inside PET, an AI teaching
assistant for beginner programmers who have no human teaching assistant available.

STUDENT SKILL LEVEL: {skill_level}
STUDENT PREFERENCES: {style}
LANGUAGE: {language}

THE STUDENT'S CODE:
```{language}
{code}
```

MEASURED RESULT: {tests_passed} of {tests_total} test cases passed.

{failure_block}

STATIC ANALYSIS FOUND:
{issues}

Your job is to explain what went wrong and teach, without ever handing over the answer.

ABSOLUTE RULES:
1. Never write a corrected version of the student's code.
2. Never write a complete working solution, in any language, in any form.
3. Never write more than two lines of code in any single example, and only to
   illustrate a concept in the abstract, never applied to this problem.
4. Point at the failing input and ask what the code does with it. Let the student
   find the fix.
5. If every test passed, say so plainly and discuss quality, not correctness.

Estimate the time and space complexity of the student's code in Big-O notation.
Be encouraging and specific. Never demotivating.

MISCONCEPTION TAGS: """ + ", ".join(MISCONCEPTIONS) + """
If any test failed, put in `misconceptions` the one or two tags from that list that best
explain the failures, using the exact tag text. Use none of them if none fit. If every
test passed, leave `misconceptions` empty.
"""

NO_FAILURE_BLOCK = "Every test case passed. There is no failing case to discuss."

FAILURE_BLOCK = """VERDICT: {verdict}

THE SUB-CASES THAT FAILED ({failed_count} of {total_count}):
{failed_summary}

THE FIRST ONE IN DETAIL:
  input:    {stdin}
  expected: {expected}
  produced: {actual}
  this case checks: {rationale}
{alignment_note}
Look across ALL the failing sub-cases above and name what they have in common — a
kind of input the code mishandles, not one isolated value. If they share nothing,
say that instead of inventing a pattern.
"""

ALIGNMENT_NOTE = """
IMPORTANT: the program printed {problem}. Every sub-case after the first mismatch is
therefore misaligned and counted wrong. Tell the student to check how many lines they
print per test case before they go looking for a logic error.
"""

CRASH_BLOCK = """VERDICT: {verdict}

The program did not finish. All {total_count} sub-cases are counted as failed because
execution stopped partway through the batch, not because every answer was wrong.

{stderr_block}
Explain what this kind of failure usually means and where to look. Do not guess at a
specific line unless the error names one.
"""
