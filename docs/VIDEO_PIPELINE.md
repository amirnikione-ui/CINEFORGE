# VIDEO PIPELINE — storyboard JSON → final cut

Canonical engine: `packages/video-engine` (RELAY offering, FORGE review) · Templates: FORGE interim → **agent-04 evolution**

Three code-driven paths from the SAME storyboard schema v1 (ADR-0006):

## Path A — FFmpeg engine (canonical, merged)

`director/tools.py` → `video_engine.timeline` (Timeline/Track/Clip IR → `compile_ffmpeg_plan`)
→ `video_engine.ffmpeg` (safe subprocess wrappers) → real MP4 → Asset(video).
Runs as a background Job: inline BackgroundTasks in the API process, or the Celery tier
(`workers/celery_app.py` — pending→running CAS single-flight) when Redis is up (ADR-0008).

## Path B — Remotion `CinematicPromo` template (`remotion-template/`, PR #37)

Editable template consuming storyboard v1 (`--props storyboard.example.json`):
`Root.tsx` → `CinematicPromo.tsx` with `components/WordReveal` (kinetic type),
`GradientBackdrop`, `VignetteOverlay`; typed by `src/schema.ts`. Evolving under agent-04:
template-pack v2 (lower-thirds, data-driven infographics, logo sting), ASS/RTL subtitles.

## Path C — Motion Canvas starter (`motion-canvas-template/`, PR #37)

`src/scenes/explainer.tsx` explainer starter; `npm run dev` opens the Motion Canvas editor.
M4: director-tool integration (`build_motion_canvas_scene`).

## Platform conform & presets

Resolutions/aspects derive from the storyboard (`aspect`, `fps`); platform caps live in
`docs/API_CONTRACTS.md` + `packages/timeline`. Conform = libx264 yuv420p +faststart (engine path).

## Verification

- `pytest backend/tests packages/video-engine/tests -q` (offline tier — zero keys)
- `npx tsc --noEmit` in `remotion-template` (CI job: `remotion-template-typecheck`)
- `python scripts/demo_e2e.py` (`--serve`/`--brief`/`--platform`/`--duration`) — brief → real MP4
