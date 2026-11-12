# onboarding

The first run. Four short background steps, then an adaptive diagnostic that walks the
topics and asks code items (predict output, fill the blank, find the bug, write code) and
theory items. Code items are graded in the sandbox; theory answers are judged by the LLM in
one grouped call, with retries for any left pending. The result seeds the learner model
and produces the profile card. Switching to a new study language runs a short language
check the same way.

## Endpoints

`router.py`, under `/api/v1/onboarding`: `GET /state`, `PUT /steps/{step}`,
`POST /diagnostic/next`, `POST /diagnostic/answer`, `POST /finish`, `POST /language`,
`POST /recheck/next`, `POST /recheck/answer`, `POST /recheck/finish`, `PATCH /profile`.

## Tables

- Writes: `onboarding_records`, `learner_preferences`, `language_checks`,
  `diagnostic_responses`, `diagnostic_items` (bank, loaded by `scripts/seed/seed_diagnostic.py`)
- Through `learner_model`: `learning_events`, `topic_mastery`
- Reads: `users`

## Files

```
router.py, service.py, models.py, schemas.py
logic/steps.py        background steps
logic/walk.py         the pure adaptive walk (which item next, when to stop)
logic/bank.py         diagnostic bank access
logic/content.py      diagnostic.json files in content/topics/ <-> diagnostic_items rows
logic/graders/        one grader per item kind; sandbox.py runs code, theory.py is the LLM judge
logic/pending.py      retries for theory answers whose judge call failed
logic/seeding.py      diagnostic results -> mastery seeds
logic/profile_card.py the card shown at the end
logic/recheck.py      language switch and language check
logic/authoring/      offline bank authoring (used by scripts/generate/generate_diagnostic.py)
```
