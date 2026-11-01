# CINEFORGE api image: FastAPI backend + video-engine (ffmpeg toolkit).
# The compose `worker` service reuses this image with a command override;
# worker.Dockerfile is the Node-capable variant for Remotion renders (CF-034).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg powers the video-engine toolkit; dejavu gives headless Pillow a default font.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first: code edits don't bust the pip layer cache.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Application code (paths per the ADR-0001 monorepo layout).
COPY backend /app/backend
COPY packages /app/packages
COPY workers /app/workers
COPY scripts /app/scripts

# Packages are plain source (no install step yet) — put them on sys.path.
ENV PYTHONPATH=/app/packages/ai-providers:/app/packages/video-engine:/app/packages/ai-agent:/app

# Non-root runtime; /data is the storage volume mount point (compose: cineforge_media).
RUN useradd --create-home --uid 1000 cineforge \
    && mkdir -p /data \
    && chown -R cineforge:cineforge /data /app
USER cineforge

EXPOSE 8000
WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
