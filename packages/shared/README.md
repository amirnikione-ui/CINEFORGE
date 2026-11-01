# packages/shared — cross-runtime schemas (planned M4)

Single source of truth for shapes that cross runtime boundaries:
TS web app ↔ Python backend ↔ render templates.

## Current source of truth (M1–M3)

Until codegen lands, the contracts are maintained by hand and mirrored:

- **Human contract**: `docs/API_CONTRACTS.md` — REST endpoints, Storyboard JSON
  schema v1, tool interface.
- **TypeScript mirrors**: `apps/web/src/types/api.ts` (web) ·
  `packages/video-engine/remotion-template/src/types.ts` (renderer).
- **Python mirror**: `backend/app/schemas.py` (Pydantic v2).

Rule (ADR-0007 §6): any PR that changes a shape updates `docs/API_CONTRACTS.md`
**and all mirrors in the same PR**.

## Plan (M4)

- Generate from one machine-readable spec (OpenAPI for REST, JSON Schema for
  storyboards/assets/jobs):
  - `openapi-typescript` → `packages/shared/ts/`
  - `datamodel-code-generator` → `packages/shared/py/`
- CI drift check: regenerated output must be diff-clean against the committed
  sources; drift fails the build.
- Web app, render templates and backend import from here; the hand-written
  mirrors are retired.

## Status

**Planned (M4).** This package becomes the import target once codegen exists —
until then, use the pointers above and keep mirrors in sync manually.
