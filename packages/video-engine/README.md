# cineforge-video-engine

Real media processing for CINEFORGE (ADR-0006): FFmpeg as the universal assembler,
Remotion for code-driven video.

## `video_engine.ffmpeg_tools`

| Function | Purpose |
|---|---|
| `run_ffmpeg(args, timeout=600)` / `run_ffprobe(args)` | argv-list subprocess calls, `VideoEngineError` with stderr tail on failure |
| `probe(path)` / `summary(path)` | ffprobe JSON / `{duration_s, width, height, fps, has_audio, codec}` |
| `scene_detect(path, threshold=0.35)` | scene-cut detection -> `[{start, end, score}]` |
| `extract_frame(path, t, out_png)` | single-frame grab (posters, thumbnails) |
| `concat_clips(clips, out)` | concat demuxer (stream copy, re-encode fallback) |
| `mix_audio(narrations, music, total, out)` | narration concat + looped music bed at volume 0.22, amix, mono->stereo safe |
| `make_srt(scenes)` / `burn_subtitles(video, srt, out)` | subtitle generation + burn-in |
| `fonts()` | first existing bold/regular font paths (DejaVu/Liberation/Noto) |

Every invocation is an argv list (no shell), workspace-confined paths, per-call timeouts.

## `video_engine.slideshow.render_slideshow`

```python
render_slideshow(storyboard, frames, narration_paths, music_path, out_path, workdir) -> dict
```

Accepts storyboard JSON schema v1 verbatim (see `docs/API_CONTRACTS.md`).
Per scene: cover-scale -> motion (`ken-burns`/`zoom` via `zoompan`, `slide` via
time-based `crop`, `reveal` via colored fade) -> palette-aware `drawtext`
headline/body with alpha fade-in -> video fade in/out -> libx264 veryfast crf20
intermediate. Then concat -> narration/music mix (`mix.m4a`) -> mux with
`-shortest -movflags +faststart`. Returns
`{path, duration_s, width, height, fps, size_bytes}`.

Optional `progress_cb` keyword streams 0.0-1.0 progress for Job rows.

## `video_engine.remotion_runner`

- `scaffold_project(storyboard, out_dir)` — copies
  `packages/video-engine/remotion-template` (ignoring `node_modules`) into
  `out_dir` and writes `public/storyboard.json`. If the template directory is
  absent, a complete generated baseline project (React comp `CinematicPromo`
  reading the storyboard JSON) is written instead.
- `render(out_dir, out_mp4)` — `npx --yes remotion render CinematicPromo <out>`
  (cwd=out_dir, 30 min timeout). **Needs Node >= 18 + Chromium** — run inside the
  worker container (`workers/`), not in the API process.

## Requirements

- `ffmpeg` + `ffprobe` >= 5 on PATH (developed against 7.1)
- Optional: Node.js + Chromium for Remotion renders
