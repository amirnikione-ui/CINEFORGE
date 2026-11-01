# CINEFORGE — Review System

> Every PR gets a cross-agent review before merge into `main`. Reviews are recorded here for substantive changes.

## Process

1. Reviewer picks a PR not authored by themselves (agents review each other — no self-merge for M1+ features).
2. Use the checklist below; request changes inline on GitHub; summarize the verdict.
3. For architectural changes, link the Proposal/ADR and record the decision outcome in `REVIEWS/RR-NNNN-<slug>.md`.

## Checklist (copy into PR review)

- [ ] Runs locally (`uvicorn` boots / `next build` passes / tests green)
- [ ] No secrets, no tokens, no absolute local paths
- [ ] Follows `docs/API_CONTRACTS.md` (or updates it in the same PR)
- [ ] New provider follows `packages/ai-providers` interface + registered in a chain
- [ ] Media code: argv-list ffmpeg calls, workspace-confined paths, timeouts set
- [ ] Mock vs real behavior clearly labeled (`meta.provider`)
- [ ] Tests added/updated; no skipped assertions
- [ ] Docs updated (`PROGRESS.md` log line; README/TASKS if scope changed)

## Review records

| ID | PR/Scope | Reviewer | Verdict | Notes |
|---|---|---|---|---|
| — | — | — | — | (none yet; bootstrap commit authored pre-team) |
