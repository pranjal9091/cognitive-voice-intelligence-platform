# API Specification (OpenAPI / REST)

The Cognitive Voice Intelligence Platform exposes a REST API via FastAPI. This document defines the endpoints, request/response JSON schemas, and state flows for the API.

---

## 🧭 Endpoint Summary

All API endpoints are prefixed with `/api/v1`.

| HTTP Method | Path | Description | Access Role |
| :--- | :--- | :--- | :--- |
| **POST** | `/sessions` | Create a new evaluation session | Frontend Client / Clinician |
| **POST** | `/sessions/{id}/audio/{question_num}` | Upload audio recording for a question | Frontend Client |
| **POST** | `/sessions/{id}/process` | Trigger transcription, metrics & risk engine | Frontend Client |
| **GET** | `/sessions/{id}` | Retrieve comprehensive session results | Clinician / Frontend Client |
| **GET** | `/sessions` | Query list of sessions for dashboard | Clinician |
| **DELETE** | `/sessions/{id}` | Anonymize or delete a session | Administrator |

---

## 📡 Endpoint Details

### 1. Initialize Assessment Session
Creates a unique, anonymized assessment instance.

*   **Endpoint**: `POST /api/v1/sessions`
*   **Request Headers**: `Content-Type: application/json`
*   **Request Body**:
    ```json
    {
      "subject_reference": "SUBJ-94821",
      "clinician_id": "CLIN-0023"
    }
    ```
*   **Response (201 Created)**:
    ```json
    {
      "session_id": "7a35649b-73bc-4993-8ef2-ef389d31ac99",
      "status": "initialized",
      "subject_reference": "SUBJ-94821",
      "created_at": "2026-06-12T17:18:14Z",
      "questions": [
        { "number": 1, "prompt": "Tell us about your morning routine.", "status": "pending" },
        { "number": 2, "prompt": "Describe a memorable event from the last week.", "status": "pending" },
        { "number": 3, "prompt": "Talk about your favourite festival or celebration.", "status": "pending" }
      ]
    }
    ```

---

### 2. Upload Audio Recording
Receives binary audio data for a single assessment question prompt.

*   **Endpoint**: `POST /api/v1/sessions/{session_id}/audio/{question_number}`
*   **Request Headers**: `Content-Type: multipart/form-data`
*   **Request Body (Form Data)**:
    *   `audio_file`: Binary data (format: `.wav` or `.webm`, audio/wav, Mono, 16kHz, 16-bit PCM recommended)
    *   `duration_seconds`: Float (duration recorded in browser client)
*   **Path Parameters**:
    *   `session_id`: UUID
    *   `question_number`: Integer (Allowed values: `1`, `2`, `3`)
*   **Response (200 OK)**:
    ```json
    {
      "session_id": "7a35649b-73bc-4993-8ef2-ef389d31ac99",
      "question_number": 1,
      "status": "uploaded",
      "file_path": "/tmp/cognitive_voice_uploads/7a35649b-73bc-4993-8ef2-ef389d31ac99_q1.wav",
      "audio_size_bytes": 1048576,
      "recorded_duration": 42.5
    }
    ```

---

### 3. Trigger Session Processing
Starts the pipeline: transcribes all three uploaded audios, computes acoustic & linguistic metrics, calculates risk scores, and saves to database.

*   **Endpoint**: `POST /api/v1/sessions/{session_id}/process`
*   **Request Headers**: `Content-Type: application/json`
*   **Response (202 Accepted)**:
    ```json
    {
      "session_id": "7a35649b-73bc-4993-8ef2-ef389d31ac99",
      "status": "processing",
      "message": "Speech analytics calculation and risk scoring has been initiated.",
      "check_status_url": "/api/v1/sessions/7a35649b-73bc-4993-8ef2-ef389d31ac99"
    }
    ```

---

### 4. Fetch Session Results
Returns all transcripts, acoustic/temporal measurements, linguistic calculations, and the final risk assessment.

*   **Endpoint**: `GET /api/v1/sessions/{session_id}`
*   **Response (200 OK)**:
    ```json
    {
      "session_id": "7a35649b-73bc-4993-8ef2-ef389d31ac99",
      "status": "completed",
      "subject_reference": "SUBJ-94821",
      "clinician_id": "CLIN-0023",
      "created_at": "2026-06-12T17:18:14Z",
      "completed_at": "2026-06-12T17:20:05Z",
      "transcriptions": [
        {
          "question_number": 1,
          "transcript_text": "I woke up at six am, had coffee, and went for a run.",
          "duration": 12.5,
          "words": [
            { "word": "I", "start": 0.2, "end": 0.4, "probability": 0.99 },
            { "word": "woke", "start": 0.5, "end": 0.8, "probability": 0.98 }
          ]
        }
      ],
      "analytics": {
        "temporal_metrics": {
          "total_speech_duration": 42.5,
          "average_response_duration": 14.16,
          "words_per_minute": 110.2,
          "pause_count": 8,
          "longest_pause_seconds": 3.2
        },
        "linguistic_metrics": {
          "word_count": 142,
          "unique_word_count": 78,
          "repeated_words": [
            { "word": "and", "count": 12 },
            { "word": "coffee", "count": 3 }
          ],
          "filler_words_count": 9,
          "filler_words_breakdown": {
            "um": 5,
            "ah": 3,
            "like": 1
          }
        }
      },
      "risk_assessment": {
        "score": 0.32,
        "classification": "Low Risk",
        "rationale": "Speech tempo and linguistic structures are within standard normal limits. Pause counts represent typical speech breaks."
      }
    }
    ```

---

### 5. Query Session List
Lists sessions with filter controls for the clinician portal.

*   **Endpoint**: `GET /api/v1/sessions`
*   **Query Parameters**:
    *   `limit`: integer (default: `20`)
    *   `offset`: integer (default: `0`)
    *   `classification`: string (`Low Risk`, `Medium Risk`, `High Risk`)
*   **Response (200 OK)**:
    ```json
    {
      "total_count": 150,
      "items": [
        {
          "session_id": "7a35649b-73bc-4993-8ef2-ef389d31ac99",
          "subject_reference": "SUBJ-94821",
          "created_at": "2026-06-12T17:18:14Z",
          "status": "completed",
          "risk_classification": "Low Risk"
        }
      ]
    }
    ```

---

## 🚫 Standard Error Envelopes

The platform returns standard RFC 7807 problem details for errors.

### 404 Not Found (Session missing)
```json
{
  "detail": "Session with ID 7a35649b-73bc-4993-8ef2-ef389d31ac99 was not found."
}
```

### 422 Unprocessable Entity (Missing fields or invalid format)
```json
{
  "detail": [
    {
      "loc": ["body", "subject_reference"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 400 Bad Request (Uploading audio in wrong order)
```json
{
  "detail": "Cannot upload question 2 response before question 1 response is completed."
}
```
