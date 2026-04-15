-- ============================================================
--  aiTA — Migration: Feedback Agent Tables
--  Run in pgAdmin Query Tool on aita_db
--  AFTER all previous migrations
-- ============================================================

-- 1. Enums
CREATE TYPE feedbacktype AS ENUM ('code_review', 'learning_recap', 'combined');
CREATE TYPE feedbacktone AS ENUM ('encouraging', 'constructive', 'challenging');

-- 2. feedback_reports
CREATE TABLE IF NOT EXISTS feedback_reports (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id)                   ON DELETE CASCADE NOT NULL,
    evaluation_id    INTEGER REFERENCES code_evaluations(id)        ON DELETE SET NULL,
    cp_session_id    INTEGER REFERENCES content_player_sessions(id) ON DELETE SET NULL,

    feedback_type    feedbacktype DEFAULT 'code_review',
    tone             feedbacktone DEFAULT 'encouraging',

    headline         VARCHAR(300),
    summary          TEXT,
    strengths        JSONB DEFAULT '[]',
    errors           JSONB DEFAULT '[]',
    misconceptions   JSONB DEFAULT '[]',
    action_items     JSONB DEFAULT '[]',
    concept_map      JSONB DEFAULT '{}',
    next_topics      JSONB DEFAULT '[]',
    motivational     TEXT,
    profile_updates  JSONB DEFAULT '{}',

    agent_steps      JSONB DEFAULT '[]',
    tokens_used      INTEGER DEFAULT 0,
    latency_ms       INTEGER DEFAULT 0,
    is_read          BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Indexes
CREATE INDEX idx_feedback_user       ON feedback_reports(user_id);
CREATE INDEX idx_feedback_unread     ON feedback_reports(user_id, is_read);
CREATE INDEX idx_feedback_eval       ON feedback_reports(evaluation_id);
CREATE INDEX idx_feedback_session    ON feedback_reports(cp_session_id);

SELECT 'Feedback Agent tables created!' AS status;