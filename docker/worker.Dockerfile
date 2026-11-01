# CINEFORGE render worker: python pipeline + Node toolchain for `remotion render`
# (ADR-0006 path b). Debian bookworm ships Node 18 — meets Remotion's >=16 floor;
# bump to Node 20 via nodesource if a newer Remotion requires it.
# First Remotion render downloads Chrome Headless Shell; pre-bake it with
# `npx remotion browser ensure` during image hardening (CF-034/CF-061).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg for the video toolkit; nodejs+npm for Remotion renders.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY packages /app/packages
COPY workers /app/workers
COPY scripts /app/scripts

ENV PYTHONPATH=/app/packages/ai-providers:/app/packages/video-engine:/app/packages/ai-agent:/app

# Non-root runtime; /data is the shared storage volume.
RUN useradd --create-home --uid 1000 cineforge \
    && mkdir -p /data \
    && chown -R cineforge:cineforge /data /app
USER cineforge

WORKDIR /app
CMD ["python", "-m", "workers.celery_app"]
