-- ============================================================
-- migration_updates.sql
-- Run this in pgAdmin on your aita_db database
-- This adds all columns needed for the new features
-- ============================================================

-- 1. Add interested_topics to users table
--    (topics saved at registration, shared across all agents)
ALTER TABLE users 
  ADD COLUMN IF NOT EXISTS interested_topics JSON DEFAULT '[]';

-- 2. Add difficulty to content_player_sessions
--    (tracks adaptive difficulty per session)
ALTER TABLE content_player_sessions 
  ADD COLUMN IF NOT EXISTS difficulty VARCHAR(20) DEFAULT 'medium';

-- ============================================================
-- Verify the changes
-- ============================================================
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name IN ('users', 'content_player_sessions')
  AND column_name IN ('interested_topics', 'difficulty')
ORDER BY table_name, column_name;