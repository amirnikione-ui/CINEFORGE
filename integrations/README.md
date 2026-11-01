# CINEFORGE — external integrations

All external AI services are reached through the **provider chains** in
`packages/ai-providers` (ADR-0004): capability interface → ordered chain from
`CINEFORGE_*_CHAIN` → terminal `mock` provider guarantees the pipeline runs with
zero keys (ADR-0005). This directory hosts the heavier adapters that don't fit the
provider interface (3D engines, vector motion, stock-media libraries).

| Integration | Purpose | Package home | Status |
|---|---|---|---|
| Z.ai GLM | LLM planning / director agent | `packages/ai-providers` (llm) | planned · M2+ |
| OpenAI | concept frames (images), TTS, STT, LLM | `packages/ai-providers` (image/tts/stt/llm) | planned · M2+ |
| Anthropic | LLM fallback | `packages/ai-providers` (llm) | planned · M2+ |
| ElevenLabs | high-quality narration TTS | `packages/ai-providers` (tts) | planned · M2+ |
| Whisper (local / OpenAI) | STT → auto-subtitles from narration | `packages/ai-providers` (stt) | planned · M2+ |
| Runway / Luma / Pika | generative video clips per scene | `packages/ai-providers` (video) | planned · M2+ |
| MusicGen / Suno / CC0 libraries | music beds per `music_mood` | `packages/ai-providers` (music) + `integrations/` | planned · M2+ |
| Stock media (Pexels / Pixabay / kenney.nl — CC0) | b-roll, SFX, footage | `integrations/stock` | planned · M3+ |
| Blender (`bpy`) | 3D title stings, scene renders | `integrations/blender` | planned · M4+ |
| Lottie / Rive | vector motion overlays | `packages/motion-engine` + `integrations/` | planned · M4+ |
| Caption/subtitle services | burned-in or sidecar subtitles | `packages/video-engine` toolkit | planned · M3+ |

Ground rules:

- **Degrade gracefully** — no integration is load-bearing; the mock tier (ADR-0005)
  always produces real artifacts first, upgrades are drop-in.
- **Transparency** — every adapter stamps `meta.provider` on each artifact it
  creates, visible in the UI and audit logs.
- **Secrets** only via env (`.env`, git-ignored); never inside the render sandbox
  (ADR-0009).
- Adding a vendor = one provider file + one chain entry (ADR-0004) — no orchestrator changes.
