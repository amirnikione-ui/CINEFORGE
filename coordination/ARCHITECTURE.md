# CINEFORGE — Architecture (v0.1)

> Living document. Changes require an ADR in `DECISIONS.md` and, if interfaces change, an update to `docs/API_CONTRACTS.md`.

## 1. System overview

```
                        ┌────────────────────────────────────────────┐
                        │              apps/web  :3000               │
                        │  Next.js 14 · React 18 · TS · Tailwind     │
                        │  Chat Studio · Projects · Preview ·        │
                        │  Timeline v1 · Media · Provider Status     │
                        └───────────────┬────────────────────────────┘
                                        │ REST/JSON (fetch, typed client)
                        ┌───────────────▼────────────────────────────┐
                        │              backend  :8000                │
                        │  FastAPI + Pydantic v2 + SQLAlchemy 2      │
                        │  ┌──────────────────────────────────────┐  │
                        │  │  Director Orchestrator               │  │
                        │  │  (packages/ai-agent)                 │  │
                        │  │  plan → tool calls → verify → reply  │  │
                        │  └───────┬──────────────────┬───────────┘  │
                        │          │                  │              │
                        │  ┌───────▼────────┐  ┌──────▼───────────┐  │
                        │  │ ai-providers   │  │ Job Runner       │  │
                        │  │ chains+fallback│  │ inline | celery  │  │
                        │  └───────┬────────┘  └──────┬───────────┘  │
                        └──────────┼──────────────────┼──────────────┘
                                   │                  │
             ┌─────────────────────▼───┐      ┌───────▼─────────────────────┐
             │ packages/video-engine   │      │ workers/ (celery app+tasks) │
             │ ffmpeg toolkit: probe,  │      │ render_project, media jobs  │
             │ scdet, cut, concat, mix,│      └───────┬─────────────────────┘
             │ subtitles, ken-burns,   │              │
             │ remotion runner,        │              │
             │ motion-canvas templates │              │
             └─────────────────────┬───┘              │
                                   ▼                  ▼
                        ┌────────────────────────────────────┐
                        │  Storage: backend/storage/<pid>/   │
                        │  frames/ audio/ video/ storyboards │
                        │  (S3 adapter in M5)                │
                        └────────────────────────────────────┘
```

## 2. Components & ownership

| Component | Tech | Purpose | Owner path |
|---|---|---|---|
| `apps/web` | Next.js 14, TS, Tailwind | Studio UI: chat, projects, preview, timeline, media, provider status | agent-02 |
| `backend` | FastAPI, SQLAlchemy | REST API, persistence, storage, orchestrator host | agent-03 |
| `packages/ai-agent` | Python | Tool registry, director prompts, plan/execute contracts | agent-03 |
| `packages/ai-providers` | Python | Capability interfaces + provider impls + fallback chains | agent-03 |
| `packages/video-engine` | Python + FFmpeg, Remotion (TS) | Real media processing + code-driven video | agent-04 |
| `packages/motion-engine` | TS/Python | GSAP/SVG/Canvas/Three helpers (M4+) | agent-04 |
| `packages/timeline` | TS + Python mirror | Timeline data model shared UI↔renderer | agent-02 + agent-04 |
| `packages/shared` | TS + Python | Schemas (storyboard, job, asset), constants | all (PRs) |
| `workers` | Celery + inline fallback | Background execution of render/media jobs | agent-05 |
| `integrations` | Python/TS adapters | External services (stock media, captions, music libs) | agent-05 |
| `docker`, CI, sandbox | Docker, GH Actions | Build/run/security | agent-05 |

## 3. Request flow — "brief to video"

```
1. POST /api/projects {title, brief}
2. POST /api/projects/{id}/chat {message}
      → user message persisted
      → Director orchestrator:
          a. PLAN   : LLM (chain) or deterministic mock-director → step list
          b. EXECUTE: tools:
               write_storyboard        → storyboards/storyboard.json (asset)
               generate_concept_frames → frames/scene-XX.png       (assets)
               generate_narration      → audio/scene-XX.mp3|wav    (assets)
               render_slideshow        → video/final_*.mp4         (asset, FFmpeg)
               build_remotion_project  → remotion project files    (editable project)
               probe_media / analyze   → QA metadata
          c. VERIFY  : ffprobe duration/streams; retry on failure
      → assistant message (summary + artifact links) persisted
3. UI polls GET /api/projects/{id} → messages, assets, jobs
4. Preview plays GET /api/assets/{id}/file (mp4)
```

## 4. Provider chains (ADR-0004/0005)

```
CINEFORGE_LLM_CHAIN=zai,openai,anthropic,mock
CINEFORGE_IMAGE_CHAIN=openai,mock
CINEFORGE_TTS_CHAIN=openai,elevenlabs,mock
CINEFORGE_STT_CHAIN=openai,mock
CINEFORGE_MUSIC_CHAIN=mock
CINEFORGE_VIDEO_CHAIN=mock
```

Registry resolves a capability → ordered providers → first `available()` (key present / local capability) wins → call errors trigger next provider. Every result carries `meta.provider` for full transparency. `mock` always available, produces real local artifacts.

## 5. Data model (v0.1)

- **Project**: id, title, brief, style, platform, status, created_at
- **Message**: id, project_id, role(user|assistant|system), content, meta(JSON)
- **Asset**: id, project_id, kind(storyboard|frame|audio|video|analysis|project), path, meta(JSON: provider, prompt, duration…)
- **Job**: id, project_id, kind(render|generate|analyze), status(pending|running|done|failed), progress, result(JSON), error

SQLite for dev (`sqlite:///./cineforge.db`), Postgres in compose. WAL mode on SQLite.

## 6. Ports, env, commands

| Service | Port | Notes |
|---|---|---|
| web | 3000 | `npm run dev` |
| api | 8000 | `uvicorn app.main:app`, docs at `/docs` |
| postgres | 5432 | compose only |
| redis | 6379 | optional |

Key env vars: see `.env.example`. Commands: see `Makefile`.

## 7. Security posture (v0.1, hardening in M5)

- Secrets only via env; `.env` git-ignored.
- FFmpeg invoked with argv lists (no shell), workspace-confined paths.
- Agent code execution: inside worker/container, timeouts everywhere (ADR-0009).
- Uploads type/size-checked before probing.
