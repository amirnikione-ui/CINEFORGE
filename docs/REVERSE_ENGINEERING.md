# REVERSE ENGINEERING — reference-video analysis

Implemented: `packages/video-engine/cineforge_video/analysis.py` + `POST /api/media/analyze`
(asset_id) + `GET /api/analysis/{job_id}` (runs as a Job, ADR-0008).
Ethics: **style extraction only, never content copying** (ADR-0009, docs/SECURITY.md).

## Signals (v1 — honest signal processing, no fake AI)

| Signal | Method |
|---|---|
| Scene cuts | ffmpeg frame sampling (3 fps, ≤240 frames, 160px) → per-pair RMS diff (Pillow) → threshold peaks (0.14) |
| Pacing | cut-interval median + first-3s cut density («hook» heuristic) |
| Motion energy | mean diff per shot, normalized |
| Palette | Pillow adaptive quantize (k=5) per mid-shot frame → global top-8 hex |
| Loudness | per-second RMS via ffmpeg astats (`-inf` → −90 dB floor) |
| Duration/fps | ffprobe |

Report JSON: `{duration_s, fps_estimate, cuts[], scenes[{start,end,duration,motion,palette}],
pacing{median_cut_s, first3s_cuts, hook_density}, loudness[{t,rms}], palette[], notes[]}`.

## From analysis to new production (M3 roadmap — claim: open / agent-03+)

1. `report → style profile`: palette tokens → `storyboard.palette`; median cut → scene-duration
   targets; hook density → hook-scene treatment (more kinetic motion, faster first cut).
2. LLM mode: profile (numbers/tokens only) + user brief → original script/storyboard.
3. Offline mode: skeleton uses the deterministic planner with style constraints.
4. **Never**: re-export source media, reproduce protected text/visuals, or ship the reference
   as part of the deliverable. Reports keep `source_asset_id` for auditability.

## Upload path

`POST /api/projects/{pid}/upload` (multipart, kind=video) → Asset → `POST /api/media/analyze`
→ poll `GET /api/jobs/{id}` → `GET /api/analysis/{job_id}`. Size cap `CINEFORGE_MAX_PROJECT_MB`.
