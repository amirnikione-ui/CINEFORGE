# packages/motion-engine — motion helpers (M4+)

Shared motion-graphics toolkit for code-driven animation, complementing the
`video-engine` render templates (ADR-0006).

## Purpose

Reusable, palette-aware animation primitives so web previews and render comps
share one motion language — same easings, same typography scales, same transition
rhythm.

## Planned modules

| Module | Contents | Runs in |
|---|---|---|
| `TypographyKit` | kinetic-type presets (slam-in, tracking-in, typewriter) mirroring the Remotion Hook/Typography scenes | Remotion comps + web previews |
| `TransitionKit` | fade/slide/wipe/glitch wrappers with consistent 15-frame entrances | Remotion comps + web previews |
| `ThreeSceneBridge` | Three.js scene wrapper (camera drift, env lighting, product geometry) for `@remotion/three` | Remotion comps (M4) |

## Integration point

- **Remotion comps**: imported directly inside `CinematicPromo` scenes; the Three
  bridge via `@remotion/three` (same React tree, deterministic frame timing).
- **Web previews**: the GSAP/CSS/Canvas implementations run directly in the
  `apps/web` preview pane — identical parameterization, browser-native playback.

## Status

**M4 — planned.** No code yet by design: the timeline model (CF-050) and the
Remotion/Motion Canvas templates land first, then this package extracts the
shared parts from them. See `coordination/TASKS.md`.
