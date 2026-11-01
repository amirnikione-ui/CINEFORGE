# CINEFORGE API + worker image (python:3.11-slim + ffmpeg + dejavu fonts)
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY backend/requirements.txt /srv/backend/requirements.txt
RUN pip install --no-cache-dir -r /srv/backend/requirements.txt

COPY backend /srv/backend
COPY packages /srv/packages
COPY workers /srv/workers
COPY scripts /srv/scripts

ENV PYTHONPATH=/srv:/srv/backend:/srv/packages/ai-providers:/srv/packages/video-engine \
    CINEFORGE_STORAGE_ROOT=/data/storage \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# default: API. The worker service overrides the command (see docker-compose.yml).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
