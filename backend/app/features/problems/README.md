# problems

Coding problems and their tests. Serves a problem from the curated bank when one fits the
topic and difficulty, otherwise asks the LLM for a new one and keeps it only if test cases
can be verified for it. Test cases come from the problem's own samples, curated cases, or
LLM cases cross-checked against a reference solution in the sandbox. After a pass or a
give-up, the model answer can be revealed (ported to C or C++ when needed).

## Endpoints

`router.py`, under `/api/v1/problems`: `POST /generate`, `POST /{problem_id}/solution`.
The bank list and single-problem view are served by `grading` under `/api/v1/code-eval`.

## Tables

- Writes: `problems`, `problem_references`, `test_cases`, `execution_results`
  (bank loaded by `scripts/seed/ingest_problems.py`)
- Through `learner_model`: `learning_events` (a give-up is recorded)
- Reads: `code_evaluations`

## Files

```
router.py
service.py                 get_or_create_problem(), find by statement, has_test_cases
logic/picker.py            choose a bank problem for topic + difficulty
logic/listing.py           bank listing
logic/generation.py        LLM problem generation
logic/test_generation/     curated_tests.py, generate_tests.py (cross-checked LLM cases)
logic/sample_run.py        run code against the shown example
logic/solution.py          reveal the model answer
models.py, schemas.py, logic/schemas.py
```
