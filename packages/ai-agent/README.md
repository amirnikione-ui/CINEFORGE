# cineforge-ai-agent

The director agent's **stable tool contract** (see `docs/API_CONTRACTS.md` §Tool interface).

`ai_agent.TOOLS_JSON` is the OpenAI-style tool schema list handed to the LLM in the
chat tool-loop. Each entry describes name, description and JSON-schema parameters.

| Tool | Input | Output |
|---|---|---|
| `write_storyboard` | brief, style, platform, duration_hint_s | storyboard asset + normalized scene plan |
| `generate_concept_frames` | storyboard (optional) | one frame asset per scene |
| `generate_narration` | storyboard (optional) | one audio asset per narrated scene |
| `generate_music` | mood, duration_s | music-bed audio asset |
| `render_slideshow` | storyboard (optional) | video asset (+ Job row with progress) |
| `build_remotion_project` | storyboard (optional) | directory asset (editable Remotion comp) |
| `probe_media` | path or asset_id | duration/size/fps/audio summary |
| `analyze_video` | path or asset_id | probe summary + scene-detect cuts |

## Rules

- Tool implementations live in `backend/app/agent/tools.py` and always attach
  `meta.provider` to every asset they create.
- The orchestrator (`backend/app/agent/orchestrator.py`) drives the loop:
  `chat_with_tools()` returns one step at a time; the orchestrator executes the
  named tool, appends a `role:"tool"` message, and repeats (max 8 steps).
- Any tool failure becomes `ToolError` -> the orchestrator either retries via the
  provider chain or reports the failure honestly in the assistant message.
- The offline tier never fakes success: when no LLM key is configured the
  deterministic mock director plans the same tools and every artifact is labeled
  `provider: "mock"`.

Helpers: `tool_names()`, `get_tool(name)`, `contract_summary()`.
