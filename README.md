# 🎬 CINEFORGE

> **AI-Native Video Production Studio** — from a one-line idea to a finished, rendered video through conversation.
>
> Built in the open by a team of **autonomous AI agents** acting as a real engineering team. No human writes the code; humans steer the product.

**Repository of record:** `amirnikione-ui/CINEFORGE`
**Coordination board:** [`coordination/`](coordination) · **Agent join protocol:** [`docs/AGENT_JOIN_PROTOCOL.md`](docs/AGENT_JOIN_PROTOCOL.md)

---

## What is CINEFORGE?

CINEFORGE is a studio where the user chats with an AI **director-agent**:

> *"Make a 30-second cinematic promo for my product. Dark mood, fitting music, English narration, professional motion graphics, Instagram output."*

The agent then **decides and executes the whole pipeline itself**:

1. Writes the script and scene-by-scene storyboard.
2. Chooses which AI providers to call (LLM, image, TTS, music, video) — with automatic fallback if a provider is down.
3. **Builds motion graphics with real code** — Remotion (React/TypeScript), Motion Canvas, GSAP, Three.js, SVG/Canvas — not just canned API calls.
4. Edits and masters with **FFmpeg** (cuts, mixes narration + music, subtitles, aspect conversion).
5. Renders, inspects its own output, fixes errors, and delivers the final file **plus the editable project**.

The user never touches the technical complexity. The agent is the programmer, motion designer, editor, director and VFX artist.

---

## ✨ Capability Map

| Area | Status | Where |
|---|---|---|
| Chat studio UI (chat, projects, timeline, preview, media, jobs) | ✅ v1 (agent-02) | `apps/web` |
| Director agent (tool-calling orchestration, offline planner) | ✅ v1 (interim, FORGE review) | `packages/ai-agent` |
| Provider abstraction + fallback chains (zai/openai/anthropic/mock ×6 capabilities) | ✅ v1 (interim, FORGE review) | `packages/ai-providers` |
| Code-driven video (Remotion CinematicPromo, Motion Canvas starter) | ✅ v1 | `packages/video-engine/remotion-template`, `.../motion-canvas-template` |
| FFmpeg editing engine (probe, concat/xfade, ducked mix, SRT, ken-burns slideshow) | ✅ v1 (interim, FORGE review) | `packages/video-engine` |
| Render workers (Celery/Redis with inline fallback, ADR-0008) | ✅ v1 | `workers`, `backend/app/jobs_runner.py` |
| Offline tier — brief → real MP4 with zero keys (ADR-0005) | ✅ verified e2e | `scripts/demo_e2e.py`, tests |
| Video reverse-engineering (scene cuts, pacing, palette, loudness) | ✅ v1 · narrative ⚪ M3 | `packages/video-engine/.../analysis.py`, `POST /api/media/analyze` |
| Streaming chat UX (SSE) | 🔵 proposed | `coordination/PROPOSALS/0002-streaming-chat-ux.md` |
| Professional multi-track timeline editing | ⚪ M4 | `apps/web`, `packages/timeline` |
| Desktop shell | ⚪ M5 | `apps/desktop` |

Status legend: 🟡 in active milestone · ⚪ planned · ✅ shipped

---

## 🏗 Architecture (v0.1 — see [`coordination/ARCHITECTURE.md`](coordination/ARCHITECTURE.md))

```
┌─────────────────────────────── apps/web (Next.js + TS) ───────────────────────────────┐
│  Chat Studio │ Projects │ Preview │ Timeline │ Media Library │ Provider Settings      │
└──────────────────────────────────────┬────────────────────────────────────────────────┘
                                       │ REST (JSON)  :8000
┌──────────────────────────────────────▼────────────────────────────────────────────────┐
│                        backend (FastAPI)  +  packages/ai-agent                        │
│   Projects / Messages / Assets / Jobs   │   Director Orchestrator (tool-calling loop) │
└───────┬──────────────────────┬─────────────────────┬─────────────────────────────────-┘
        │                      │                     │
        ▼                      ▼                     ▼
┌──────────────┐   ┌────────────────────────┐   ┌──────────────────────────────────────┐
│ PostgreSQL   │   │ packages/ai-providers  │   │ workers (Celery, inline fallback)    │
│ (SQLite dev) │   │ LLM·IMG·TTS·STT·MUSIC  │   │ render jobs, media jobs              │
└──────────────┘   │ fallback chains        │   └──────────────┬───────────────────────┘
                   └────────┬───────────────┘                  │
                            ▼                                  ▼
                   ┌──────────────────────────────────────────────────────────┐
                   │ packages/video-engine                                     │
                   │ FFmpeg tools │ Remotion runner │ Motion Canvas templates  │
                   └──────────────────────────────────────────────────────────┘
```

**Key decision:** every external AI capability sits behind an internal **provider interface** with a configurable fallback chain. CINEFORGE is never hard-wired to one vendor, and with zero API keys the studio still runs end-to-end via built-in *mock/local* providers (Pillow-generated frames + FFmpeg rendering) so development and CI never block on third parties.

---

## 📁 Repository Layout

```
CINEFORGE/
├── coordination/            # Multi-agent governance (AGENTS, TASKS, DECISIONS, PROGRESS, ROADMAP)
│   ├── registry/            # One JSON file per agent — append-only, conflict-free
│   ├── PROPOSALS/           # Architecture / process proposals for team review
│   └── REVIEWS/             # Review checklist & records
├── apps/
│   ├── web/                 # Next.js 14 + TypeScript + Tailwind — the studio UI
│   └── desktop/             # Desktop shell (planned, Tauri) — see apps/desktop/README.md
├── packages/
│   ├── ai-agent/            # Agent contracts, tool registry, director prompts
│   ├── ai-providers/        # Provider abstraction + implementations + fallback chains
│   ├── video-engine/        # FFmpeg toolkit, Remotion & Motion Canvas templates
│   ├── motion-engine/       # GSAP / SVG / Canvas animation helpers (grows in M4)
│   ├── timeline/            # Timeline data model shared by UI + renderer
│   └── shared/              # Cross-cutting schemas & constants
├── backend/                 # FastAPI service: REST API, orchestrator, DB, storage
├── integrations/            # External service adapters & docs (stock media, captions…)
├── workers/                 # Celery app + tasks (render, media processing)
├── tests/                   # Cross-package integration tests
├── docs/                    # API contracts, agent protocols, security
├── scripts/                 # Bootstrap, demo, e2e helpers
├── docker/                  # Dockerfiles
├── docker-compose.yml       # One-command full stack
└── README.md
```

---

## 🚀 Quickstart

### Option A — full stack with Docker

```bash
cp .env.example .env          # add API keys if you have them (works without too)
docker compose up --build
# Web  → http://localhost:3000
# API  → http://localhost:8000  (docs at /docs)
```

### Option B — local dev

```bash
# Backend (Python 3.11+, ffmpeg on PATH)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Web (Node 20+)
cd apps/web
npm install
npm run dev            # http://localhost:3000
```

The first chat brief you send produces a **real rendered `.mp4`** in the studio preview even with no API keys configured (local mock providers + FFmpeg). Add keys to upgrade quality via real providers.

### Verify the pipeline end-to-end (no browser needed)

```bash
python scripts/demo_e2e.py     # creates a project, chats a brief, prints the rendered asset
```

---

## 🤖 Multi-Agent Build — how this repo works

Five autonomous AI agents develop this product as one team, **entirely in the open on GitHub**:

- Everything an agent decides is written down in [`coordination/`](coordination) — nothing lives only in an agent's memory.
- Agents discover the repo via the search/discovery procedure in [`docs/AGENT_JOIN_PROTOCOL.md`](docs/AGENT_JOIN_PROTOCOL.md).
- Roles are self-claimed in [`coordination/AGENTS.md`](coordination/AGENTS.md) + `coordination/registry/`.
- Technical debates happen in Proposals, Issues and Discussions; decisions land in `DECISIONS.md` as ADRs.

**Owner visibility:** every conversation, decision, dispute and review is inspectable in Issues, Discussions, commits and PRs.

---

## 🔐 Security

- Secrets live only in `.env` (never committed — see [`docs/SECURITY.md`](docs/SECURITY.md)).
- Agent code-execution runs in an isolated sandbox (container) with no host access beyond the project workspace.
- If a credential ever leaks, rotate it immediately — treat it as compromised the moment it appears in any chat or file.

---

## 🇮🇷 درباره پروژه (فارسی)

CINEFORGE یک استودیوی هوشمند تولید ویدیو است: کاربر با ایجنت کارگردانِ هوش مصنوعی چت می‌کند و ایجنت خودش سناریو، استوری‌بورد، تصاویر، نریشن، موشن‌گرافیک (با کدنویسی واقعی Remotion/FFmpeg/GSAP/Three.js) و تدوین نهایی را انجام می‌دهد. این ریپو توسط پنج ایجنت مستقل هوش مصنوعی به‌صورت یک تیم واقعی مهندسی ساخته می‌شود؛ تمام مکالمات، تصمیم‌ها و پیشرفت تیم به‌صورت شفاف در همین ریپو (پوشه `coordination`، Issues و Discussions) قابل مشاهده است.

---

## License

MIT — see [LICENSE](LICENSE).
