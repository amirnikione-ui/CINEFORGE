# RUNBOOK — operations & troubleshooting

## Local dev (no Docker)

```bash
python3 -m venv backend/.venv && . backend/.venv/bin/activate
pip install -r backend/requirements.txt && pip install -e ./packages/video-engine
cd backend && uvicorn app.main:app --reload --port 8000      # API + inline jobs
cd apps/web && npm install && npm run dev                     # studio :3000
# optional Celery tier (needs REDIS_URL): python -m workers.celery_app  (repo root)
```

Tests: `pytest backend/tests packages/video-engine/tests -q` (offline tier, zero keys).
E2E demo: `python scripts/demo_e2e.py` (in-process) or `python scripts/demo_e2e.py --serve http://localhost:8000 --duration 12`.

## Docker (full stack — images by FORGE, PR #28/#37)

```bash
cp -n .env.example .env
docker compose up --build        # api :8000 · worker · web :3000 · postgres · redis
docker compose logs -f api       # director + render logs
docker compose --profile slim up api web   # sqlite + inline executor, no db/redis
```

`docker/backend.Dockerfile` serves api and worker (`python -m workers.celery_app` from repo
root) with ffmpeg + dejavu fonts. Requirements include `celery[redis]` + `psycopg[binary]`
(compose worker imports celery; compose `DATABASE_URL` is `postgresql+psycopg`).

## Failure matrix

| Symptom | Cause | Fix |
|---|---|---|
| LLM provider `mock` in `/health` | no `LLM_API_KEY`/`LLM_BASE_URL` | expected offline; add key for online tier |
| `Could not parse SQLAlchemy URL` at import | foreign injected `DATABASE_URL` (e.g. `file:…`) | tests force-isolate (conftest); runtime: set a valid URL |
| worker crashes: `ModuleNotFoundError: celery` | deps not installed | `pip install -r backend/requirements.txt` (includes celery) |
| worker: `ModuleNotFoundError: app` | wrong cwd | run `python -m workers.celery_app` from repo root |
| job stuck `running` | worker died mid-render | `docker compose logs worker`; inline: api logs |
| render failed, no output | ffmpeg error in `job.error` tail | fonts (`fonts-dejavu-core`), frame assets present |
| remotion render fails | node deps | install node ≥18; template `npm install` lazy |
| `no such table` in tests | lifespan not run | use `with TestClient(app)` |

## Data

`STORAGE_ROOT` (settings) holds `/<pid>/…` assets; `DELETE /api/projects/{id}` purges DB + files.
Security: secrets via env only; CI secret-guard scans for PAT-looking strings; sandbox hardening CF-061.
