# cineforge-ai-providers

Vendor-agnostic capability layer for CINEFORGE (ADR-0004/0005).

## Capabilities

| Capability | Method | Notes |
|---|---|---|
| `llm` | `complete(system, messages, json_mode)` / `chat_with_tools(system, messages, tools_schema, max_steps)` | `chat_with_tools` performs **one** tool-mode request and returns `{"content", "tool_calls":[{"id","name","arguments"}]}`; the orchestrator drives the loop. |
| `image` | `generate_image(prompt, out_path, width, height, **kw)` | writes a real file; metadata includes `provider` |
| `tts` | `synthesize(text, out_path_wav)` | metadata includes real `duration_s` |
| `music` | `generate_music(mood, duration_s, out_path_wav)` | |
| `stt` | `transcribe(wav_path) -> str` | |
| `video` | `generate_video(...)` | M2+; mock tier points to the local FFmpeg/Remotion pipeline |

## Chains

Configured via env, parsed in `config.py`:

```
CINEFORGE_LLM_CHAIN=zai,openai,anthropic,mock
CINEFORGE_IMAGE_CHAIN=openai,mock
CINEFORGE_TTS_CHAIN=openai,mock
CINEFORGE_MUSIC_CHAIN=mock
CINEFORGE_STT_CHAIN=openai,mock
CINEFORGE_VIDEO_CHAIN=mock
```

`ProviderRegistry.walk`: first `available()` provider wins (key present / local
capability); call errors trigger the next provider; the terminal `mock` tier
produces **real local artifacts** (Pillow frames, stdlib WAV audio) always
labeled `provider: "mock"` — no code path pretends to be a real vendor.

## Health

`registry.status()` powers `GET /health`, e.g.
`{"llm": ["zai", "openai*", "mock"], "image": ["mock"], ...}` where `*` marks
a configured-but-unavailable provider.

## Adding a vendor

One file + one entry in `registry.py` (`_builtin_factory` / vendor support map)
+ a chain env var. Implement only the capability classes you support; other
capabilities raise honest errors and the registry falls through.
