# accounts

Who the student is. PET runs on the student's own computer, so there is no sign-in:
the browser opens a session for the one local student and carries its token. Also the
student's own profile, data-sharing consent and the peer comparison.

## Endpoints

| Router | Prefix | Endpoints |
|---|---|---|
| `router_auth.py` | `/api/v1/auth` | `POST /session` (opens the local student's session), `GET /me` |
| `router_users.py` | `/api/v1/users` | my profile (get/update), consent, peer comparison, admin user list |
| `router_profile.py` | `/api/v1/profile` | `GET /mastery`, measured mastery per topic (read from `learner_model`) |

## Tables

- Writes: `users`, `user_sessions`, `learning_profiles`
- Reads: `topic_mastery` (mastery endpoint), `code_submissions` / `code_evaluations`
  (profile stats), `onboarding_records` (profile)

`learning_profiles` rows are created here; their mirrored fields are kept up to date by
`learner_model`. `users.points`, `users.level` and `users.badges` are mirrors written by
`gamification`.

## Files

```
router_auth.py, router_users.py, router_profile.py   HTTP
service.py            AuthService: the local student, sessions, tokens
logic/user_service.py UserService: profile, consent, peer comparison
models.py             User, LearningProfile, UserSession
schemas.py            request/response models (auth, user, profile)
```
