# aiTA — AI Teaching Assistant

An AI-powered personalized learning platform for programming students. aiTA combines four specialized AI agents into a continuous feedback loop — it watches how you learn, evaluates your code, synthesizes feedback, and recommends what to study next.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Features

### 🤖 AI Agents
- **Content Player Agent** — Interactive AI tutor with 5 modes: Walkthrough, Q&A, Quiz, Code Help, Brainstorm. Adaptive difficulty adjusts automatically based on comfort signals.
- **Code Evaluation Agent** — Multi-dimensional code analysis: correctness, efficiency, security, style, documentation, and corrected code with explanations.
- **Feedback Agent** — Synthesizes findings from code evaluations and learning sessions into personalized narrative feedback. Updates your learning profile in real time.
- **Content Recommendation Agent** — Hybrid CF + CBF + RL + Groq LLM pipeline. Fetches real YouTube videos and ranks them with personalized explanations.

### 🔐 Security & Authentication
- **2-Step Login (OTP)** — Password check → bcrypt-hashed OTP sent via Gmail API → JWT tokens issued after OTP verification
- **Gmail API OAuth2** — Secure email delivery using Google's infrastructure (works on all platforms including Render)
- **Forgot Password** — Email OTP → verify → set new password. OTP bcrypt-hashed, single-use, 10-minute expiry
- **JWT Authentication** — Access + refresh tokens with automatic token refresh

### 📊 Personalization & Privacy
- **Peer Comparison** — Anonymized rank, percentile ring, and metric benchmarks vs all consenting users
- **Data Privacy Controls** — ChatGPT-style data consent toggle. Choose exactly what data is shared
- **Dynamic Learner Profile** — Every agent reads from and writes to your profile for better personalization
- **Gamification** — Points, levels, badges, and progress tracking

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 + Vite + Tailwind CSS |
| **Backend** | FastAPI (Python 3.10+) |
| **Database** | PostgreSQL + SQLAlchemy ORM |
| **LLM** | Groq API (`llama-3.3-70b-versatile`, fallback `llama3-8b-8192`) |
| **Video** | YouTube Data API v3 |
| **Auth** | JWT (access + refresh) + bcrypt + OTP |
| **Email** | Gmail API OAuth2 (HTTPS - works on Render) |
| **HTTP Client** | Axios (frontend), httpx (backend) |
| **Deployment** | Render (backend), Netlify (frontend) |

---

## 📁 Project Structure

```
aiTA/
├── backend/
│   ├── .env                        # Environment variables
│   └── app/
│       ├── main.py                 # FastAPI app entry point
│       ├── core/
│       │   ├── config.py           # Settings (DB, JWT, Gmail API, API keys)
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
│       │   ├── content_player.py
│       │   ├── code_eval.py
│       │   ├── feedback.py
│       │   └── recommendations.py
│       ├── services/               # Business logic layer
│       │   ├── auth_service.py     # Gmail API OAuth2 + SMTP fallback
│       │   └── ...
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
        │   ├── LoginPage.jsx       # 2-step login + forgot password
        │   ├── RegisterPage.jsx    # 2-step registration with topic selection
        │   ├── DashboardPage.jsx   # Stats, agents, peer comparison
        │   ├── ProfilePage.jsx     # Profile, Learning, Security, Privacy tabs
        │   ├── ContentPlayerPage.jsx
        │   ├── CodeEvalPage.jsx
        │   ├── FeedbackPage.jsx
        │   └── RecommendationPage.jsx
        ├── components/             # UI components per feature
        ├── hooks/                  # Custom React hooks
        └── utils/api.js            # Axios API client with auto token refresh
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **Groq API key** — [Get it here](https://console.groq.com)
- **YouTube Data API v3 key** *(optional)* — [Get it here](https://console.cloud.google.com)
- **Gmail API OAuth2** *(recommended for production)* — See [Gmail API Setup Guide](GMAIL_OAUTH_SETUP.md)

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/aiTA.git
cd aiTA
```

---

### 2️⃣ Backend Setup

#### Install Dependencies

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r app/requirements.txt
```

#### Configure Environment Variables

Create `backend/.env`:

```env
# PostgreSQL Database
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/aita_db

# JWT Configuration
SECRET_KEY=your_random_secret_key_here_use_long_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Groq LLM API
GROQ_API_KEY=gsk_your_groq_key_here

# YouTube Data API (optional)
YOUTUBE_API_KEY=your_youtube_api_key

# Gmail API OAuth2 (recommended for production)
# See GMAIL_OAUTH_SETUP.md for detailed setup instructions
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-your-client-secret
GMAIL_REFRESH_TOKEN=1//your-refresh-token
GMAIL_FROM_EMAIL=youremail@gmail.com

# SMTP Fallback (for local development)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password

# App Configuration
APP_NAME=aiTA - AI Teaching Assistant
APP_VERSION=1.0.0
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### Create Database

```sql
-- In psql or pgAdmin
CREATE DATABASE aita_db;
```

#### Run Migrations

```bash
# Run all migration files
psql -U postgres -d aita_db -f backend/app/setup_db.sql
psql -U postgres -d aita_db -f backend/app/migration_otp.sql
psql -U postgres -d aita_db -f backend/app/migration_content_player.sql
psql -U postgres -d aita_db -f backend/app/migration_code_eval.sql
psql -U postgres -d aita_db -f backend/app/migration_feedback.sql
psql -U postgres -d aita_db -f backend/app/migration_recommendation.sql
psql -U postgres -d aita_db -f backend/app/migration_updates.sql
```

Or run them all at once:

```bash
cd backend/app
for file in setup_db.sql migration_*.sql; do
  psql -U postgres -d aita_db -f "$file"
done
```

#### Start Backend Server

```bash
cd backend/app
uvicorn main:app --reload --port 8000
```

✅ API docs available at: `http://localhost:8000/docs`

---

### 3️⃣ Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Start Development Server

```bash
npm run dev
```

✅ App runs at: `http://localhost:5173`

---

## 📧 Email Configuration

### Option 1: Gmail API OAuth2 (Recommended for Production)

**Benefits:**
- ✅ Works on Render (uses HTTPS, not SMTP ports)
- ✅ Completely FREE - no limits
- ✅ No domain required
- ✅ Most reliable

**Setup Time:** ~20 minutes

**See detailed guide:** [GMAIL_OAUTH_SETUP.md](GMAIL_OAUTH_SETUP.md)

**Quick Reference:** [GMAIL_QUICK_REFERENCE.md](GMAIL_QUICK_REFERENCE.md)

### Option 2: SMTP (For Local Development)

**Benefits:**
- ✅ Quick setup (2 minutes)
- ✅ Works locally

**Limitations:**
- ⚠️ May not work on Render (port 587 blocked)

**Setup:** Just add SMTP credentials to `.env`

### Development Mode (No Email)

If neither Gmail API nor SMTP is configured, OTPs will print to console:

```
[DEV] OTP for user@example.com: 123456
```

---

## 🔑 Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| **Database** | | |
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection string |
| **JWT** | | |
| `SECRET_KEY` | ✅ Yes | JWT signing secret (use a long random string) |
| `ALGORITHM` | ✅ Yes | JWT algorithm (HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ Yes | Access token expiry (default: 60) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ✅ Yes | Refresh token expiry (default: 7) |
| **AI Services** | | |
| `GROQ_API_KEY` | ✅ Yes | Groq API key for all LLM agents |
| `YOUTUBE_API_KEY` | ⚠️ Optional | YouTube Data API v3 key for video recommendations |
| **Email (Gmail API - Recommended)** | | |
| `GMAIL_CLIENT_ID` | ⚠️ Optional | OAuth2 Client ID from Google Cloud Console |
| `GMAIL_CLIENT_SECRET` | ⚠️ Optional | OAuth2 Client Secret |
| `GMAIL_REFRESH_TOKEN` | ⚠️ Optional | OAuth2 Refresh Token from OAuth Playground |
| `GMAIL_FROM_EMAIL` | ⚠️ Optional | Your Gmail address (sender) |
| **Email (SMTP Fallback)** | | |
| `SMTP_HOST` | ⚠️ Optional | SMTP server (default: smtp.gmail.com) |
| `SMTP_PORT` | ⚠️ Optional | SMTP port (default: 587) |
| `SMTP_USER` | ⚠️ Optional | Gmail address for OTP emails |
| `SMTP_PASSWORD` | ⚠️ Optional | Gmail App Password |
| **App** | | |
| `APP_NAME` | ✅ Yes | Application name |
| `DEBUG` | ✅ Yes | Debug mode (True/False) |
| `ALLOWED_ORIGINS` | ✅ Yes | Comma-separated frontend origins for CORS |

---

## 📡 API Overview

### Authentication Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Step 1: Verify password, send OTP |
| `POST` | `/api/v1/auth/verify-otp` | Step 2: Verify OTP, get JWT tokens |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset OTP |
| `POST` | `/api/v1/auth/reset-password` | Reset password with OTP |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `POST` | `/api/v1/auth/logout` | Logout and invalidate session |

### User Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/users/profile` | Get user profile |
| `PATCH` | `/api/v1/users/profile` | Update user profile |
| `PATCH` | `/api/v1/users/consent` | Update data sharing consent |
| `GET` | `/api/v1/users/peer-comparison` | Get peer comparison stats |
| `POST` | `/api/v1/users/change-password` | Change password |

### AI Agent Endpoints

| Agent | Base Path | Key Endpoints |
|---|---|---|
| **Content Player** | `/api/v1/content-player` | Sessions, chat, problem generation |
| **Code Evaluation** | `/api/v1/code-eval` | Submit code, get evaluation, history |
| **Feedback** | `/api/v1/feedback` | Generate feedback, list, mark read |
| **Recommendations** | `/api/v1/recommendations` | Get recommendations, log interactions |

**Full interactive API docs:** `http://localhost:8000/docs`

---

## 🔐 Authentication Flow

### 2-Step Login with OTP

```
1. POST /auth/login { email, password }
   ↓
   ✓ Verify password
   ✓ Generate 6-digit OTP
   ✓ Bcrypt-hash OTP (raw OTP never stored)
   ✓ Send OTP via Gmail API or SMTP
   ↓
   ← Return otp_token (10-min JWT)

2. POST /auth/verify-otp { otp_token, otp }
   ↓
   ✓ Decode otp_token → get user_id
   ✓ Verify OTP against bcrypt hash
   ✓ Mark OTP as used (single-use)
   ↓
   ← Return access_token + refresh_token
```

### Forgot Password Flow

```
1. POST /auth/forgot-password { email }
   ↓
   ✓ Always returns 200 (never reveals if email exists)
   ✓ If email found: generate OTP → hash → send
   ↓
   ← Return otp_token

2. POST /auth/reset-password { otp_token, otp, new_password }
   ↓
   ✓ Verify OTP hash
   ✓ Mark OTP as used
   ✓ Hash new password → save
   ↓
   ← Return success
```

---

## 🤖 AI Agent Pipeline

```
User Activity
     │
     ▼
┌─────────────────────────┐
│ Content Player Agent    │ → Learns topics, detects mastery/confusion
│ (Interactive Tutor)     │    Adaptive difficulty
└─────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│ Code Evaluation Agent   │ → Problem + code → 6-dimension analysis
│ (Code Analyzer)         │    Correctness, efficiency, security, style
└─────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│ Feedback Agent          │ → Synthesizes eval + session data
│ (Profile Updater)       │    Updates LearningProfile
└─────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│ Recommendation Agent    │ → YouTube + CF/CBF/RL + Groq ranking
│ (Content Recommender)   │    Personalized video recommendations
└─────────────────────────┘
```

Each agent writes signals back to the shared `LearningProfile`, making every subsequent agent smarter.

---

## 📊 Peer Comparison & Privacy

Users can opt in to anonymous data sharing from **Profile → Privacy tab**.

### What's Shared (When Enabled):
- ✅ Points, sessions, code scores, accuracy
- ✅ Aggregated statistics only

### What's NEVER Shared:
- ❌ Name, email
- ❌ Code submissions
- ❌ Chat messages
- ❌ Personal information

### Features:
- Percentile ring visualization
- Anonymous rank among peers
- Metric benchmarks vs platform average
- Toggle on/off anytime

```http
PATCH /users/consent?consent=true   # Enable data sharing
GET   /users/peer-comparison         # Get comparison stats
```

---

## 🗄️ Database Schema

### Core Tables

- **users** — User accounts, profiles, preferences
- **learning_profiles** — Topic scores, strengths, weaknesses, recommendations
- **user_sessions** — Active JWT sessions
- **otp_records** — Bcrypt-hashed OTPs for 2FA

### Agent Tables

- **content_player_sessions** — Learning session metadata
- **content_player_messages** — Chat history
- **code_submissions** — User code submissions
- **code_evaluations** — Multi-dimensional code analysis results
- **feedback_reports** — Personalized feedback narratives
- **content_catalog** — YouTube videos and metadata
- **recommendations** — Personalized content recommendations

---

## 🚀 Deployment

### Backend (Render)

1. **Create Web Service** on Render
2. **Connect GitHub repository**
3. **Configure:**
   - Build Command: `pip install -r backend/app/requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Add Environment Variables** (all from `.env`)
5. **Deploy!**

**Important:** Use Gmail API OAuth2 for email (SMTP ports may be blocked)

### Frontend (Netlify)

1. **Connect GitHub repository**
2. **Configure:**
   - Build Command: `npm run build`
   - Publish Directory: `dist`
3. **Add Environment Variables:**
   - `VITE_API_URL=https://your-backend.onrender.com`
4. **Deploy!**

---

## 📚 Documentation

### Setup Guides
- [Gmail API OAuth2 Setup](GMAIL_OAUTH_SETUP.md) - Detailed step-by-step guide
- [Gmail Quick Reference](GMAIL_QUICK_REFERENCE.md) - 20-minute quick setup
- [Setup Checklist](SETUP_CHECKLIST.md) - Track your progress
- [Email Setup Summary](EMAIL_SETUP_SUMMARY.md) - Overview of email options

### Additional Docs
- [SMTP Setup](SMTP_SETUP.md) - Alternative SMTP configuration
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

---

## 🛠️ Development Notes

### OTP in Development
OTPs print to console if email is not configured:
```
[DEV] OTP for user@example.com: 123456
```

### YouTube API Fallback
Recommendations work without YouTube API key; videos will have `url: null`

### Groq LLM Fallback
Primary model → `llama3-8b-8192` fallback → score-based ranking if both fail

### Profile Topics
Set topics in **Profile → Learning tab** before running Recommendation Agent

### Peer Comparison
Requires at least one other user with data sharing enabled

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Contribution Guidelines
- Follow existing code style
- Add tests for new features
- Update documentation
- Keep commits atomic and well-described

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Your Name** - *Initial work* - [GitHub](https://github.com/your-username)

---

## 🙏 Acknowledgments

- **Groq** - For providing fast LLM inference
- **YouTube Data API** - For video content
- **FastAPI** - For the amazing Python web framework
- **React** - For the powerful frontend library
- **Google Cloud** - For Gmail API OAuth2

---

## 📞 Support

- **Documentation:** See guides in the repository
- **Issues:** [GitHub Issues](https://github.com/your-username/aiTA/issues)
- **Email:** your-email@example.com

---

## 🗺️ Roadmap

- [ ] Mobile app (React Native)
- [ ] More programming languages support
- [ ] Real-time collaboration features
- [ ] Advanced analytics dashboard
- [ ] Integration with more video platforms
- [ ] Offline mode support

---

<div align="center">

**Made with ❤️ by the aiTA Team**

[⭐ Star us on GitHub](https://github.com/your-username/aiTA) | [🐛 Report Bug](https://github.com/your-username/aiTA/issues) | [✨ Request Feature](https://github.com/your-username/aiTA/issues)

</div>
