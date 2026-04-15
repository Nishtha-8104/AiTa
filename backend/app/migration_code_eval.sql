-- ============================================================
--  aiTA — Migration: Code Evaluation Agent Tables
--  Run in pgAdmin Query Tool on aita_db
--  AFTER all previous migrations have been run
-- ============================================================

-- 1. Enums
CREATE TYPE language_enum AS ENUM (
    'python','javascript','java','cpp','c','typescript','go','rust','sql'
);
CREATE TYPE eval_status AS ENUM ('pending','running','done','failed');
CREATE TYPE severity_level AS ENUM ('info','warning','error','critical');

-- 2. Code submissions
CREATE TABLE IF NOT EXISTS code_submissions (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    title            VARCHAR(300),
    language         language_enum NOT NULL,
    code             TEXT NOT NULL,
    problem_context  TEXT,
    expected_output  TEXT,
    status           eval_status DEFAULT 'pending',
    eval_count       INTEGER DEFAULT 0,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ
);

-- 3. Code evaluations (full result per agent run)
CREATE TABLE IF NOT EXISTS code_evaluations (
    id                    SERIAL PRIMARY KEY,
    submission_id         INTEGER REFERENCES code_submissions(id) ON DELETE CASCADE,
    user_id               INTEGER REFERENCES users(id) ON DELETE CASCADE,

    -- Scores (0-100)
    overall_score         FLOAT DEFAULT 0,
    correctness_score     FLOAT DEFAULT 0,
    quality_score         FLOAT DEFAULT 0,
    efficiency_score      FLOAT DEFAULT 0,
    security_score        FLOAT DEFAULT 0,
    style_score           FLOAT DEFAULT 0,
    documentation_score   FLOAT DEFAULT 0,

    -- Static analysis
    issues                JSONB DEFAULT '[]',

    -- Complexity
    time_complexity       VARCHAR(30),
    space_complexity      VARCHAR(30),
    cyclomatic_complexity INTEGER,
    lines_of_code         INTEGER,
    comment_ratio         FLOAT,

    -- LLM output
    summary               TEXT,
    detailed_feedback     TEXT,
    corrected_code        TEXT,
    key_improvements      JSONB DEFAULT '[]',
    learning_points       JSONB DEFAULT '[]',
    best_practices_used   JSONB DEFAULT '[]',
    anti_patterns         JSONB DEFAULT '[]',
    suggested_resources   JSONB DEFAULT '[]',

    -- Agent metadata
    agent_steps           JSONB DEFAULT '[]',
    tokens_used           INTEGER DEFAULT 0,
    latency_ms            INTEGER DEFAULT 0,
    model_used            VARCHAR(100),
    static_tool_used      VARCHAR(100),

    created_at            TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Evaluation history (for progress tracking / score chart)
CREATE TABLE IF NOT EXISTS eval_history (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    submission_id   INTEGER REFERENCES code_submissions(id) ON DELETE CASCADE,
    evaluation_id   INTEGER REFERENCES code_evaluations(id) ON DELETE CASCADE,
    overall_score   FLOAT DEFAULT 0,
    language        language_enum NOT NULL,
    eval_number     INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Indexes
CREATE INDEX idx_submissions_user    ON code_submissions(user_id);
CREATE INDEX idx_submissions_lang    ON code_submissions(language);
CREATE INDEX idx_evaluations_sub     ON code_evaluations(submission_id);
CREATE INDEX idx_evaluations_user    ON code_evaluations(user_id);
CREATE INDEX idx_eval_history_user   ON eval_history(user_id);
CREATE INDEX idx_eval_history_sub    ON eval_history(submission_id);

SELECT 'Code Evaluation Agent tables created!' AS status;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;