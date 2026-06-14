# Database Design Specification

The Cognitive Voice Intelligence Platform utilizes a relational **PostgreSQL** database. This document defines the schema, table constraints, indices, and ORM mapping design.

---

## 📊 Relational Database Schema ERD

```
  ┌─────────────────┐
  │    sessions     │
  ├─────────────────┤
  │ PK session_id   │◄┐
  │    subject_ref  │ │
  │    clinician_id │ │
  │    status       │ │
  │    created_at   │ │
  │    completed_at │ │
  └─────────────────┘ │
           │          │
           │ 1        │ 1
           ├──────────┼───────────────────────┐
           │ 1..N     │ 1                     │ 1
           ▼          ▼                       ▼
  ┌─────────────────┐┌─────────────────┐┌─────────────────┐
  │ audio_metadata  ││   transcripts   ││   risk_scores   │
  ├─────────────────┤├─────────────────┤├─────────────────┤
  │ PK audio_id     ││ PK transcript_id││ PK risk_id      │
  │ FK session_id   ││ FK session_id   ││ FK session_id   │
  │    question_num ││    question_num ││    score (float)│
  │    file_path    ││    full_text    ││    class (enum) │
  │    duration_sec ││    words_json   ││    rationale    │
  │    file_size    ││    confidence   ││    created_at   │
  │    created_at   ││    created_at   │└─────────────────┘
  └─────────────────┘└─────────────────┘
           │
           │ 1
           ├─────────────────────────┐
           │ 1                       │ 1
           ▼                         ▼
  ┌─────────────────┐       ┌─────────────────┐
  │temporal_metrics │       │linguistic_metric│
  ├─────────────────┤       │├────────────────┤
  │ PK temporal_id  │       │ PK linguistic_id│
  │ FK audio_id     │       │ FK audio_id     │
  │    speech_dur   │       │    word_count   │
  │    silence_dur  │       │    unique_words │
  │    wpm          │       │    repeated_json│
  │    pause_count  │       │    filler_json  │
  │    longest_pause│       │    lex_density  │
  └─────────────────┘       └─────────────────┘
```

---

## 🗄️ Database Tables Definition

### 1. `sessions`
Tracks the overall assessment process.
*   **Table Name**: `sessions`
*   **Columns**:
    *   `session_id` (UUID, Primary Key, Default: `uuid_generate_v4()`)
    *   `subject_reference` (VARCHAR(100), Indexed, Not Null) - Anonymized clinician reference code.
    *   `clinician_id` (VARCHAR(100), Indexed) - Relates to clinician identifying records.
    *   `status` (VARCHAR(30), Not Null) - Enum: `initialized`, `audio_uploading`, `processing`, `completed`, `failed`.
    *   `created_at` (TIMESTAMPTZ, Not Null, Default: `NOW()`)
    *   `completed_at` (TIMESTAMPTZ, Null)

---

### 2. `audio_metadata`
Stores reference details of the files uploaded per question.
*   **Table Name**: `audio_metadata`
*   **Columns**:
    *   `audio_id` (UUID, Primary Key, Default: `uuid_generate_v4()`)
    *   `session_id` (UUID, Foreign Key referencing `sessions.session_id` ON DELETE CASCADE, Not Null)
    *   `question_number` (INT, Not Null) - Question number (1, 2, or 3)
    *   `file_path` (VARCHAR(512), Not Null) - Location on server storage or S3 bucket.
    *   `duration_seconds` (FLOAT, Not Null)
    *   `file_size_bytes` (INT, Not Null)
    *   `created_at` (TIMESTAMPTZ, Not Null, Default: `NOW()`)
*   **Constraints**:
    *   Unique constraint on `(session_id, question_number)`.

---

### 3. `transcripts`
Holds word-level timestamps and the transcribed text.
*   **Table Name**: `transcripts`
*   **Columns**:
    *   `transcript_id` (UUID, Primary Key, Default: `uuid_generate_v4()`)
    *   `session_id` (UUID, Foreign Key referencing `sessions.session_id` ON DELETE CASCADE, Not Null)
    *   `question_number` (INT, Not Null)
    *   `full_text` (TEXT, Not Null) - The complete synthesized text.
    *   `words_json` (JSONB, Not Null) - Array of individual words with timestamps: `[{ "word": "example", "start": 0.1, "end": 0.5, "probability": 0.99 }]`.
    *   `confidence` (FLOAT, Not Null) - Average transcription confidence score.
    *   `created_at` (TIMESTAMPTZ, Not Null, Default: `NOW()`)
*   **Constraints**:
    *   Unique constraint on `(session_id, question_number)`.

---

### 4. `temporal_metrics`
Saves time-based speech signals extracted per audio file.
*   **Table Name**: `temporal_metrics`
*   **Columns**:
    *   `temporal_id` (UUID, Primary Key, Default: `uuid_generate_v4()`)
    *   `audio_id` (UUID, Foreign Key referencing `audio_metadata.audio_id` ON DELETE CASCADE, Unique, Not Null)
    *   `speech_duration_seconds` (FLOAT, Not Null) - Active duration minus pause segments.
    *   `words_per_minute` (FLOAT, Not Null) - Word count scaled to a 60-second window.
    *   `pause_count` (INT, Not Null) - Counts of pauses longer than a threshold (e.g., >250ms).
    *   `longest_pause_seconds` (FLOAT, Not Null)
    *   `speech_rate_ratio` (FLOAT, Not Null) - Active speech time divided by total duration.

---

### 5. `linguistic_metrics`
Stores linguistic structures parsed from the transcripts.
*   **Table Name**: `linguistic_metrics`
*   **Columns**:
    *   `linguistic_id` (UUID, Primary Key, Default: `uuid_generate_v4()`)
    *   `audio_id` (UUID, Foreign Key referencing `audio_metadata.audio_id` ON DELETE CASCADE, Unique, Not Null)
    *   `word_count` (INT, Not Null)
    *   `unique_word_count` (INT, Not Null)
    *   `repeated_words_json` (JSONB, Not Null) - Vocabulary repetition records: `{"word": count}`.
    *   `filler_words_json` (JSONB, Not Null) - Count of vocal fillers: `{"um": 4, "ah": 2}`.
    *   `lexical_density` (FLOAT, Not Null) - Ratio of content words (nouns, verbs, adjectives) to grammatical helper words.

---

### 6. `risk_scores`
Saves final classification outputs computed for a session.
*   **Table Name**: `risk_scores`
*   **Columns**:
    *   `risk_id` (UUID, Primary Key, Default: `uuid_generate_v4()`)
    *   `session_id` (UUID, Foreign Key referencing `sessions.session_id` ON DELETE CASCADE, Unique, Not Null)
    *   `score` (FLOAT, Not Null) - Aggregated risk score (normalized `0.0` to `1.0`).
    *   `classification` (VARCHAR(20), Not Null) - Enum: `Low Risk`, `Medium Risk`, `High Risk`.
    *   `rationale` (TEXT, Not Null) - Clinician-readable details explaining the classification trigger thresholds.
    *   `created_at` (TIMESTAMPTZ, Default: `NOW()`)

---

## ⚡ Indexing Optimization Strategy

To maintain sub-millisecond search performance in the clinician dashboard, the following indices are added:
1.  `idx_sessions_subject_reference`: B-tree index on `sessions(subject_reference)`.
2.  `idx_sessions_status`: B-tree index on `sessions(status)`.
3.  `idx_risk_scores_classification`: B-tree index on `risk_scores(classification)`.
4.  `idx_audio_session_id`: B-tree index on `audio_metadata(session_id)`. Reduces JOIN latency during temporal extraction checks.

---

## 🔄 Migration Plan (Alembic)

Database schema evolution will be managed via **Alembic** in the `database` folder:
*   **Alembic Directory**: Initialized in `database/alembic/`.
*   **Model Autogeneration**: Alembic is configured to scan SQLAlchemy declarative models defined under `database/models/` and match them against the active schema.
*   **Migration CLI commands**:
    *   Create migrations: `alembic -c database/alembic.ini revision --autogenerate -m "description"`
    *   Apply migrations: `alembic -c database/alembic.ini upgrade head`
