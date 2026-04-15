-- Migration: add question mastery tracking columns to content_player_sessions
-- Run in pgAdmin or psql

ALTER TABLE content_player_sessions
    ADD COLUMN IF NOT EXISTS solved_questions        JSON    DEFAULT '[]'::json,
    ADD COLUMN IF NOT EXISTS consecutive_easy_solves INTEGER DEFAULT 0;
