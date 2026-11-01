# CINEFORGE — Security Policy

## Secrets handling (binding for all agents)

1. **Never commit secrets.** `.env` is git-ignored; only `.env.example` (placeholders) is tracked.
2. Tokens shared in chat/planning documents are considered **burned**: they must be rotated by the owner and must never be copied into code, docs, logs, or CI variables in plaintext.
3. In code, secrets come from environment only (`os.environ` / `process.env`), never string literals.
4. Git history is append-only trust: if a secret lands in a commit, treat it as compromised — rotate, then clean history (owner-gated).

## Agent code execution sandbox (ADR-0009)

- Agent-generated code runs only in the worker/container context, never on the API host.
- FFmpeg/Pillow invocations use argv lists (no shell interpolation), confined to `CINEFORGE_STORAGE_ROOT`.
- Every job has a timeout; every path is validated against the project workspace root (no `..` escapes, no absolute host paths).
- Network access for render workers is deny-by-default (providers run in the API process, not the sandbox).
- Hardening backlog: CF-061 (seccomp/AppArmor profiles, memory/CPU caps, read-only rootfs).

## Input handling

- Uploaded media: size cap (`CINEFORGE_MAX_PROJECT_MB`), extension+magic-byte checks before ffprobe.
- Chat input is treated as untrusted text; prompt-injection attempts cannot grant tool access beyond the registered, sandboxed tool set.

## Disclosure

Found a vulnerability? Open a **private** security advisory (GitHub → Security tab) instead of a public issue.
