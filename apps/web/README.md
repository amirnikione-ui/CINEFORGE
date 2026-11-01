# 🎬 CINEFORGE — Web Studio (`apps/web`)

The studio UI for CINEFORGE, an AI-native video production studio: chat with the director-agent,
watch it plan, generate and render your video, inspect the storyboard pre-vis and timeline, and
grab every artifact (frames, audio, mp4, editable Remotion project).

Stack: **Next.js 14 (App Router) · TypeScript (strict) · Tailwind CSS 3** — no other runtime deps.
All backend access goes through a thin typed fetch client (`src/lib/api.ts`) implementing
[`docs/API_CONTRACTS.md`](../../docs/API_CONTRACTS.md) v0.1.

## Run it

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
```

The UI expects the FastAPI backend on port 8000 — from the repo root:

```bash
make api           # uvicorn app.main:app --reload --port 8000
```

Without the backend the app stays honest: the dashboard shows an amber **API OFFLINE** chip and the
studio shows a banner — `Cannot reach API at http://localhost:8000 — start the backend (make api)`.

### Environment

| Variable | Default | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL. Inlined at **build time** — restart `npm run dev` after changing it. |

## Scripts

| Script | What it does |
|---|---|
| `npm run dev` | Next dev server on :3000 |
| `npm run build` | Production build (type-checked, strict TS) |
| `npm start` | Serve the production build |

## Features

**Dashboard (`/`)**
- Provider capability chips from `GET /health` (green dot per capability → preferred provider; amber
  `API OFFLINE` chip when unreachable).
- Create a project from a title + brief — inline hero card **and** a modal dialog ("✦ Create with
  Director"), then straight into the studio.
- Project grid with status pills (draft / generating / ready / failed), platform, brief excerpt,
  created date and live asset counts.
- 5s polling while the tab is visible; skeleton shimmer only while loading; honest empty/error
  states with retry.

**Studio (`/studio/[projectId]`)**
- Three-pane layout: chat (380px, left) · preview + timeline (center) · media (300px, right,
  collapsible below `xl`); chat becomes a drawer below `lg`.
- **Chat**: optimistic send, "Director is working…" animated state, collapsible director plan with
  checkmarks, tool chips, `provider:` tag, honest red inline error if a message fails to deliver
  (draft is restored).
- **Preview**: latest rendered `.mp4` in an HTML5 player (with poster frame + duration/WxH/provider
  meta) or the storyboard pre-vis — scene cards with palette swatches.
- **Timeline v1**: VIDEO scene blocks (palette-derived gradients), AUDIO narration blocks, MUSIC
  full-width bed, OVERLAY transition diamonds, 5s ruler, 12/24/48 px/s zoom, static playhead at
  t=0 (scrubbing lands in M4 — stated in the UI).
- **Media panel**: job progress bars (accent gradient, % + error text) and assets grouped by kind
  with provider/duration/dimension chips and direct file links; `project` kind is labeled
  "editable Remotion project (on server)".
- Adaptive polling: 2.5s while jobs are pending/running or the project is generating, 8s when idle;
  paused while the tab is hidden. 404 → "Project not found" with a way back.

## Structure

```
src/
├── app/
│   ├── layout.tsx                     # dark shell, metadata
│   ├── globals.css                    # theme tokens, scrollbars, film grain, animations
│   ├── page.tsx                       # dashboard
│   └── studio/[projectId]/page.tsx    # server shell → StudioClient
├── components/
│   ├── StudioClient.tsx               # studio layout, useProjectDetail polling, chat wiring
│   ├── ChatPanel.tsx                  # director chat + composer
│   ├── PreviewPane.tsx                # video player / storyboard pre-vis
│   ├── Timeline.tsx                   # timeline v1
│   ├── AssetsPanel.tsx                # jobs + media library
│   ├── NewProjectDialog.tsx           # inline card + modal
│   ├── ProviderChips.tsx              # /health → capability chips
│   └── TopBar.tsx                     # shared header (+ StatusPill)
├── lib/api.ts                         # typed fetch client, ApiError, apiDown(), formatters
└── types/api.ts                       # mirror of docs/API_CONTRACTS.md v0.1
```

## Design language

Professional film studio, dark: background `#07070c`, panels `#0d0d16` / `#12121e`, 1px `#1e1e30`
borders, rounded-xl, violet→cyan accent (`#7c5cff` → `#00e5ff`) used sparingly (active states,
playhead, primary buttons), mono type for IDs/timings, CSS-only film grain on the header, thin
custom scrollbars, micro-interactions via Tailwind transitions.

## Honest-state policy

No fake data, ever. When the API is down you get offline chips/banners; when a storyboard or
timeline can't load you get the exact fetch error plus a retry button; when there is nothing to
show you get an explicit empty state.
