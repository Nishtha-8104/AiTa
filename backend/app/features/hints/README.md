# hints

The hint ladder. Each request for a problem gives the next rung, from a nudge up to a
concrete pointer, never the fix itself. Every LLM-written hint passes a guardrail that
rejects quoted reference code and asks a judge whether the hint states the fix. Approach
hints (before any code is written) serve the chat. Hint use is recorded so mastery and the
leak rate can account for it.

## The ladder

| Level | Name | Practice hint (failing code) | Approach hint (chat, no tests) | Written by | Mastery multiplier |
|---|---|---|---|---|---|
| L1 | Failing case / nudge | The first failing input, expected vs printed output, "trace it by hand" | Questions to restate the input and output; names no technique | Template (practice), LLM (approach) | 0.9 |
| L2 | Concept | The programming idea being missed, in general terms, with one question tying it to the failing input; no lines or names from the code | The idea or data structure the problem relies on | LLM | 0.75 |
| L3 | Steps in words | The steps a correct approach takes on the failing input, stopping just before the one the student gets wrong | The main steps of a correct program, details left to the student | LLM | 0.6 |
| L4 | Line pointer / outline | The line(s) where the problem starts, and what is wrong there, never how to rewrite it | A short numbered pseudocode outline, edge cases left out | LLM | 0.5 |

- Each Practice request gives the next level, up to L4. A fully passing Practice run
  resets the ladder. Chat hints never move it.
- The mastery multiplier applies the highest Practice level seen before a submission to
  that submission's score. No hint means 1.0.
- Every LLM hint passes `guardrail.check`, which blocks it if it quotes the reference
  solution, has more than 3 lines of code (2 at L4), or has code that passes the tests. A
  hint about the student's code then goes to the `states_fix` LLM judge, which blocks a fix
  told in words.
- A blocked hint is retried once. If it is blocked again, or the LLM is down, the
  level's fixed template is shown instead.

## Endpoints

None of its own. Hints are served by `POST /api/v1/feedback/hint` (`feedback/router.py`)
and by the chat's `get_hint` tool.

## Tables

- Writes: `hint_events`
- Reads: `problems`, `test_cases`, `code_submissions`, `code_evaluations`, `learning_events`

## Files

```
service.py           request_hint(), approach_hint(), next_level(), leak_rate()
logic/guardrail.py   code-quote check and the states_fix judge
logic/prompts.py     one template per ladder level, plus approach templates
models.py            HintEvent
```
