# Agent sync protocol

## Boundaries

- Identity is local in `.agent-identity`: `dima` or `azim`.
- Write only `docs/agents/<me>/` and your own section of `docs/STATUS.md`.
- Read everything. Ownership of product modules is assigned in `docs/STATUS.md` after kickoff.
- Ask in `shared/QUESTIONS.md` before touching the other person's owned area unless trivial.

## Start a session

1. `git pull --rebase --autostash`
2. Read `AGENTS.md`, `docs/PROJECT.md`, and `docs/STATUS.md`.
3. Read the tail of `docs/DECISIONS.md`.
4. Read the other person's `HANDOFF.md` and last ~30 lines of their `LOG.md`.
5. Run `git log --oneline -15`.
6. State three lines: understood state; planned work; blockers/coordination.

## While working

- After each meaningful change append to your LOG:
  `## YYYY-MM-DD HH:MM - what / why / files / impact`.
- Add `[AFFECTS-OTHERS]` when changing an API/contract, schema, dependency,
  environment variable, design token, or folder structure.
- For every `[AFFECTS-OTHERS]` change, append a record to `docs/DECISIONS.md`.
- Keep commits small and use `scripts/checkpoint.ps1`; during the active event aim for a verified checkpoint about every 4 active minutes. Fetch and inspect incoming paths plus teammate STATUS/HANDOFF first; do not publish broken or empty timer commits.
- During a timed hackathon, use `docs/PROJECT.md` and `docs/ARCHITECTURE.md` as the shared project memory. Every handoff names completed work, changed paths/contracts, commit/push state, next action, and blockers.
- Integrate continuously: push small verified commits when permitted, pull/rebase before dependent integration, and reserve a time buffer for a clean run and demo. Never force-push or overwrite the other person's changes.

## Subagents

- Use project roles from `.codex/agents/` for bounded independent analysis or verification.
- Subagents never impersonate Dima/Azim and never edit personal LOG, HANDOFF, or STATUS sections.
- Prefer parallel read-only work. Allow code edits only with an exclusive file scope assigned by the main agent.
- The main agent waits for results, validates evidence, and remains responsible for the final change.

## End a session

1. Update only your STATUS section.
2. Replace your HANDOFF with current state, next three steps, and blockers.
3. Run checkpoint to verify, commit, rebase, and push if event rules/access allow.

## Conflicts

Keep both sides' intent; never drop teammate changes. If uncertain, stop the merge,
write the question in `shared/QUESTIONS.md`, and tell the human.
