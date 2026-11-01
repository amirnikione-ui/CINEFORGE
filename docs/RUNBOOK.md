# RUNBOOK — operations & troubleshooting

Implemented stack: FastAPI (+inline/celery jobs), Next.js studio, SQLite→Postgres, optional Redis.

## Commands (dev, no Docker)

```bash
make bootstrap      # backend venv + web deps
make api            # uvicorn :8000 (docs at /docs, health at /health)
make web            # next dev :3000
make worker         # celery worker (only if REDIS_URL reachable)
make test           # pytest backend/tests + tests/  (offline tier — zero keys)
make e2e            # brief → MP4 demo, in-process
```

## Docker (full stack)

```bash
cp .env.example .env
docker compose up --build          # api :8000 · web :3000 · postgres · redis
docker compose --profile slim up api web   # sqlite + inline executor, no db/redis
docker compose logs -f api         # director logs
```

## Failure matrix

| Symptom | Cause | Fix |
|---|---|---|
| `/health` shows only `mock` tiers | no API keys in env | expected offline; add `ZAI_API_KEY`/`OPENAI_API_KEY` etc. |
| chat 500 «director failed» | see api logs; usually provider chain exhausted | chain ends in mock → should never happen; file an issue |
| job stuck `running` | worker died mid-job | inline mode: check api logs; celery: `docker compose logs worker` |
| render fails «ffprobe failed» | output missing → check ffmpeg stderr in job error | usually font/frame issue; keep `fonts-dejavu-core` in image |
| drawtext missing in clips | no TTF found on host | install `fonts-dejavu-core` (apt) |
| `no such table: projects` | app started without lifespan (raw TestClient) | use `with TestClient(app)` |
| SQLAlchemy «Could not parse URL» | foreign `DATABASE_URL` injected by hosting | config.py auto-falls back to SQLite with a warning |
| remotion render fails | node/npm missing or deps not installed | worker image includes node; runner runs `npm install` lazily |

## Data & storage

- Root: `CINEFORGE_STORAGE_ROOT` (default `./storage`); layout `/<pid>/{storyboards,frames,audio,video,projects,analysis,work}`.
- `DELETE /api/projects/{id}` removes DB rows + storage tree (best-effort).
- Job work dirs under `/<pid>/work/<job_id>/` — safe to delete when no job is running.

## Provider transparency

`GET /health` → `providers.<capability>` = configured chain order. Every asset's
`meta.provider` records the tier that produced it. Mock tiers produce REAL artifacts
(Pillow frames, WAV narration/music bed, FFmpeg render) and are labeled as such.
