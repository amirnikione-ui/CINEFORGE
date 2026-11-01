# PROPOSAL 0002 — Streaming chat UX (SSE) for the director conversation · Status: OPEN

Author: agent-04 (HALO) · Cross-review requested: FORGE (API seam) · 2026-11-02 · Blocks: nothing (upgrade path) · Relates: ADR-0002/0003, contracts «Chat»

## Context

Contracts v0.1 define `POST /api/projects/{pid}/chat` as **synchronous**: plan + core tools complete,
render is a Job. This is simple, debuggable and shippable — and it is what M1 implements today.
The cost: for LLM-heavy plans the user stares at a "Director is planning…" placeholder (observed
p50 ≈ 3–8 s online; offline mode answers in ~2 s).

## Recommendation

Keep the sync endpoint as the **contract of record** for M1; add a **parallel** streaming variant in M2:

1. `POST /api/projects/{pid}/chat/stream` → `text/event-stream` with typed frames:
   `status → plan → tool_call → tool_result* → artifact* → done` (final frame carries the same
   ChatResponse payload; identical persistence semantics — no contract drift).
2. Web client prefers `/stream` and transparently falls back to sync on any non-200/SSE response.
3. Heartbeat `ping` every 15 s; unknown event types must be ignored by clients (forward-compat).

## Alternatives

- WebSocket channel: rejected — SSE is unidirectional, proxy-friendly, and auto-reconnects.
- Streaming inside the existing endpoint via content negotiation: rejected — muddies the contract.

## Consequences

- Zero change to tool/persistence logic; only the transport wraps it.
- Tasks: web hook (`useAgentStream`), FastAPI StreamingResponse route, contract doc addition.
- Owner: agent-02 (web) + agent-03 (API) — needs one cross-review per ADR-0007.
