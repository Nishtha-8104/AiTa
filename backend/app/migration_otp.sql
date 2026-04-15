-- Migration: Add OTP records table for 2-step login verification
-- Run this in pgAdmin or psql before starting the server

CREATE TABLE IF NOT EXISTS otp_records (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hashed_otp  VARCHAR(255) NOT NULL,   -- bcrypt hash, raw OTP never stored
    expires_at  TIMESTAMPTZ NOT NULL,
    is_used     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_otp_records_user_id ON otp_records(user_id);
