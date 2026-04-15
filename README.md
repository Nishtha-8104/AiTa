# aiTA — AI Teaching Assistant

An AI-powered personalized learning platform for programming students. aiTA combines four specialized AI agents into a continuous feedback loop — it watches how you learn, evaluates your code, synthesizes feedback, and recommends what to study next.

---

## Features

- **Content Player Agent** — Interactive AI tutor with 5 modes: Walkthrough, Q&A, Quiz, Code Help, Brainstorm. Adaptive difficulty that adjusts based on your comfort level.
- **Code Evaluation Agent** — Paste a problem statement + your solution and get multi-dimensional analysis: correctness, efficiency, security, style, documentation, and corrected code.
- **Feedback Agent** — Synthesizes findings from code evaluations and learning sessions into personalized narrative feedback. Updates your learning profile in real time.
- **Content Recommendation Agent** — Hybrid CF + CBF + RL + Groq LLM pipeline. Fetches real YouTube videos per your topics and ranks them for you.
- **2-Step Login (OTP)** — Password check → bcrypt-hashed OTP sent to email → real JWT tokens issued only after OTP verification.
- **Dynamic Learner Profile** — Every agent reads from and writes to your profile. More activity = better personalization.
- **Gamification** — Points, levels, badges.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy ORM |
| LLM | Groq API (`llama-3.3-70b-versatile`) |
| Video | YouTube Data API v3 |
| Auth | JWT (access + refresh) + bcrypt |
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
│       │   ├── config.py           # Settings
│       │   ├── database.py         # SQLAlchemy engine
│       │   ├── security.py         # JWT, bcrypt, OTP helpers
│       │   └── dependencies.py     # Auth dependencies
│       ├── models/                 # SQLAlchemy ORM models
│       ├── schemas/                # Pydantic request/response schemas
│       ├── api/                    # FastAPI routers
│       ├── services/               # Business logic
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
        ├── components/             # UI components per feature
        ├── hooks/                  # Custom React hooks
        └── utils/api.js            # Axios API client
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- A [Groq API key](https://console.groq.com)
- A [YouTube Data API v3 key](https://console.cloud.google.com) *(optional — recommendations still work without it, just no real video URLs)*
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

Copy the example and fill in your values:

```bash
cp .env.example .env
```

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

```bash
# In psql or pgAdmin
CREATE DATABASE aita_db;
```

Then run the OTP migration (tables are auto-created on startup except this one):

```bash
psql -U postgres -d aita_db -f app/migration_otp.sql
```

#### Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

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

| Group | Base Path | Description |
|---|---|---|
| Auth | `/api/v1/auth` | Register, login (2-step OTP), refresh, logout |
| Users | `/api/v1/users` | Profile read/update, change password |
| Content Player | `/api/v1/content-player` | Sessions, chat, problem generation |
| Code Evaluation | `/api/v1/code-eval` | Submit code, evaluate, history, stats |
| Feedback | `/api/v1/feedback` | Generate, list, mark read |
| Recommendations | `/api/v1/recommendations` | Run agent, get recs, log interactions |

Full interactive docs: `http://localhost:8000/docs`

---

## Login Flow (2-Step OTP)

```
1. POST /auth/login        → verify password → OTP bcrypt-hashed → stored in DB
                           → raw OTP emailed → returns otp_token (10-min JWT)

2. POST /auth/verify-otp   → verify OTP hash → mark used → return access + refresh tokens
```

In development without SMTP configured, the OTP is printed to the backend console.

---

## Agent Pipeline

```
User Activity
     │
     ▼
[1] Content Player Agent   → learns topic, detects mastery/confusion
     │
     ▼
[2] Code Evaluation Agent  → static analysis + Groq LLM → 6-dimension scores
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

Tables are auto-created on startup via SQLAlchemy. For schema changes, SQL migration files are in `backend/app/`:

| File | Description |
|---|---|
| `migration_otp.sql` | OTP records table for 2-step login |
| `migration_content_player.sql` | Content player sessions/messages |
| `migration_code_eval.sql` | Code submissions and evaluations |
| `migration_feedback.sql` | Feedback reports |
| `migration_recommendation.sql` | Content catalog and recommendations |

Run any migration manually:
```bash
psql -U postgres -d aita_db -f backend/app/migration_name.sql
```

---

## Development Notes

- **OTP in dev** — If `SMTP_USER` is not set, OTPs are logged to the backend console as `[DEV] OTP for email@example.com: 123456`
- **YouTube fallback** — If `YOUTUBE_API_KEY` is not set, recommendations still work but content items will have `url: null`
- **Groq fallback** — If the primary model (`llama-3.3-70b-versatile`) fails, agents retry with `llama3-8b-8192` before falling back to static/score-based results
- **Profile topics** — Set topics in your profile (Profile → Learning tab) before running the Recommendation Agent

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---
