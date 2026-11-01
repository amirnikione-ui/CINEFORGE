# REVERSE ENGINEERING — reference-video analysis

Engine: `packages/video-engine/video_engine/analysis.py` · API: `POST /api/media/analyze`
(asset_id) → Job → `GET /api/jobs/{id}` → report in `job.result` (M3 contracts).
Ethics: **style extraction only, never content copying** (ADR-0009, docs/SECURITY.md).

## Signals (v1 — honest signal processing)

| Signal | Method |
|---|---|
| Duration / fps / streams | ffprobe via `video_engine.ffmpeg.probe` |
| Scene cuts & pacing | sampled-frame diffs → threshold peaks → cut intervals + first-3s hook density |
| Palette | dominant colors per scene (Pillow quantize) |
| Motion energy | normalized frame-diff per shot |
| Loudness envelope | ffmpeg astats RMS series |

## From report to new production (M3 — open for claim)

1. Report → **style profile**: palette tokens → `storyboard.palette`; median cut → scene-duration
   targets; hook density → kinetic treatment of the hook scene.
2. Online mode: profile (numbers/tokens only) + user brief → original script/storyboard via the
   provider chain (`packages/ai-providers` — the documented swap point, ADR-0010).
3. Offline mode: deterministic planner with style constraints.
4. **Never** re-export source media or reproduce protected content; reports keep the source
   asset id for auditability.

## Upload path

`POST /api/projects/{pid}/upload` (multipart, kind=video) → Asset → `POST /api/media/analyze`
→ poll job → report. Size cap: `CINEFORGE_MAX_PROJECT_MB` / storage settings.
