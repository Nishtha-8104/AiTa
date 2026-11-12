# practice

Day-to-day practice. The Assessment Agent picks what to practise next and says why
(multiple-choice, debugging challenge, coding problem or theory question), grades MCQ and
debug answers, and hands coding problems to `grading`. Practice sessions group a stretch of
graded answers and end with a short wrap-up and feedback. Topic practice is a run of items
on one chosen topic, with a written explanation of that topic.

## Endpoints

| Router | Prefix | Endpoints |
|---|---|---|
| `router_assessment.py` | `/api/v1/assessment` | `GET /next`, `POST /mcq/{id}/answer`, `POST /debug/{id}/submit` |
| `router_sessions.py` | `/api/v1/practice-sessions` | `GET /current`, `GET /pending`, `POST /{id}/finish`, `GET /{id}`, `POST /{id}/feedback` |
| `router_topic_practice.py` | `/api/v1/topic-practice` | `GET /next`, `POST /theory/{id}/answer`, `GET /{topic}/explanation`, `POST /{topic}/start` |

## Tables

- Writes: `practice_sessions`, `mcq_attempts`, `debug_attempts`, `theory_attempts`;
  the banks `mcq_questions`, `debug_challenges`, `theory_questions` are loaded by
  `scripts/seed/`
- Through `learner_model`: `learning_events`, `topic_mastery`
- Reads: `topic_mastery`, `problems`, `test_cases`, `hint_events`, `code_evaluations`

## Files

```
router_assessment.py, router_sessions.py, router_topic_practice.py
service.py                  practice-session lifecycle (open, close on idle or language switch)
agent/graph.py              Assessment Agent: next_item()
logic/assessment/policy.py  the next-item policy
logic/assessment/grading.py MCQ and debug grading
logic/assessment/theory.py  LLM judge for theory answers
logic/assessment/content.py the practice and theory banks from content/topics/<topic>/
logic/assessment/           generation, parsing, verify, seeding, sanitize (bank authoring)
logic/practice_session/     session facts and the short session feedback
logic/topic_practice/       topic runs
models.py, schemas.py
```
