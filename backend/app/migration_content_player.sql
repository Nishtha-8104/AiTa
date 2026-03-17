-- ============================================================
--  aiTA — Migration: Content Player Agent Tables
--  Run in pgAdmin Query Tool on aita_db AFTER previous migrations
-- ============================================================

CREATE TYPE sessionmode AS ENUM ('qa', 'code_help', 'brainstorm', 'quiz', 'walkthrough');
CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'system');

-- 1. Sessions table
CREATE TABLE IF NOT EXISTS content_player_sessions (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    title               VARCHAR(500),
    mode                sessionmode DEFAULT 'qa',
    language            VARCHAR(50),
    topic               VARCHAR(255),
    is_active           BOOLEAN DEFAULT TRUE,
    is_archived         BOOLEAN DEFAULT FALSE,
    total_messages      INTEGER DEFAULT 0,
    total_tokens_used   INTEGER DEFAULT 0,
    concepts_covered    JSONB DEFAULT '[]',
    agent_model         VARCHAR(100) DEFAULT 'llama-3.3-70b-versatile',
    confusion_detected  BOOLEAN DEFAULT FALSE,
    mastery_signals     JSONB DEFAULT '[]',
    weak_signals        JSONB DEFAULT '[]',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,
    last_message_at     TIMESTAMPTZ
);

-- 2. Messages table
CREATE TABLE IF NOT EXISTS content_player_messages (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES content_player_sessions(id) ON DELETE CASCADE,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role            messagerole NOT NULL,
    content         TEXT NOT NULL,
    has_code        BOOLEAN DEFAULT FALSE,
    code_snippet    TEXT,
    code_language   VARCHAR(50),
    error_message   TEXT,
    tokens_used     INTEGER DEFAULT 0,
    latency_ms      INTEGER DEFAULT 0,
    model_used      VARCHAR(100),
    was_helpful     BOOLEAN,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Code snapshots
CREATE TABLE IF NOT EXISTS code_snapshots (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES content_player_sessions(id) ON DELETE CASCADE,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    language        VARCHAR(50) NOT NULL,
    code            TEXT NOT NULL,
    error           TEXT,
    agent_feedback  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Indexes
CREATE INDEX idx_cp_sessions_user     ON content_player_sessions(user_id);
CREATE INDEX idx_cp_sessions_active   ON content_player_sessions(is_active, is_archived);
CREATE INDEX idx_cp_messages_session  ON content_player_messages(session_id);
CREATE INDEX idx_cp_messages_user     ON content_player_messages(user_id);
CREATE INDEX idx_code_snap_session    ON code_snapshots(session_id);

SELECT 'Content Player Agent tables created!' AS status;