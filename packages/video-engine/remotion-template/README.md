# @cineforge/remotion-template-cinematic-promo

Storyboard-driven Remotion v4 template for CINEFORGE. It renders the
director agent's **Storyboard JSON (schema_version 1)** as a cinematic
typography promo (see `docs/API_CONTRACTS.md` for the binding contract).

The storyboard is consumed **verbatim**: no field is renamed, dropped or
re-typed. The Zod schema in `src/schema.ts` mirrors the contract exactly
(same enums, same optional fields) and is attached to the composition, so
invalid storyboards fail loudly in the studio and in renders instead of
rendering garbage.

This template and the Python FFmpeg engine (`packages/video-engine`, task
CF-013) consume the **same** storyboard schema. Any storyboard that renders
through the FFmpeg pipeline renders here too, and vice versa.

## Composition parameters

| Property           | Value                                                            |
| ------------------ | ---------------------------------------------------------------- |
| id                 | `CinematicPromo`                                                 |
| size               | from the storyboard `aspect` field (default `9:16` → 1080×1920)  |
| fps                | `storyboard.fps`                                                 |
| durationInFrames   | `Math.round(sum(scenes[].duration_s) * storyboard.fps)`          |
| props              | a full Storyboard JSON document (schema-validated)               |

`calculateMetadata` derives fps, duration and dimensions from the actual
props, so rendering any storyboard via `--props` produces the right length
and aspect - not the defaults baked into `src/Root.tsx`.

## Scene kinds implemented

- `hook` — huge bold headline, per-word `<WordReveal>` spring stagger, body
  line fades up after the headline.
- `reveal` — headline slides in from the left with an overshoot spring,
  accent underline bar grows (`scaleX`), body fades up.
- `typography` — words pop in one-by-one on a beat grid
  (`framesPerWord = sceneFrames / wordCount`) with a slight deterministic
  rotation (seeded via Remotion's `random()`, never `Math.random`).
- `outro` — centered stack: wordmark (`storyboard.title` uppercase),
  headline, thin accent rule, fade-through-black over the last 12 frames.

Per-scene behavior:

- `motion.style`: `ken-burns` (scale 1.0 → 1.0 + 0.12·intensity + slight
  translate), `zoom` (scale in then out, sin pulse), `slide` (horizontal
  drift) applied to the scene backdrop layer and the text container;
  `reveal` drives a clip-path inset wipe on the text block.
- `transition_in`: `fade` (0 → 1 over the first 10 frames), `slide`
  (translateX 8% → 0, spring over the first 12 frames), `cut` (nothing).
- Headlines render in `palette.text` with the **last word** wrapped in
  `palette.accent`; body lines use `palette.text` at 70% opacity.

Rendering is fully deterministic: no `Math.random`, no `Date.now`. Fonts are
system stacks only, so renders work in offline/air-gapped environments.

## Commands

```bash
npm install

# Interactive preview (Remotion Studio) with the example storyboard
npm run preview

# Render the example storyboard to out/cinematic-promo.mp4
npm run render

# Render a single still cover frame
npm run still
```

## Rendering an arbitrary storyboard

Props are passed with `--props=<file>`, which Remotion serves as the
composition input (`getInputProps()`):

```bash
npx remotion render src/index.ts CinematicPromo out/video.mp4 --props=/path/to/storyboard.json
npx remotion still src/index.ts CinematicPromo out/cover.png --props=/path/to/storyboard.json
```

The props document must be a complete Storyboard JSON (schema_version 1) -
exactly the artifact the director agent's `write_storyboard` tool produces.

## Worker integration (CF-034)

The CINEFORGE render worker will invoke this template headlessly:

```
npx remotion render <entry-or-bundled-project> CinematicPromo <output.mp4> --props=<generated-storyboard.json>
```

No interactive steps are required: the entry point is `src/index.ts`, the
composition id is fixed (`CinematicPromo`), and the storyboard drives
duration, fps and aspect through `calculateMetadata`.

## File map

- `src/schema.ts` — Zod mirror of the storyboard contract + inferred types.
- `src/utils.ts` — frame math (`sceneFrames`, `totalFrames`, `sceneLayouts`),
  motion/clip-path helpers, aspect→dimensions map, color helper.
- `src/index.ts` — `registerRoot` entry point.
- `src/Root.tsx` — composition registration + inline default storyboard
  (typed duplicate of `storyboard.example.json`).
- `src/CinematicPromo.tsx` — the composition: scene sequencing, per-kind
  scene renderers, motion, transitions.
- `src/components/` — `WordReveal`, `GradientBackdrop`, `VignetteOverlay`.
- `storyboard.example.json` — real example storyboard (3 scenes, 11.5 s).
- `remotion.config.ts` — CLI defaults (jpeg frames, overwrite output).
