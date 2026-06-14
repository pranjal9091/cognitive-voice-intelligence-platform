# ==============================================================================
# Dockerfile - Cognitive Voice Intelligence Platform Backend
# Note: Designed for future GPU support (CUDA) if Faster-Whisper requires it.
# ==============================================================================

FROM python:3.10-slim AS builder

WORKDIR /build

# Install compilation requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Production Stage ---
FROM python:3.10-slim AS runner

WORKDIR /app

# Install FFmpeg (Critical dependency for audio transcoding and faster-whisper)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed libraries from builder
COPY --from=builder /root/.local /root/.local
COPY backend/app /app/app
# Expose database module as shared dependency path if needed
COPY database /app/database

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

EXPOSE 8000

# Run FastAPI using uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
