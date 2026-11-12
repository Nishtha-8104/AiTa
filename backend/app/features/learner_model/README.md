# learner_model

What the system believes the student knows. The Profiling Agent takes every graded event
(code, MCQ, debug, theory, diagnostic), stores it as a learning event, moves mastery for
that topic in that language, runs the gamification step and refreshes the learning profile.
It also holds the read-only query layer over all learning data (used by the chat) and the
style line built from onboarding preferences.

## Endpoints

None of its own. Mastery is shown through `GET /api/v1/profile/mastery` (`accounts`).

## Tables

- Writes: `learning_events`, `topic_mastery`; mirrored fields on `learning_profiles`
- Through `gamification`: `gamification_awards`
- Reads (learning data): `code_submissions`, `code_evaluations`, `mcq_*`, `debug_*`,
  `theory_*`, `hint_events`, `feedback_reports`, `problems`, `learner_preferences`

## Files

```
agent/graph.py            Profiling Agent: ingest()
service.py                EventInput, mastery_snapshot(), derive_profile(), diagnostic seeding
logic/mastery.py          the mastery update and its constants
logic/learning_data.py    query() over every learning source
logic/personalisation/    style_line() from onboarding preferences
logic/demo.py             report and reset for the demo account
models.py                 LearningEvent, TopicMastery
```
