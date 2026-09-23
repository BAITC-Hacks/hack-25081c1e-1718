---
name: agent-sync
description: Synchronize Dima and Azim at the start, during, and end of a repository work session while avoiding conflicting edits.
---

# Agent sync

Read `.agent-identity`; stop this workflow if it is absent or not `dima`/`azim`.

## Start

- Run `git pull --rebase --autostash`.
- Read `AGENTS.md`, `docs/PROJECT.md`, and `docs/STATUS.md`.
- Read the tail of `docs/DECISIONS.md`.
- Read the other person's HANDOFF and last ~30 LOG lines.
- Run `git log --oneline -15`.
- State exactly three short lines: understood state; planned work; blockers/coordination.
- During an active event, also read the current shared project summary and latest handoff before starting dependent work; avoid repeating repository-wide reads when the same session has not changed.

## Work

- Edit only `docs/agents/<me>/` and your section of `docs/STATUS.md`.
- Respect product ownership in STATUS. Ask in `shared/QUESTIONS.md` before editing the other owner's area unless trivial.
- After meaningful changes append to your LOG:
  `## YYYY-MM-DD HH:MM - what / why / files / impact`.
- Mark changes to contracts, schemas, dependencies, env vars, design tokens, or folder structure `[AFFECTS-OTHERS]` and append a decision.
- Keep `docs/PROJECT.md` and `docs/ARCHITECTURE.md` as the shared source of truth for product intent and interfaces. Tell the teammate what changed, why, affected paths, commit/push state, and any action needed; do not assume they saw private Codex context.
- Prefer a short written handoff at meaningful integration points over continuous status chatter. Before editing a teammate-owned file, coordinate in `docs/agents/shared/QUESTIONS.md` unless ownership explicitly allows it.
- Commit and push verified, coherent units during the event when repository rules allow. Pull/rebase before integrating, preserve both sides on conflicts, and never force-push or discard teammate work.

## Finish

- Update only your STATUS section.
- Replace your HANDOFF with current state, next three steps, and blockers.
- Run `pwsh ./scripts/checkpoint.ps1 "type: imperative message"` if pushing is allowed.
- On conflicts, preserve both intents. If unclear, stop, ask in QUESTIONS, and tell the human.
