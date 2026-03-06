-- ============================================================
--  aiTA — Migration: Content Recommendation Agent Tables
--  Run this in pgAdmin Query Tool on the aita_db database
-- ============================================================

-- 1. Content type enums
CREATE TYPE contenttype AS ENUM ('video', 'article', 'exercise', 'quiz', 'project', 'tutorial');
CREATE TYPE difficultylevel AS ENUM ('beginner', 'intermediate', 'advanced');
CREATE TYPE interactiontype AS ENUM ('view', 'complete', 'like', 'dislike', 'skip', 'bookmark');

-- 2. Content catalog
CREATE TABLE IF NOT EXISTS contents (
    id               SERIAL PRIMARY KEY,
    title            VARCHAR(500) NOT NULL,
    description      TEXT,
    content_type     contenttype NOT NULL,
    difficulty       difficultylevel NOT NULL,
    url              VARCHAR(1000),
    thumbnail_url    VARCHAR(1000),
    duration_mins    FLOAT,
    language         VARCHAR(50),
    topics           JSONB DEFAULT '[]',
    skills_gained    JSONB DEFAULT '[]',
    prerequisites    JSONB DEFAULT '[]',
    author           VARCHAR(255),
    source           VARCHAR(255),
    avg_rating       FLOAT DEFAULT 0.0,
    total_ratings    INTEGER DEFAULT 0,
    completion_rate  FLOAT DEFAULT 0.0,
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ
);

-- 3. User-Content interaction matrix (Collaborative Filtering data)
CREATE TABLE IF NOT EXISTS user_content_interactions (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    content_id       INTEGER REFERENCES contents(id) ON DELETE CASCADE NOT NULL,
    interaction      interactiontype DEFAULT 'view',
    rating           FLOAT,                        -- explicit 1-5
    implicit_score   FLOAT DEFAULT 0.0,            -- computed: time × completion
    time_spent_mins  FLOAT DEFAULT 0.0,
    completion_pct   FLOAT DEFAULT 0.0,
    is_completed     BOOLEAN DEFAULT FALSE,
    is_bookmarked    BOOLEAN DEFAULT FALSE,
    interacted_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ,
    CONSTRAINT uq_user_content UNIQUE (user_id, content_id)
);

-- 4. AI-generated recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    content_id       INTEGER REFERENCES contents(id) ON DELETE CASCADE NOT NULL,
    score            FLOAT DEFAULT 0.0,
    cf_score         FLOAT DEFAULT 0.0,
    cbf_score        FLOAT DEFAULT 0.0,
    rl_bonus         FLOAT DEFAULT 0.0,
    agent_reasoning  TEXT,
    rank             INTEGER,
    batch_id         VARCHAR(64),
    is_dismissed     BOOLEAN DEFAULT FALSE,
    is_clicked       BOOLEAN DEFAULT FALSE,
    generated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Agent run audit log
CREATE TABLE IF NOT EXISTS agent_run_logs (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    batch_id         VARCHAR(64) UNIQUE NOT NULL,
    status           VARCHAR(30) DEFAULT 'pending',
    step_log         JSONB DEFAULT '[]',
    cf_candidates    INTEGER DEFAULT 0,
    cbf_candidates   INTEGER DEFAULT 0,
    final_count      INTEGER DEFAULT 0,
    llm_tokens_used  INTEGER DEFAULT 0,
    duration_ms      INTEGER DEFAULT 0,
    error_message    TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Indexes
CREATE INDEX idx_interactions_user    ON user_content_interactions(user_id);
CREATE INDEX idx_interactions_content ON user_content_interactions(content_id);
CREATE INDEX idx_recs_user            ON recommendations(user_id);
CREATE INDEX idx_recs_batch           ON recommendations(batch_id);
CREATE INDEX idx_agent_log_user       ON agent_run_logs(user_id);
CREATE INDEX idx_contents_type        ON contents(content_type);
CREATE INDEX idx_contents_difficulty  ON contents(difficulty);

SELECT 'Recommendation Agent tables created!' AS status;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;