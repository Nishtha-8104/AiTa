# aiTA — AI Teaching Assistant

An AI-powered personalized learning platform for programming students. aiTA combines four specialized AI agents into a continuous feedback loop — it watches how you learn, evaluates your code, synthesizes feedback, and recommends what to study next.

---

## Features

- **Content Player Agent** — Interactive AI tutor with 5 modes: Walkthrough, Q&A, Quiz, Code Help, Brainstorm. Adaptive difficulty adjusts automatically based on comfort signals.
- **Code Evaluation Agent** — Paste a problem statement + your solution and get multi-dimensional analysis: correctness, efficiency, security, style, documentation, and corrected code.
- **Feedback Agent** — Synthesizes findings from code evaluations and learning sessions into personalized narrative feedback. Updates your learning profile in real time.
- **Content Recommendation Agent** — Hybrid CF + CBF + RL + Groq LLM pipeline. Fetches real YouTube videos per your topics and ranks them with personalized explanations.
- **2-Step Login (OTP)** — Password check → bcrypt-hashed OTP sent to email → real JWT tokens issued only after OTP verification.
- **Forgot Password** — Email OTP → verify → set new password. OTP bcrypt-hashed before storage, single-use, 10-minute expiry.
- **Peer Comparison** — Anonymized rank, percentile ring, and metric benchmarks vs all consenting users. Opt-in via Privacy Settings.
- **Data Privacy Controls** — ChatGPT-style data consent toggle. Choose exactly what data is shared for comparison. Name and email are never shared.
- **Dynamic Learner Profile** — Every agent reads from and writes to your profile. More activity = better personalization.
- **Gamification** — Points, levels, badges.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy ORM |
| LLM | Groq API (`llama-3.3-70b-versatile`, fallback `llama3-8b-8192`) |
| Video | YouTube Data API v3 |
| Auth | JWT (access + refresh) + bcrypt + OTP |
| HTTP Client | Axios (frontend), httpx (backend) |

---

## Project Structure

```
aiTA/
├── backend/
│   ├── .env                        # Environment variables
│   └── app/
│       ├── main.py                 # FastAPI app entry point
│       ├── core/
│       │   ├── config.py           # Settings (DB, JWT, SMTP, API keys)
│       │   ├── database.py         # SQLAlchemy engine + session
│       │   ├── security.py         # JWT, bcrypt, OTP generate/hash/verify
│       │   └── dependencies.py     # Auth dependencies + role checks
│       ├── models/                 # SQLAlchemy ORM models
│       │   ├── user.py             # User, LearningProfile, OTPRecord, UserSession
│       │   ├── content_player.py
│       │   ├── code_eval.py
│       │   ├── feedback.py
│       │   └── recommendation.py
│       ├── schemas/                # Pydantic request/response schemas
│       ├── api/                    # FastAPI routers
│       │   ├── auth.py             # login, verify-otp, forgot-password, reset-password
│       │   ├── users.py            # profile, consent, peer-comparison
│       │   └── ...
│       ├── services/               # Business logic layer
│       └── agents/                 # AI agent logic
│           ├── content_player_agent.py
│           ├── code_eval_agent.py
│           ├── feedback_agent.py
│           └── recommendation_agent.py
└── frontend/
    ├── index.html
    └── src/
        ├── App.jsx
        ├── pages/                  # Route-level pages
        │   ├── LoginPage.jsx       # 2-step login + forgot password (inline)
        │   ├── RegisterPage.jsx    # 2-step registration with topic selection
        │   ├── DashboardPage.jsx   # Stats, agents, peer comparison
        │   ├── ProfilePage.jsx     # Profile, Learning, Security, Privacy tabs
        │   └── ...
        ├── components/             # UI components per feature
        ├── hooks/                  # Custom React hooks
        └── utils/api.js            # Axios API client with auto token refresh
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- A [Groq API key](https://console.groq.com)
- A [YouTube Data API v3 key](https://console.cloud.google.com) *(optional — recommendations still work without it)*
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) for OTP emails *(optional — OTP prints to console in dev mode)*

---

### 1. Clone the repo

```bash
git clone https://github.com/your-username/aiTA.git
cd aiTA
```

---

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r app/requirements.txt
```

#### Configure environment variables

Edit `backend/.env`:

```env
# PostgreSQL
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/aita_db

# JWT
SECRET_KEY=your_random_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Groq LLM
GROQ_API_KEY=gsk_your_groq_key_here

# YouTube Data API (optional)
YOUTUBE_API_KEY=your_youtube_api_key

# SMTP for OTP emails (optional — OTP logs to console if not set)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password

# App
APP_NAME=aiTA - AI Teaching Assistant
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### Create the database

```sql
-- In psql or pgAdmin
CREATE DATABASE aita_db;
```

Then run the required migrations:

```bash
psql -U postgres -d aita_db -f backend/app/migration_otp.sql
```

> Other tables are auto-created on startup via SQLAlchemy. Also run this to add the data consent columns:
> ```sql
> ALTER TABLE users
>   ADD COLUMN IF NOT EXISTS data_sharing_consent BOOLEAN DEFAULT FALSE,
>   ADD COLUMN IF NOT EXISTS consent_updated_at TIMESTAMPTZ;
> ```

#### Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

---

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

App runs at: `http://localhost:5173`

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing secret (use a long random string) |
| `GROQ_API_KEY` | Yes | Groq API key for all LLM agents |
| `YOUTUBE_API_KEY` | No | YouTube Data API v3 key for real video content |
| `SMTP_USER` | No | Gmail address for OTP emails |
| `SMTP_PASSWORD` | No | Gmail App Password (not your regular password) |
| `ALLOWED_ORIGINS` | Yes | Comma-separated frontend origins for CORS |

---

## API Overview

| Group | Base Path | Key Endpoints |
|---|---|---|
| Auth | `/api/v1/auth` | `POST /login`, `POST /verify-otp`, `POST /forgot-password`, `POST /reset-password`, `POST /register`, `POST /refresh`, `POST /logout` |
| Users | `/api/v1/users` | `GET/PATCH /profile`, `PATCH /consent`, `GET /peer-comparison`, `POST /change-password` |
| Content Player | `/api/v1/content-player` | Sessions, chat, problem generation |
| Code Evaluation | `/api/v1/code-eval` | Submit, evaluate, history, stats |
| Feedback | `/api/v1/feedback` | Generate, auto-generate, list, mark read |
| Recommendations | `/api/v1/recommendations` | Run agent, get recs, log interactions, dismiss |

Full interactive docs: `http://localhost:8000/docs`

---

## Auth Flows

### Login (2-Step OTP)

```
POST /auth/login
  → verify password
  → generate 6-digit OTP
  → bcrypt-hash OTP → store hash in otp_records (raw OTP never saved)
  → email raw OTP to user
  → return otp_token (10-min JWT, type: otp_pending)

POST /auth/verify-otp  { otp_token, otp }
  → decode otp_token → get user_id
  → verify OTP against bcrypt hash
  → mark OTP as used (single-use)
  → return access_token + refresh_token
```

### Forgot Password

```
POST /auth/forgot-password  { email }
  → always returns 200 (never reveals if email exists)
  → if email found: generate OTP → bcrypt-hash → store → email raw OTP
  → return otp_token

POST /auth/reset-password  { otp_token, otp, new_password }
  → verify OTP hash
  → mark OTP as used
  → bcrypt-hash new password → save
```

In development without SMTP, all OTPs print to the backend console as:
```
[DEV] OTP for email@example.com: 123456
```

---

## Peer Comparison & Privacy

Users can opt in to anonymous data sharing from **Profile → Privacy tab**.

- When enabled: points, sessions, code scores, and accuracy are included in platform-wide comparisons
- Name, email, code submissions, and chat messages are **never** shared
- The dashboard shows a percentile ring, rank, and metric benchmarks vs all consenting users
- Consent can be toggled off at any time — data is excluded immediately

```
PATCH /users/consent?consent=true   → enable data sharing
GET  /users/peer-comparison         → returns rank, percentile, metric comparisons
```

---

## Agent Pipeline

```
User Activity
     │
     ▼
[1] Content Player Agent   → learns topic, detects mastery/confusion, adaptive difficulty
     │
     ▼
[2] Code Evaluation Agent  → problem statement + code → static analysis + Groq LLM → 6-dimension scores
     │
     ▼
[3] Feedback Agent         → synthesizes eval + session → updates LearningProfile
     │
     ▼
[4] Recommendation Agent   → reads profile → YouTube + CF/CBF/RL + Groq ranking
```

Each agent writes signals back to the shared `LearningProfile`, making every subsequent agent smarter.

---

## Database Migrations

| File | Description |
|---|---|
| `migration_otp.sql` | `otp_records` table for 2-step login and password reset |
| `migration_content_player.sql` | Content player sessions and messages |
| `migration_code_eval.sql` | Code submissions and evaluations |
| `migration_feedback.sql` | Feedback reports |
| `migration_recommendation.sql` | Content catalog and recommendations |

Manual columns (not in migration files):
```sql
-- Data consent (peer comparison)
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS data_sharing_consent BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS consent_updated_at TIMESTAMPTZ;
```

---

## Development Notes

- **OTP in dev** — OTPs print to console if SMTP is not configured: `[DEV] OTP for ...: 123456`
- **YouTube fallback** — Recommendations work without a YouTube key; content items will have `url: null`
- **Groq fallback** — Primary model → `llama3-8b-8192` fallback → score-based ranking if both fail
- **Profile topics** — Set topics in Profile → Learning tab before running the Recommendation Agent
- **Peer comparison** — Requires at least one other user with data sharing enabled to show meaningful data

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m 'Add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---
