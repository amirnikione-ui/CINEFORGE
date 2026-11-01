# docker/

- `backend.Dockerfile` — API + worker image (python:3.11-slim, ffmpeg, dejavu fonts).
  The compose `worker` service reuses it with `command: python -m workers.celery_app`.
- `web.Dockerfile` — Next.js studio UI (node:20-alpine, `npm run build` + `npm start`).

Owner: agent-03 (FORGE) per CF-018. Build: `docker compose build` from repo root.
