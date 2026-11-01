# VIDEO PIPELINE — storyboard JSON → final cut (implemented)

Owner: agent-04 (evolution) · Implemented by agent-02 (interim) · `packages/video-engine`

Two render paths from the SAME storyboard schema v1 (ADR-0006):

## Path A — FFmpeg slideshow renderer (`cineforge_video.slideshow`) — default in M1

```
storyboard.json + frames/*.png + audio/narration-*.wav + audio/music.wav
 1. per-scene clip   : PNG → pre-scale 4× → zoompan (ken-burns|zoom|reveal|slide by
                       motion.intensity) → drawtext headline/body (palette colors,
                       fade-in alpha, DejaVu bold) → scale/pad 1080×1920|1920×1080
 2. joins            : xfade chain — fade 0.5 s | slide 0.5 s | cut = 1-frame fade;
                       offsets = L_prev − f (concat_xfade_plan)
 3. audio            : narration clips adelay'ed to scene starts → amix →
                       music (vol 0.9) side-chain-ducked (threshold 0.03, ratio 6) →
                       atrim to final duration → afade-out 1 s → aac 192 k
 4. subtitles        : narration → SRT (42-char chunks, word-timed) → burn-in
 5. conform          : libx264 crf20 yuv420p +faststart, -t exact plan duration
```

Honest fallbacks: missing frame → palette color source (never a crash); missing font →
skip typography (frames still render); missing narration → silence-safe mix.

## Path B — Remotion `CinematicPromo` (`remotion-template/`) — code-driven motion

Storyboard consumed **verbatim** (`--props storyboard.json`): TransitionSeries with
`fade()`/`slide()` presentations, per-letter staggered kinetic typography (spring),
glow-orb visual anchors, vignette + letterbox + seeded film-grain overlays, palette-
driven — zero hardcoded style, zero external assets. Runner: `cineforge_video.remotion.
render_remotion` (lazy `npm install`, timeout-guarded, needs Node in the worker image —
included in `docker/backend.Dockerfile`).

`build_remotion_project` tool copies the template into `storage/<pid>/projects/` with the
storyboard injected → Asset(kind=project) — the user's editable artifact.

## Reference-video analysis (`cineforge_video.analysis`) — M3 entrypoint

Frame sampling (ffmpeg fps=3, 160px, ≤240 frames) → Pillow RMS-diff scene cuts →
per-scene duration/motion/palette (adaptive quantize) → pacing stats + first-3s hook
density → loudness envelope (ffmpeg astats). Style only — source never re-exported
(`docs/SECURITY.md`, ADR-0009 ethics).

## Verification hooks

- Unit: `backend/tests/test_ffmpeg_plan.py` (xfade math, SRT, drawtext escaping)
- E2E: `backend/tests/test_e2e_offline.py` renders a real MP4 and probes it (codec/dims/duration)
- Demo: `make e2e`
