-- ============================================================
--  aiTA Database Setup Script
--  Run this in pgAdmin Query Tool BEFORE starting the backend
-- ============================================================

-- 1. Create the database (run this connected to 'postgres' DB)
CREATE DATABASE aita_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- 2. Connect to aita_db and run the rest below
-- \c aita_db;  (in psql) or switch to aita_db in pgAdmin

-- 3. Create ENUM types
CREATE TYPE userrole AS ENUM ('student', 'instructor', 'ta', 'admin');
CREATE TYPE skilllevel AS ENUM ('beginner', 'intermediate', 'advanced');

-- 4. Users table
CREATE TABLE IF NOT EXISTS users (
    id                      SERIAL PRIMARY KEY,
    email                   VARCHAR(255) UNIQUE NOT NULL,
    username                VARCHAR(100) UNIQUE NOT NULL,
    hashed_password         VARCHAR(255) NOT NULL,
    full_name               VARCHAR(255),
    role                    userrole DEFAULT 'student' NOT NULL,
    is_active               BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified             BOOLEAN DEFAULT FALSE NOT NULL,
    bio                     TEXT,
    avatar_url              VARCHAR(500),
    institution             VARCHAR(255),
    year_of_study           INTEGER,
    city                    VARCHAR(100),
    state                   VARCHAR(100),
    skill_level             skilllevel DEFAULT 'beginner',
    years_of_experience     FLOAT DEFAULT 0.0,
    preferred_languages     JSONB DEFAULT '[]',
    learning_goals          JSONB DEFAULT '[]',
    interests               JSONB DEFAULT '[]',
    total_sessions          INTEGER DEFAULT 0,
    total_time_spent_mins   FLOAT DEFAULT 0.0,
    avg_session_duration_mins FLOAT DEFAULT 0.0,
    last_active_at          TIMESTAMPTZ,
    points                  INTEGER DEFAULT 0,
    level                   INTEGER DEFAULT 1,
    badges                  JSONB DEFAULT '[]',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ
);

-- 5. Learning profiles table (one per user)
CREATE TABLE IF NOT EXISTS learning_profiles (
    id                          SERIAL PRIMARY KEY,
    user_id                     INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    topic_scores                JSONB DEFAULT '{}',
    error_patterns              JSONB DEFAULT '[]',
    strong_areas                JSONB DEFAULT '[]',
    weak_areas                  JSONB DEFAULT '[]',
    recommended_next            JSONB DEFAULT '[]',
    preferred_content_types     JSONB DEFAULT '[]',
    study_time_preference       VARCHAR(50),
    avg_problems_per_session    FLOAT DEFAULT 0.0,
    accuracy_rate               FLOAT DEFAULT 0.0,
    improvement_rate            FLOAT DEFAULT 0.0,
    profile_completeness        FLOAT DEFAULT 0.0,
    last_updated_by_agent       TIMESTAMPTZ,
    agent_version               VARCHAR(20) DEFAULT '1.0',
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ
);

-- 6. User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_jti   VARCHAR(255) UNIQUE NOT NULL,
    ip_address  VARCHAR(50),
    user_agent  VARCHAR(500),
    is_active   BOOLEAN DEFAULT TRUE,
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,
    ended_at    TIMESTAMPTZ
);

-- 7. Helpful indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_jti ON user_sessions(token_jti);

-- 8. Verify
SELECT 'Database setup complete! Tables created:' AS status;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';