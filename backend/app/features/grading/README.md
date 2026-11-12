# grading

Code evaluation. The Code Evaluation Agent runs the student's code in the sandbox against
verified tests, measures it statically, scores it, has the LLM explain the result, builds
the first hint from the failing case, saves everything and reports a learning event. With
no problem statement or a language the sandbox cannot run, it falls back to an unscored
review. The full walk-through is in `agent/README.md`.

## Endpoints

`router.py`, under `/api/v1/code-eval`: `GET /problems`, `GET /problems/{id}`, `POST /run`,
`POST /submit`, `POST /submit/{id}/evaluate`, `POST /evaluate`, `GET /submissions`,
`GET /submissions/{id}`, `DELETE /submissions/{id}`, `GET /stats`.

## Tables

- Writes: `code_submissions`, `code_evaluations`, `eval_history`, `execution_results`;
  `test_cases` through `problems`
- Through `learner_model`: `learning_events`, `topic_mastery`
- Reads: `problems`, `test_cases`, `users`

## Files

```
router.py
service.py                 CodeEvalService: submit, evaluate, list, delete
agent/                     the LangGraph pipeline (see agent/README.md)
logic/execution/           sandbox client: base types, sidecar HTTP provider, run_code, judge
logic/code_eval_stats.py   the stats endpoint
models.py, schemas.py
```

The sandbox itself lives in `backend/executor/`.
