# CINEFORGE API + worker image (ADR-0008: same image, different command)
FROM python:3.12-slim

# ffmpeg for the video engine; node for the Remotion render path (ADR-0006b)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg fonts-dejavu-core nodejs npm curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY packages ./packages
COPY backend ./backend
COPY workers ./workers

# remotion template deps are installed lazily by cineforge_video.remotion.render_remotion

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
