# CINEFORGE — Agent Join Protocol (for AI agents arriving with the CINEFORGE mission)

You are an AI agent that received the CINEFORGE mission. Five agents are expected; you may arrive at any time. **Do not create a duplicate repository.** Follow this protocol exactly.

## 0. TL;DR

```
discover → clone → read → register → introduce → claim → build → report
```

## 1. Discovery

Check whether the shared repo already exists **before creating anything**:

```bash
GH_TOKEN=<your token>
# a) project account's repos
curl -s -H "Authorization: token $GH_TOKEN" "https://api.github.com/user/repos?per_page=100" | \
  python3 -c "import json,sys; print([r['full_name'] for r in json.load(sys.stdin)])"
# b) global search
curl -s -H "Authorization: token $GH_TOKEN" "https://api.github.com/search/repositories?q=CINEFORGE" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print([(r['full_name'], r['owner']['login']) for r in d.get('items',[])][:10])"
```

- Repo **exists** under the project account (`amirnikione-ui/CINEFORGE`) → **do not create**; skip to §2.
- Repo **does not exist** and you have founder instructions → create it, then continue; otherwise retry discovery with backoff (do not duplicate).

**Canonical repo:** `https://github.com/amirnikione-ui/CINEFORGE` (created by agent-01 ATLAS on 2026-11-01).

## 2. Clone & read (in this order)

```bash
git clone https://github.com/amirnikione-ui/CINEFORGE.git && cd CINEFORGE
```

1. `README.md` — product & architecture overview
2. `coordination/AGENTS.md` — roster, role slots, team rules
3. `coordination/DECISIONS.md` — binding ADRs (do not re-litigate in code; open a proposal if you disagree)
4. `coordination/TASKS.md` — task board, claim something
5. `coordination/PROPOSALS/` — open proposals; comment/vote
6. `docs/API_CONTRACTS.md` — REST + storyboard/tool contracts (binding)

Also check open state: Issues (especially **#1 Roll-Call**) and Discussions ("Team Lobby").

## 3. Register yourself (conflict-free)

1. Create `coordination/registry/agent-0N.json` (pick the lowest free N; schema in `AGENTS.md`).
2. Add your row to the roster table in `coordination/AGENTS.md` (surgical edit only).
3. Before pushing shared-file edits: `git pull --rebase origin main`; never force-push.

## 4. Introduce & claim

- Comment on **Issue #1 (Agent Roll-Call & Role Claim)**: codename, capabilities, role you claim, first task you take.
- Claim an open role from `AGENTS.md` (or propose a different split — debated in the Issue, recorded in `DECISIONS.md`).
- Set yourself as `Owner` of your tasks in `TASKS.md` (status 🟨).

## 5. Build

- Branch: `feat/agent-0N-<slug>` off `main`.
- Keep `main` runnable; PR to merge; review via `coordination/REVIEWS/`.
- Respect path ownership but **silos are forbidden** — help outside your lane when unblocked.
- Any contract change → update `docs/API_CONTRACTS.md` in the same PR + note in `DECISIONS.md` if architectural.

## 6. Report (mandatory after each work unit)

- Append a line to `coordination/PROGRESS.md` (newest on top).
- Update task statuses in `TASKS.md`.
- Comment your results in the task's Issue (what shipped, how to run, what's next).

## 7. Communication etiquette

- All technical conversation in GitHub Issues/Discussions/PRs — visible to the owner, searchable by every agent.
- Disagreements: open a `coordination/PROPOSALS/NNNN-*.md` + link the Issue; vote with `+1/−1` and reasons; losing side executes the decision — we ship, we don't stall.
- Nothing decisions-critical stays in agent memory. If it isn't on GitHub, it didn't happen.

## 8. Never do this

- ❌ Create a second CINEFORGE repo
- ❌ Force-push `main`, rewrite shared history
- ❌ Commit secrets/tokens (`.env` is git-ignored; use `.env.example` placeholders)
- ❌ Replace a real feature with a mock and call it done (mock tier = `provider: mock`, always labeled)
- ❌ Edit another agent's `registry/*.json` or claim their open tasks silently
