# apps/desktop — Tauri shell (planned, M5)

Native desktop wrapper for the CINEFORGE studio (CF-063). Wraps the `apps/web`
build — no separate UI codebase.

## Plan

- **Shell**: Tauri 2 (Rust core + system webview) loading the Next.js build — no
  Electron/Chromium bundle; small binaries on macOS/Windows/Linux.
- **Native file dialogs**: project import/export (`.cineforge.json` bundles:
  storyboard + assets manifest + timeline), save-as for renders, drag-drop of
  media into the timeline.
- **Local ffmpeg sidecar**: bundled static `ffmpeg`/`ffprobe` binaries; the shell
  invokes the same `video-engine` code paths the worker uses (via a local Python
  sidecar running the backend, or a TS port — decided at spike time).
- **API in desktop mode**: the FastAPI backend runs as a child process on a
  localhost port; `NEXT_PUBLIC_API_URL` points at it. Same REST contract, no
  forked logic.
- **Security**: agent-generated code still executes only inside the render
  sandbox — ADR-0009 applies to desktop too. No shell-outs outside the sidecar.

## Status

**M5 — not started.** The spike will live in `apps/desktop/src-tauri/`; until
then this directory is documentation-only. Track progress under CF-063 in
`coordination/TASKS.md`.
