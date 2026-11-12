# gamification

Verified gamification. Points, topic levels and badges are awarded only from graded
learning events, inside the Profiling Agent's run, and every award is a ledger row tied to
the event that earned it. The ledger can be rebuilt from `learning_events` and gives the
same result. `GAMIFICATION_MODE` sets it to `live`, `silent` or `off`.

## Endpoints

`router.py`, under `/api/v1/gamification`: `GET /me`.

## Tables

- Writes: `gamification_awards`; the mirrors `users.points`, `users.level`, `users.badges`
- Reads: `learning_events`, `topic_mastery`

## Files

```
router.py
service.py       apply() per event, rebuild(), summary()
logic/rules.py   pure award rules: evaluate(), is_solved()
models.py        GamificationAward
schemas.py
```

Rebuild with `scripts/tools/rebuild_awards.py`.
