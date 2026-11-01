# CinematicPromo — CINEFORGE Remotion template (ADR-0006, path b)

Storyboard-driven, **fully code-driven** cinematic composition. Consumes storyboard
schema v1 (see repo `docs/API_CONTRACTS.md`) **verbatim** — the CINEFORGE director
agent writes `storyboard.json`, this template renders it.

## Edit & preview

```bash
npm install
npx remotion studio      # storyboard.json is hot-reloaded
```

## Render

```bash
npx remotion render src/index.ts CinematicPromo out/promo.mp4 --props storyboard.json
```

## Structure

- `src/scenes.tsx` — scene renderer (`hook | reveal | typography | outro`) × motion
  styles (`ken-burns | slide | zoom | reveal`), per-letter staggered typography,
  glow-orb visual anchors, vignette + letterbox + seeded film grain overlays.
- Palette, aspect, fps, durations all come from the storyboard — zero hardcoded style.
- The FFmpeg path (`cineforge_video.slideshow`) renders generated concept frames;
  this template is 100% procedural so it runs with zero assets. Combine both for
  maximum production value (roadmap: mixed-sequence rendering, M4).

Ownership: template co-built by agent-02/agent-03; evolution belongs to **agent-04**
(`packages/video-engine` scope in `coordination/AGENTS.md`).
