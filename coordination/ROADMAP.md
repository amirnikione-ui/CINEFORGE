# CINEFORGE — Roadmap

> Milestones are outcome-based; agents self-assign tasks from `TASKS.md`. Dates are session-relative, not calendar promises.

## M0 — Bootstrap ✅ (session 1)
Shared repo + governance + contracts + skeleton. **Exit criteria:** repo public with coordination/, docs, and a runnable skeleton pushed to `main`. *Status: DONE.*

## M1 — Core Pipeline: "chat brief → rendered video" (sessions 1–3)
A user types a brief in the chat studio; the director-agent plans, produces storyboard, frames, narration (mock tier), renders an mp4 via FFmpeg (ken-burns + typography + audio mix), registers assets/jobs, and the web studio shows chat + preview + timeline v1 + media library.
**Exit criteria:** `docker compose up` works; `scripts/demo_e2e.py` renders an mp4 with zero API keys; pytest suite green; UI studio functional against API.

## M2 — Real provider bring-up (sessions 3–5)
Plug real LLM (Z.ai GLM/OpenAI/Anthropic), image, TTS, music providers into the existing chains; provider health dashboard in UI; Remotion render runner in worker; auto-subtitles from TTS timings.
**Exit criteria:** same brief produces a noticeably higher-quality video with keys configured; fallback proven by chaos test (disable a provider mid-run).

## M3 — Video reverse-engineering (sessions 5–7)
Upload reference video → scene/cut detection, pacing, palette & style extraction, audio profile, narrative/hook pattern inference → a **generation recipe** (style transfer for new content; no copyrighted-content reproduction).
**Exit criteria:** analysis report asset generated per upload; recipe feeds the director's storyboard.

## M4 — Pro editing & motion engine (sessions 7–10)
Timeline data model v2 (tracks/clips/transitions/keyframes) shared by UI and renderer; interactive multi-track editor; targeted regeneration ("fix scene 3 only"); GSAP/Three.js/SVG helpers in `packages/motion-engine` wired into Remotion comps.
**Exit criteria:** user can edit a clip's timing/text in the timeline and re-render only the delta.

## M5 — Hardening & desktop (sessions 10+)
CI on every PR; sandbox hardening (CF-061); S3 adapter; packaging; Tauri desktop shell spike; docs/site polish.
**Exit criteria:** green CI, security checklist signed off by the QA/DevOps role, installable artifacts.

---

### Product principles (binding for all milestones)
1. The user describes outcomes, never toolchains.
2. The agent always delivers: final file **and** editable project.
3. Every generated artifact is inspectable, regenerable, and traceable to a plan step.
4. Code-driven video is the soul of the product; APIs are accelerators, not the foundation.
5. Nothing fake: mocks are labeled, demos are real pipelines.
