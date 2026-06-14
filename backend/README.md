# Backend API Server

This is the FastAPI-based Python REST backend for the Cognitive Voice Intelligence Platform. It manages evaluations, uploads audio payloads, orchestrates Faster-Whisper transcriber sequences, and calculates clinical scoring parameters.

---

## 🛠️ Requirements & Setup

Ensure Python 3.10+ is installed on your development system.

1.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install system dependencies**:
    *   **FFmpeg**: Faster-Whisper and audio processing pipelines require `ffmpeg` to be installed on the host OS.
        ```bash
        # macOS
        brew install ffmpeg
        
        # Ubuntu/Debian
        sudo apt-get install ffmpeg
        ```
3.  **Install python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚀 Running the Server

1.  Configure parameters inside the local `.env` file copied from the template in root.
2.  Launch the development server:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
3.  Open the documentation site at:
    *   **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
    *   **Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📁 Architecture Structure

```
backend/
├── requirements.txt            # Package listings
├── Dockerfile                  # Container configurations (placeholder)
├── .env.example                # Local configuration overrides
└── app/
    ├── __init__.py
    ├── main.py                 # Core app instance & middleware setups
    ├── core/
    │   ├── __init__.py
    │   └── config.py           # Global settings reader (Pydantic)
    ├── api/
    │   ├── __init__.py
    │   └── v1/                 # Version 1 Router handlers (placeholder stubs)
    ├── schemas/
    │   ├── __init__.py
    │   ├── session.py          # Pydantic schemas for Sessions
    │   └── analytics.py        # Pydantic schemas for Metrics & Risk scores
    └── services/
        ├── __init__.py
        ├── whisper_asr.py      # Faster-Whisper pipeline stub
        └── risk_engine.py      # Calculations calculator stub
```
