# CINEFORGE Remotion template — `CinematicPromo`

Storyboard-driven cinematic promo composition (ADR-0006, render path b). It
consumes the CINEFORGE **Storyboard JSON schema v1** (`docs/API_CONTRACTS.md`)
verbatim and derives canvas size, fps, scene timing and palette from it — nothing
is hardcoded.

## Scenes

| kind | component | motion |
|---|---|---|
| `hook` | `HookScene` | headline words slam in word-by-word (spring, staggered), screen shake on impact, accent gradient sweep |
| `reveal` | `RevealScene` | product card spring-in with primary glow border, rotating conic sheen, gentle float |
| `typography` | `TypographyScene` | up to 3 keyword lines slide in alternating directions with tracking-in letter spacing |
| `feature` | `FeatureScene` | feature pills (from `body`, `|` separated) pop in staggered and bob — renderer extension of the contract's kind list |
| `outro` | `OutroScene` | headline scales down to a centered lockup, CTA types on (typewriter), fade to bg |

Shared layers: `KenBurns` drift (per `motion.style`/`intensity`), `SceneTransition`
(fade | slide | cut, first 15 frames), `AnimatedSubtitles` (word-by-word narration
reveal), `GrainOverlay` (feTurbulence film grain), and 2.39:1-style letterbox bars
on 16:9 canvases.

## Run the studio

```bash
npm install
npm run dev          # Remotion Studio (default port 3000 — pass --port if the web app owns it)
```

## Render

```bash
npm run render                                      # silent promo (no narration audio)
npm run render -- --props='{"includeAudio":true}'   # play public/audio/<scene-id>.mp3 when present
```

Output lands in `out/video.mp4` (dimensions/fps/duration come from the storyboard).

**Requirements:** Node ≥ 18 (20 recommended). On first render Remotion downloads a
headless Chrome; for air-gapped machines run `npx remotion browser ensure` once on
a connected machine, or point the `BROWSER` env var at a local Chrome binary.

## Scaffold contract — how CINEFORGE uses this template

1. The `build_remotion_project` tool (video-engine) copies this folder into the
   project workspace.
2. The backend **overwrites `public/storyboard.json`** with the generated
   storyboard (schema v1). `src/Root.tsx` imports that file statically, so it must
   exist. `public/storyboard.example.json` is the committed reference copy —
   restore from it if `storyboard.json` is ever deleted.
3. Narration (optional): the backend writes `public/audio/<scene-id>.mp3`. Audio
   plays only when `includeAudio` is true **and** the file exists — availability is
   HEAD-checked at render start (missing files degrade to subtitles-only).
4. The worker runs `npx remotion render CinematicPromo out/video.mp4` in the
   workspace (CF-034 automates this inside the render container, ADR-0009).

## Editing notes

- **Colors** flow from `storyboard.palette` through `src/theme.ts` helpers
  (`resolvePalette`, `rgba`) — no hardcoded hex in scenes; partial palettes fall
  back per-channel.
- **Durations** derive from `scenes[].duration_s * fps` in `src/CinematicPromo.tsx`
  (`segmentStoryboard` + `calculateMetadata`). Never hardcode scene lengths.
- **Types** in `src/types.ts` mirror schema v1 exactly; `src/parse.ts` normalizes
  raw JSON at the boundary (coerce/clamp/default) so imperfect payloads still render.
- Keyword lists for `typography`/`feature` come from `scene.body` split on `|`
  (or `,`), falling back to headline words — see `src/content.ts`.
