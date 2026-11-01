# CINEFORGE — API Contracts v0.1

> **Binding** for M1. Changes require a PR that updates this file. All endpoints JSON unless noted. Base URL `http://localhost:8000`.
> TypeScript mirror: `apps/web/src/types/api.ts` · Python schemas: `backend/app/schemas.py`.

## REST Endpoints

### Health
```
GET /health → 200
{
  "status": "ok",
  "version": "0.1.0",
  "providers": {
    "llm":    ["zai", "openai", "anthropic", "mock"],   // ordered by availability in current env
    "image":  ["mock"],
    "tts":    ["mock"],
    "stt":    ["mock"],
    "music":  ["mock"],
    "video":  ["mock"]
  },
  "storage_root": "/data/storage"
}
```

### Projects
```
POST /api/projects
{ "title": "Nova Runners promo", "brief": "30s cinematic promo, dark mood, English narration…",
  "style": "cinematic-dark",       // optional
  "platform": "instagram",         // optional: instagram|youtube|tiktok|web
  "duration_hint_s": 30 }          // optional
→ 201 { "id": "uuid", "title": "…", "brief": "…", "style": "…", "platform": "…",
        "status": "draft|generating|ready|failed", "created_at": "ISO" }

GET /api/projects → 200 [Project]           // newest first
GET /api/projects/{pid} → 200 ProjectDetail
{ "project": {...}, "messages": [Message], "assets": [Asset], "jobs": [Job] }
DELETE /api/projects/{pid} → 204            // deletes DB rows; files best-effort purge
```

### Chat (director agent)
```
POST /api/projects/{pid}/chat
{ "message": "make it punchier, shorter hook" }
→ 200 ChatResponse
{
  "user_message":      { "id": "…", "role": "user", "content": "…", "created_at": "…" },
  "assistant_message": { "id": "…", "role": "assistant", "content": "…",
                         "meta": { "plan": [...], "tools_used": [...], "llm_provider": "mock" } },
  "assets": [ Asset ],    // newly created artifacts (storyboard, frames, audio, video, project)
  "jobs":   [ Job ]
}
// Long operations surface as Job rows; the chat response returns after the synchronous
// plan+core tools complete. Clients poll GET /api/jobs/{id} for background progress.
```

### Assets & Jobs
```
GET  /api/jobs/{id} → 200 Job
{ "id": "…", "project_id": "…", "kind": "render|generate|analyze",
  "status": "pending|running|done|failed", "progress": 0.0–1.0,
  "result": {...}, "error": "…|null" }

GET  /api/assets/{id}/file → 200 binary (Content-Type per kind; video/mp4, image/png, audio/wav, application/json)
POST /api/media/analyze        // M3 reverse-engineering entrypoint
{ "asset_id": "uuid" }         // or { "url": "https://…" } in M3
→ 200 AnalysisReport (schema below, M3)
```

### Object shapes
```
Asset { "id": "…", "project_id": "…",
        "kind": "storyboard|frame|audio|video|analysis|project",
        "filename": "final_v1.mp4", "path": "/data/storage/<pid>/video/final_v1.mp4",
        "meta": { "provider": "mock|openai|…", "duration_s": 30.0,
                  "width": 1080, "height": 1920, "fps": 30, "prompt": "…" },
        "created_at": "ISO" }

Message { "id": "…", "project_id": "…", "role": "user|assistant|system",
          "content": "…", "meta": {...}, "created_at": "ISO" }
```

## Storyboard JSON (schema_version 1) — the director's central artifact

```json
{
  "schema_version": 1,
  "title": "Nova Runners — Cinematic Promo",
  "platform": "instagram",
  "aspect": "9:16",
  "fps": 30,
  "duration_target_s": 30,
  "palette": { "bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff" },
  "music_mood": "dark-cinematic",
  "scenes": [
    {
      "id": "scene-01",
      "kind": "hook|reveal|typography|outro",
      "duration_s": 4.0,
      "headline": "RUN BEYOND LIMITS",
      "body": "Optional supporting line",
      "narration": "In a city that never slows down…",
      "visual_prompt": "dark cityscape, neon reflections, cinematic haze",
      "motion": { "style": "ken-burns|slide|zoom|reveal", "intensity": 0.6 },
      "transition_in": "fade|cut|slide"
    }
  ]
}
```

Rules: `sum(scenes[].duration_s)` ≈ `duration_target_s` (±10%). Renderer implementations (FFmpeg toolkit, Remotion template) MUST accept this schema verbatim.

## Tool interface (director ↔ tools, internal but stable)

Registered tools (name → signature summary):

| Tool | Input | Output |
|---|---|---|
| `write_storyboard` | brief, style, platform, duration_hint | Asset(storyboard) |
| `generate_concept_frames` | storyboard | [Asset(frame)] |
| `generate_narration` | storyboard | [Asset(audio)] |
| `generate_music` | mood, duration_s | Asset(audio) |
| `render_slideshow` | storyboard, frames, audio | Asset(video, mp4) |
| `build_remotion_project` | storyboard | Asset(project, editable TS comp) |
| `probe_media` | path | {duration_s, width, height, fps, streams} |
| `analyze_video` | path (M3) | AnalysisReport |

Tool results always include `meta.provider`. Errors raise `ToolError` → orchestrator logs to message meta and either retries with next provider or reports the failure honestly in the assistant message.

## Conventions

- IDs: UUID4 strings. Timestamps: ISO-8601 UTC.
- Errors: `{"detail": "human readable"}` with proper HTTP codes (400 validation, 404 missing, 409 conflict, 500 internal).
- No auth in v0.1 (local studio). Auth lands with multi-user (tracked post-M2).
