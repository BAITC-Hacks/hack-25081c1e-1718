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

## Work

- Edit only `docs/agents/<me>/` and your section of `docs/STATUS.md`.
- Respect product ownership in STATUS. Ask in `shared/QUESTIONS.md` before editing the other owner's area unless trivial.
- After meaningful changes append to your LOG:
  `## YYYY-MM-DD HH:MM - what / why / files / impact`.
- Mark changes to contracts, schemas, dependencies, env vars, design tokens, or folder structure `[AFFECTS-OTHERS]` and append a decision.

## Finish

- Update only your STATUS section.
- Replace your HANDOFF with current state, next three steps, and blockers.
- Run `pwsh ./scripts/checkpoint.ps1 "type: imperative message"` if pushing is allowed.
- On conflicts, preserve both intents. If unclear, stop, ask in QUESTIONS, and tell the human.
