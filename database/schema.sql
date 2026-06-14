-- ==============================================================================
-- SQL Schema Setup - Cognitive Voice Intelligence Platform
-- Target: PostgreSQL 15+
-- ==============================================================================

-- Enable UUID extension if not active
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_reference VARCHAR(100) NOT NULL,
    clinician_id VARCHAR(100) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'initialized',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL
);

-- Indexing sessions for performance
CREATE INDEX IF NOT EXISTS idx_sessions_subject_reference ON sessions(subject_reference);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

-- 2. Audio Metadata Table
CREATE TABLE IF NOT EXISTS audio_metadata (
    audio_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    question_number INT NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    duration_seconds FLOAT NOT NULL,
    file_size_bytes INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    CONSTRAINT unique_session_question UNIQUE (session_id, question_number)
);

CREATE INDEX IF NOT EXISTS idx_audio_session_id ON audio_metadata(session_id);

-- 3. Transcripts Table
CREATE TABLE IF NOT EXISTS transcripts (
    transcript_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    question_number INT NOT NULL,
    full_text TEXT NOT NULL,
    words_json JSONB NOT NULL,
    confidence FLOAT NOT NULL,
    language VARCHAR(10) NULL,
    language_probability DOUBLE PRECISION NULL,
    average_segment_confidence DOUBLE PRECISION NULL,
    processing_time_seconds FLOAT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    CONSTRAINT unique_session_transcript UNIQUE (session_id, question_number)
);

CREATE INDEX IF NOT EXISTS idx_transcripts_session_id ON transcripts(session_id);

-- 4. Temporal Metrics Table
CREATE TABLE IF NOT EXISTS temporal_metrics (
    temporal_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_id UUID NOT NULL UNIQUE,
    speech_duration_seconds FLOAT NOT NULL,
    words_per_minute FLOAT NOT NULL,
    pause_count INT NOT NULL,
    longest_pause_seconds FLOAT NOT NULL,
    speech_rate_ratio FLOAT NOT NULL,
    FOREIGN KEY (audio_id) REFERENCES audio_metadata(audio_id) ON DELETE CASCADE
);

-- 5. Linguistic Metrics Table
CREATE TABLE IF NOT EXISTS linguistic_metrics (
    linguistic_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audio_id UUID NOT NULL UNIQUE,
    word_count INT NOT NULL,
    unique_word_count INT NOT NULL,
    repeated_words_json JSONB NOT NULL,
    filler_words_json JSONB NOT NULL,
    lexical_density FLOAT NOT NULL,
    FOREIGN KEY (audio_id) REFERENCES audio_metadata(audio_id) ON DELETE CASCADE
);

-- 6. Risk Scores Table
CREATE TABLE IF NOT EXISTS risk_scores (
    risk_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE,
    score FLOAT NOT NULL,
    classification VARCHAR(20) NOT NULL,
    rationale TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_risk_scores_classification ON risk_scores(classification);
