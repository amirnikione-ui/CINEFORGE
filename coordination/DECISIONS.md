# CINEFORGE — Decision Log (ADR-style)

> Every significant technical decision is recorded here. Format: **ADR-NNNN — Title** · Status · Date · Owner · Context → Decision → Consequences.
> Disagree? Open a comment in the linked Proposal/Issue; ADRs can be `Superseded`, never silently rewritten.

---

## ADR-0001 — Monorepo layout
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01 · **Proposal:** PROPOSALS/0001
**Context:** Five agents developing interdependent packages (UI, agent, providers, engines) in parallel.
**Decision:** Single repository with `apps/`, `packages/`, `backend/`, `workers/` mirroring the mission structure. Shared contracts in `docs/API_CONTRACTS.md`; per-agent ownership by path (see `AGENTS.md`).
**Consequences:** Atomic cross-cutting changes, one PR history for the owner to audit; requires branch/rebase discipline to avoid shared-file conflicts.

## ADR-0002 — Frontend: Next.js 14 + TypeScript + Tailwind
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01 · **Proposal:** PROPOSALS/0001
**Context:** The studio needs a chat-first UI with dashboard, preview and timeline; the mission shortlists Next.js.
**Decision:** Next.js 14 (App Router) + React 18 + TypeScript + Tailwind CSS 3. Hand-rolled dark "studio" components (no heavy UI kit) to keep installs fast and code auditable.
**Consequences:** SSR not critical for the app shell; `NEXT_PUBLIC_API_URL` points at FastAPI. Desktop later wraps the same UI (Tauri).

## ADR-0003 — Backend: FastAPI + SQLAlchemy (SQLite dev / PostgreSQL prod)
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01
**Context:** Media pipelines need background jobs, file storage, and typed APIs; mission shortlists Python+FastAPI.
**Decision:** FastAPI + Pydantic v2 + SQLAlchemy 2. `DATABASE_URL` defaults to SQLite for zero-config dev; Postgres in compose/prod. Storage: local FS `CINEFORGE_STORAGE_ROOT` (S3 adapter later, CF-062).
**Consequences:** Sync endpoints run in FastAPI's threadpool; long jobs always become `Job` rows so the UI can poll.

## ADR-0004 — Provider abstraction with fallback chains (vendor-agnostic)
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01
**Context:** Mission requires independence from any single AI vendor and graceful degradation.
**Decision:** `packages/ai-providers` defines interfaces per capability (LLM, image, TTS, STT, music, video). Chains are configured via env (`CINEFORGE_LLM_CHAIN=zai,openai,anthropic,mock`). Registry walks the chain: tries providers in order, falls back on error/absence of key, and the terminal `mock` provider guarantees the pipeline always runs.
**Consequences:** Adding a vendor = one file + chain entry. Health/status exposed at `GET /health`.

## ADR-0005 — Offline-first "mock tier" is a first-class citizen
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01
**Context:** Agents/CI can't assume API keys or network. Mission forbids fake demos — so mocks must be honest and useful.
**Decision:** Mock providers produce **real artifacts** (Pillow-rendered frames, FFmpeg-rendered mp4 with real motion: ken-burns, typography) — clearly labeled `provider: mock` in metadata. This yields a genuinely runnable product with zero keys and stable tests.
**Consequences:** Quality upgrades are drop-in: add a key, chain picks it up. No code path pretends to be a real vendor.

## ADR-0006 — Code-driven video: Remotion templates + FFmpeg as the universal assembler
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01
**Context:** Mission prioritizes programming the video, not only calling video APIs.
**Decision:** Storyboards are JSON (schema in `docs/API_CONTRACTS.md`). Two render paths: (a) `video-engine` FFmpeg toolkit renders slideshows/motion natively in Python; (b) Remotion template `CinematicPromo` renders the same storyboard via React (worker runs `remotion render`; requires Node/Chromium in the render container). Motion Canvas template ships for explainer-style animations. GSAP/Three.js grow inside web/Remotion comps in M4.
**Consequences:** The director-agent writes/edits storyboard JSON or TypeScript comps; both paths output to the same asset store.

## ADR-0007 — Multi-agent coordination protocol
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01
**Context:** Five concurrent agents must not trample each other or the repo.
**Decision:** (1) Discovery via GitHub API search + this repo's docs. (2) Registration = per-agent JSON file (append-only, conflict-free). (3) Shared markdown files edited surgically with `pull --rebase` before push. (4) All substantive debate in Issues/Discussions/PROPOSALS. (5) Feature branches `feat/agent-0N-<slug>`; `main` stays runnable; no force-push. (6) Contract changes require updating `docs/API_CONTRACTS.md` in the same PR.
**Consequences:** Full auditability for the owner; low merge friction; agents can join at any time without a coordinator bottleneck.

## ADR-0008 — Jobs & queue: Celery/Redis optional, inline executor fallback
**Status:** Accepted · **Date:** 2026-11-01 · **Owner:** agent-01
**Context:** Renders are long-running; but requiring Redis on day one blocks local dev.
**Decision:** Job rows in DB are the single interface. If `REDIS_URL` is reachable → Celery workers; otherwise an in-process ThreadPoolExecutor executes the same task functions. UI polls `GET /api/jobs/{id}`.
**Consequences:** Same task code runs dev and prod; compose profile adds Redis.

## ADR-0009 — Sandbox policy for agent-generated code
**Status:** Accepted (principle) · **Date:** 2026-11-01 · **Owner:** agent-01 (hardening: agent-05, CF-061)
**Context:** The director-agent generates and executes code (Remotion comps, ffmpeg args, python snippets).
**Decision:** Execution happens only inside the render container/worker: filesystem limited to the project workspace, no network for ffmpeg/path (a), Remotion renders via pinned toolchain, timeouts on every job, and no secrets inside the sandbox env.
**Consequences:** CF-061 tracks enforcement details (seccomp, memory/CPU caps) before M5 exit.

## ADR-0010 — Backend consolidation after a live parallel-implementation race
**Status:** Accepted · **Date:** 2026-11-02 · **Owner:** agent-03 (FORGE) · **Review:** agent-05 (RELAY), agent-01 (ATLAS)
**Context:** During session 2, FORGE (agent-03) and RELAY (agent-05) independently implemented the M1 backend + video engine in parallel. RELAY's contract-complete service (PR #27) and VEGA's studio merged to `main` first while FORGE's verified branch (PR #28) was in flight. Two backends cannot both be canonical — contract divergence would break the studio↔API integration.
**Decision:** RELAY's backend + `packages/video-engine` are **canonical**. FORGE's parallel backend implementation is **withdrawn** (deleted on the branch before merge). FORGE's PR #28 became the additive layer on top of the canonical stack: `packages/ai-providers` (the documented swap point for `backend/app/providers`), Celery workers wired to the canonical executor with a single-flight `pending→running` CAS, docker images (which the compose stack referenced but lacked), `scripts/demo_e2e.py`, provider tests, and a `DATABASE_URL` guard in the canonical config. FORGE's verified-but-unported ideas are tracked for adoption: commit-before-submit for background jobs, short-session discipline around SQLite renders, richer per-capability chains (CF-021).
**Consequences:** One backend, zero contract divergence, full audit trail of the race in PR #28's description. When two agents drift toward the same files, the earlier-merged implementation wins by default and the other rebases into an additive/upgrade PR — do not re-litigate by force-pushing.
