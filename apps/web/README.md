# apps/web — CINEFORGE Studio

The chat-first studio UI: brief a director agent, watch it plan/storyboard/generate/render, inspect the timeline, preview the cut, manage media and providers.

**Owner:** agent-02 (VEGA) · **Task:** CF-016 · **Contract:** `docs/API_CONTRACTS.md` v0.1

## Stack

Next.js 14 (App Router) · React 18 · TypeScript strict · Tailwind CSS 3 (dark cinematic palette per contract example) — hand-rolled components, no UI kit (ADR-0002).

## Run

```bash
npm install

# with the real backend (agent-03's FastAPI on :8000)
npm run dev

# UI-only development: labeled in-memory mock API on :8000 (frontend fixture, NOT the product backend)
npm run dev:mocked
```

Open http://localhost:3000. Point at a different API with `NEXT_PUBLIC_API_URL=http://host:port`.

## Pages

| Route | What |
|---|---|
| `/` | Productions dashboard: create (title/brief/style/platform/duration), filter by status, provider health pills |
| `/projects/[id]` | The studio: agent chat (plan steps, tool chips, provider chip, job progress) + tabs Preview / Timeline / Media / Providers |

## Structure

```
src/
  app/            # App Router pages + globals
  components/     # studio panels + hand-rolled primitives (ui.tsx)
  lib/            # typed API client, storyboard helpers, display utils
  types/api.ts    # contract mirror (docs/API_CONTRACTS.md) — keep in sync
mocks/            # DEV-ONLY labeled fixture API (never a product feature)
```

## Contract discipline

- All server communication goes through `src/lib/api.ts` (single fetch/error point).
- Types mirror the binding contract; changes to the contract ship in the same PR here, in `packages/timeline`, and in `docs/API_CONTRACTS.md` (ADR-0007).
- The mock API is honest by design (ADR-0005): in-memory, `provider:"mock"` everywhere, `X-Mock-Api` header, loud banner — it exists so the UI is buildable before the backend lands and is **not** a substitute for CF-010/011.

## Notes for the team

- Timeline v1 reads the **storyboard JSON** (from the storyboard asset — inline in `meta.storyboard` or via the asset file endpoint) and derives video/narration/captions lanes; scene colors map `kind` (hook/reveal/typography/outro).
- Polling: the studio page polls `GET /api/projects/{id}` every 3.5s only while jobs are pending/running or the project is `generating` (ADR-0008).
- ESLint config intentionally deferred to CI hardening (CF-060, agent-05); type safety is enforced by `tsc --noEmit` strict + `next build` type checking.
