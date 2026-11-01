# CINEFORGE Motion Canvas template

Explainer / motion-graphics sequences (ADR-0006): title cards, animated charts,
diagram walkthroughs — the complement to the cinematic `CinematicPromo` Remotion
comp. Ships one example scene: a typography bar-chart explainer (tweened title,
4 bars growing with counting value labels, caption beat).

## Run

```bash
npm install
npm run dev      # Motion Canvas editor (Vite) — animate and preview in the browser
npm run build    # tsc type-check + vite production build
```

Render to video from the Studio's render panel (ffmpeg must be on `PATH`), or wire
the `@motion-canvas/core` render CLI into the worker later.

## What it's for

- Explainer segments: charts, process diagrams, feature walkthroughs.
- Title/interstitial cards that need precise, layout-driven motion.
- Anything where a generator function (`yield*` tweens) beats hand-timed CSS.

## Integration plan

The worker (CF-034+) renders chosen scenes to `.mp4`; the output is then ingested
as a normal CINEFORGE asset (`kind: video`) and trimmed/concatenated by the
`video-engine` FFmpeg toolkit — the same asset store Remotion renders land in.

## Status / caveats

- Written against `@motion-canvas/core` **3.x** APIs (`makeScene2D`, `createRef`,
  `createRefArray`, `tween`, `all`, `waitFor`, `Rect`/`Txt`/`Layout`) — matching
  the upstream starter conventions. Not yet exercised in CI; pin exact minor
  versions on first `npm install` if the 3.x line drifts.
- `tsconfig.json` follows upstream template conventions (`jsx: preserve`,
  `jsxImportSource: @motion-canvas/2d`). The `?scene` import suffix in
  `src/project.ts` is resolved by `@motion-canvas/vite-plugin`; if your editor
  flags it before `npm install`, that's expected.
