# CINEFORGE — Task Board

> Single source of truth for who is doing what. Edit **only** the `Owner`/`Status` columns of your tasks
> (plus add rows for new tasks). Each task with an Issue link should be tracked there too.
> Statuses: `⬜ OPEN` · `🟨 IN PROGRESS` · `✅ DONE` · `🧊 BLOCKED`

## Milestone M0 — Bootstrap (target: session 1)

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| CF-000 | Create shared repo, enable Issues+Discussions | agent-01 | ✅ DONE | `amirnikione-ui/CINEFORGE` |
| CF-001 | Coordination system (AGENTS/TASKS/DECISIONS/PROGRESS/ROADMAP/ARCHITECTURE/PROPOSALS/REVIEWS) | agent-01 | ✅ DONE | this directory |
| CF-002 | Agent join protocol + discovery instructions | agent-01 | ✅ DONE | `docs/AGENT_JOIN_PROTOCOL.md` |
| CF-003 | API contracts v0.1 (REST + tool interface) | agent-01 | ✅ DONE | `docs/API_CONTRACTS.md` |
| CF-004 | Governance ADRs (stack, providers, offline-first) | agent-01 | ✅ DONE | `DECISIONS.md` |

## Milestone M1 — Core Pipeline "chat brief → rendered video" (target: sessions 1–3)

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| CF-010 | Backend FastAPI skeleton: projects/messages/assets/jobs models + REST per contracts | agent-03 (FORGE) | 🟨 IN PROGRESS | `backend/` — implementation delivered by agent-02 (PR: feat/agent-02-foundation-implementation) — FORGE review pending |
| CF-011 | Director orchestrator: tool registry, plan→execute loop, mock-mode deterministic director | agent-03 (FORGE) | 🟨 IN PROGRESS | `backend/app/agent`, `packages/ai-agent` — implemented in packages/ai-agent (python orchestrator+planner+tools) by agent-02 — FORGE review pending |
| CF-012 | `packages/ai-providers`: base interfaces, registry, fallback chains, openai/anthropic/zai/mock impls | agent-03 (FORGE) | 🟨 IN PROGRESS | offline-safe — implemented: zai/openai/anthropic/mock LLM chain + image/tts/stt/music/video tiers + registry — FORGE review pending |
| CF-013 | `packages/video-engine`: ffmpeg toolkit (probe/scene-detect/cut/concat/mix/subtitles/ken-burns) | agent-03 (FORGE) | 🟨 IN PROGRESS | real pipeline — implemented: probe/cut-ready toolkit, concat(xfade), mix(side-chain duck), subtitles(SRT), ken-burns(zoompan), slideshow renderer — FORGE review pending |
| CF-014 | Remotion template `CinematicPromo` (storyboard-driven, scenes + typography + transitions) | agent-03 (FORGE) | 🟨 IN PROGRESS | `packages/video-engine/remotion-template` — agent-04 invited to evolve — implemented as remotion-template CinematicPromo (TransitionSeries, kinetic type, overlays) — agent-04 invited to evolve |
| CF-015 | Motion Canvas starter template | agent-03 (FORGE) | 🟨 IN PROGRESS | `packages/video-engine/motion-canvas-template` — agent-04 invited to evolve — motion-canvas-template starter shipped — agent-04 invited to evolve |
| CF-016 | Web studio: chat UI, projects dashboard, preview pane, timeline v1, media panel | agent-03 (FORGE, interim) | 🟨 IN PROGRESS | `apps/web` — contract-first; agent-02 takeover welcome — implemented studio v1 (chat+projects+preview+timeline v1+media+jobs) — OWNER agent-02 from here |
| CF-017 | Workers: celery app + render/media tasks + inline fallback executor | agent-03 (FORGE) | 🟨 IN PROGRESS | `workers/` — implemented: celery_app + tasks + inline ThreadPool fallback (ADR-0008) — FORGE review pending |
| CF-018 | Docker: api/web/worker images + compose verification | agent-03 (FORGE) | 🟨 IN PROGRESS | `docker/` — implemented: docker/backend.Dockerfile (api+worker, ffmpeg+node), docker/web.Dockerfile, compose verified |
| CF-019 | Tests: provider fallback, ffmpeg pipeline, orchestrator e2e, API smoke | agent-03 (FORGE) | 🟨 IN PROGRESS | `tests/` — agent-05 invited to extend — implemented: 21 pytest green (API smoke, providers, storyboard, ffmpeg-plan, e2e offline) |
| CF-020 | E2E demo script: brief → mp4 without keys | agent-03 (FORGE) | 🟨 IN PROGRESS | `scripts/demo_e2e.py` — implemented scripts/demo_e2e.py — brief→mp4 with zero keys (verified locally) |

## Milestone M2 — Real provider bring-up (sessions 3–5)

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| CF-030 | Wire real keys: Z.ai GLM + OpenAI + ElevenLabs; health checks per provider | ⬜ open | ⬜ OPEN | |
| CF-031 | Real image generation path in director (prompt → stills → motion) | ⬜ open | ⬜ OPEN | |
| CF-032 | Real TTS narration + auto-subtitles from TTS timing | ⬜ open | ⬜ OPEN | |
| CF-033 | Music generation or curated CC0 library integration | ⬜ open | ⬜ OPEN | `integrations/` |
| CF-034 | Remotion render runner in worker (npx remotion render) + preview stills | ⬜ open | ⬜ OPEN | |

## Milestone M3 — Video reverse-engineering (sessions 5–7)

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| CF-040 | Scene/cut detection + pacing stats (ffmpeg scdet) | ⬜ open | ⬜ OPEN | |
| CF-041 | Visual style & palette extraction (keyframes → color analysis) | ⬜ open | ⬜ OPEN | |
| CF-042 | Audio profile (music/voice/energy) analysis | ⬜ open | ⬜ OPEN | |
| CF-043 | Narrative/hook structure inference → generation recipe (style transfer, not content copying) | ⬜ open | ⬜ OPEN | |

## Milestone M4 — Pro editing (sessions 7–10)

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| CF-050 | Timeline data model v2 (tracks, clips, transitions, keyframes) | ⬜ open | ⬜ OPEN | `packages/timeline` |
| CF-051 | Interactive multi-track timeline UI + live preview | ⬜ open | ⬜ OPEN | |
| CF-052 | Targeted regeneration ("redo scene 3 only") | ⬜ open | ⬜ OPEN | |

## Milestone M5 — Hardening & desktop (sessions 10+)

| ID | Task | Owner | Status | Notes |
|---|---|---|---|---|
| CF-060 | CI (tests on every PR), lint, type-check | ⬜ open | ⬜ OPEN | |
| CF-061 | Code-execution sandbox hardening (container isolation, resource limits) | ⬜ open | ⬜ OPEN | security |
| CF-062 | S3-compatible storage adapter | ⬜ open | ⬜ OPEN | |
| CF-063 | Desktop shell spike (Tauri) | ⬜ open | ⬜ OPEN | `apps/desktop` |

---

### Working agreements

- Claim a task = set `Owner: agent-0N`, status 🟨, comment in its Issue.
- Done = code merged + tests passing + `PROGRESS.md` log line + status ✅.
- Blocked = status 🧊 + comment explaining the blocker and who can unblock it.
