# @cineforge/timeline

Shared **Storyboard/Timeline data model** for CINEFORGE — the contract between the studio UI, the director agent, and the render engines.

## What's inside

- `src/index.ts` — TypeScript types + helpers:
  - `Storyboard`, `Scene`, `SceneMotion`, `Palette` (mirror of `docs/API_CONTRACTS.md` v0.1, `schema_version: 1`)
  - `storyboardDuration`, `storyboardDurationOk` (contract rule: scenes sum ≈ target ±10%)
  - `storyboardLanes` — derives the UI's `video / narration / captions` lane layout with start offsets
  - `aspectDimensions`, `platformAspect` — platform → aspect → pixel size
- `schema/storyboard.schema.json` — normative JSON Schema (draft 2020-12) for tooling/validation.

## Consumers

| Consumer | Usage |
|---|---|
| `apps/web` (agent-02) | timeline v1 visualization, scene inspector, preview sizing (`apps/web/src/types/api.ts` re-mirrors these types for the app bundle — keep in sync) |
| `packages/video-engine` (agent-03/04) | FFmpeg toolkit MUST accept this shape verbatim (contract rule) |
| Remotion template `CinematicPromo` | storyboard-driven React composition |
| director orchestrator | `write_storyboard` tool output |

## Rules

- This schema is **binding** (M1): changes require a PR updating `docs/API_CONTRACTS.md` in the same PR and an ADR if architectural.
- Validation in JS/TS (quick): check `schema_version === 1`, required keys, and `storyboardDurationOk`. Full validation: run the JSON Schema with any draft-2020-12 validator (e.g. Ajv) in the backend or tests.

```ts
import type { Storyboard } from '@cineforge/timeline';
// or (until workspaces are wired): import type { Storyboard } from '../../packages/timeline/src';
```
