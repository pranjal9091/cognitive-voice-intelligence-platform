# ==============================================================================
# Dockerfile - Hugging Face Spaces Backend Deployment
# ==============================================================================

FROM python:3.10-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Runner Stage ---
FROM python:3.10-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY backend/app /app/app
COPY database /app/database

# Create storage directory and set open permissions for Hugging Face user (UID 1000)
RUN mkdir -p /app/storage/audio/sessions && chmod -R 777 /app/storage

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PORT=7860

EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 7860"]
