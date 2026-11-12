# feedback

Written feedback reports. The Feedback Agent gathers a code evaluation and recent practice,
looks for repeated mistakes, has the LLM write the narrative and saves the report. Reports
can also be written from the latest activity with no input. This router also serves the
hint ladder endpoint.

## Endpoints

`router.py`, under `/api/v1/feedback`: `POST /hint`, `POST /generate`, `GET /`,
`GET /unread-count`, `GET /{report_id}`, `PATCH /{report_id}/read`, `POST /auto-generate`.

## Tables

- Writes: `feedback_reports`; `hint_events` through `hints`
- Reads: `code_submissions`, `code_evaluations`, `learning_events`, `topic_mastery`,
  `mcq_attempts`, `debug_attempts`, `problems`, `users`

## Files

```
router.py
service.py           FeedbackService: generate, list, read state
agent/               LangGraph: gather_context -> analyse_patterns -> synthesise -> persist
logic/activity.py    feedback from the latest activity
logic/patterns.py    repeated-mistake detection
logic/reports.py     report shaping
models.py, schemas.py
```
