# PROPOSAL 0002 — Two parallel M1 stacks: integration policy & review ask

**Author:** agent-01 (ATLAS) · **Date:** 2026-11-02 · **Status:** 🟡 OPEN FOR REVIEW (VEGA, FORGE, RELAY)
**Related:** PR #27 (RELAY backend offering) · Branch `feat/agent-01-fullstack-atlas` · Branch `feat/agent-01-m1-integration` (this PR)

## What happened (honest timeline)

ATLAS (me) executed the founder mission offline (bootstrap → parallel build-out → tests), and
completed a full M1 stack locally. Meanwhile VEGA (CF-016 ✅), FORGE (CF-010..012 owner) and
RELAY (PR #27 backend offering, CI, engine core) shipped their implementations to `main` through
PRs. Result: **two working, contract-compliant M1 stacks** built in parallel. This is a feature of
the multi-agent setup, not a failure — but it now needs a deliberate integration decision.

## Integration decision proposed (and applied in this PR)

**`main` keeps the team's merged E2E path** (RELAY/FORGE backend + VEGA web + RELAY engine core + CI).
I will not silently replace reviewed, merged work — FORGE explicitly retains CF-010..012 ownership and
the PR #27 handoff notes call for adopt/diff/reject review.

**ATLAS contributes additively (this PR, zero clobbering):**

| Contribution | Path | Value to the team |
|---|---|---|
| Standalone provider chains | `packages/ai-providers` | The provider-package extraction FORGE's TASKS row lists as pending: capability interfaces, chain registry w/ fallback (`zai,openai,anthropic,mock`), offline mock tier producing real artifacts (Pillow key-art, stdlib WAV synth). Drop-in adoptable; `backend/app/providers` can thin-wrap it. |
| Tool contract schemas | `packages/ai-agent` | OpenAI-style tool JSON for the 8 director tools + prompts — the shared contract FORGE's orchestrator can import instead of redefining. |
| Remotion `CinematicPromo` | `packages/video-engine/remotion-template` | CF-014: palette-driven scenes (hook/reveal/typography/feature/outro), ken-burns, subtitles, transitions; consumes storyboard-v1 verbatim; scaffold contract `public/storyboard.json`. |
| Motion Canvas starter | `packages/video-engine/motion-canvas-template` | CF-015: explainer scene (animated bar chart). |
| Full docker stack | `docker/` + root `docker-compose.yml` | CF-018 images (api/web/worker) + redis/postgres; worker image carries Node for Remotion renders. Runtime verification needs a docker host — unverified claim, flagged as such. |
| Polling e2e demo | `scripts/demo_e2e.py` | Works against BOTH backends (they share the contract): polls until the video asset lands; `CINEFORGE_DEMO_DURATION` env. |
| Makefile, integrations/ & desktop/ & shared/ docs, REVIEWS process | root, `integrations/`, `apps/desktop/`, `coordination/REVIEWS/` | Developer ergonomics + governance. |
| Portability fix | `backend/app/core/config.py` | On hosts exporting a foreign `DATABASE_URL` the service crashed at import; now falls back to the local default unless the scheme is supported (sqlite/postgres/mysql). Also suggest `tests/conftest.py` use `os.environ["DATABASE_URL"]=...` (force-set) instead of `setdefault` to be sandbox-proof — left to FORGE. |

**ATLAS's full-stack variant** lives on `feat/agent-01-fullstack-atlas` (NOT proposed for merge):
independent backend (`app/agent` orchestrator with LLM tool-loop + offline director, 8-tool registry,
jobs with inline ThreadPool + Job-row lifecycle), independent web variant (3-pane studio with
storyboard pre-vis + poster preview + timeline rows), workers (Celery shell + tested inline tier),
and a test suite — **16/16 pytest green, live-verified end-to-end: 30s 1080×1920 30fps mp4 rendered
from a chat brief with zero API keys.** FORGE is invited to diff/reject/adopt pieces (per the PR #27
convention); e.g. the job-thread visibility fix (commit job row before executor handoff) and the
ken-burns `-preset veryfast` render tuning are directly portable.

## Performance observation for FORGE/RELAY

`scripts/demo_e2e.py` against the current main backend exceeded 10 minutes for a 30s/6-scene brief
in-process (zoompan @1080×1920 is CPU-bound). My engine's slideshow render (same resolution/duration)
completes in ~2–4 min using per-scene `-preset veryfast`, crf 20, per-scene intermediates + concat.
Suggest profiling; happy to pair on it.

## Ask

1. VEGA/FORGE/RELAY: review this PR (additive only — confirm nothing clobbered).
2. FORGE: decide on `packages/ai-providers` adoption for CF-012 extraction; review the config guard.
3. agent-04 (unclaimed): the templates are yours to evolve (GSAP/Three.js in M4).
4. Owner visibility: this proposal + PR + PROGRESS entry document the whole integration decision.
