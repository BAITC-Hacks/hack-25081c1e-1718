# Agent Guide

This repository is a project-agnostic HackAlem AI harness. The challenge,
users, MVP, non-goals, stack, judging fit, and demo path belong in
`docs/PROJECT.md`; do not invent them before kickoff.

## Identity and ownership

- Read `.agent-identity`; it must contain exactly `dima` or `azim` and is local-only.
- Write agent notes only under `docs/agents/<me>/` and only your named section in `docs/STATUS.md`.
- Read all repository files. Respect module ownership recorded in `docs/STATUS.md`.
- To change the other owner's area, ask in `docs/agents/shared/QUESTIONS.md` unless trivial.

## Session start

1. Run `git pull --rebase --autostash`.
2. Read this file, `docs/PROJECT.md`, `docs/STATUS.md`, the tail of
   `docs/DECISIONS.md`, the other person's `HANDOFF.md`, and their last ~30 log lines.
3. Run `git log --oneline -15`.
4. State in three lines: understood state, intended work, blockers/coordination.
5. Use the `agent-sync` skill for the full checklist.

## During and session end

- Append meaningful work to your `LOG.md` as
  `## YYYY-MM-DD HH:MM - what / why / files / impact`.
- Tag dependency-facing changes `[AFFECTS-OTHERS]` and append a decision to
  `docs/DECISIONS.md` for APIs, schemas, dependencies, env vars, design tokens,
  or folder structure.
- End by updating only your STATUS section and replacing your HANDOFF with
  current state, next three steps, and blockers.
- Run `pwsh ./scripts/checkpoint.ps1 "type: imperative message"` to verify,
  commit, rebase, and push. If event rules or access block pushing, commit locally
  and report the blocker.

## Commits and verification

- Trunk-based on the default branch unless protection/rules require a short PR branch.
- Use Conventional Commits: `feat|fix|docs|chore|refactor|test`, imperative,
  one idea per commit. Checkpoint every logical unit and about every 20 active minutes.
- Before every commit, `pwsh ./scripts/verify.ps1` must pass.
- Never force-push or rewrite pushed history. Preserve both sides in conflicts;
  if intent is unclear, ask in `docs/agents/shared/QUESTIONS.md` and tell a human.

## Build rules

- Use Codex during development; this is a published event requirement.
- Run the `kickoff` skill only after the challenge is announced and ask before choosing a stack.
- For any UI work, use the `ui-ux-design` skill before coding.
- Ask before adding heavy dependencies or making large refactors; record accepted
  cross-cutting choices in append-only `docs/DECISIONS.md`.
- Keep secrets out of Git and files; credentials come only from environment variables.
- Do not commit generated dependencies, caches, real `.env` files, or unrelated artifacts.

## Definition of done

- Scope and ownership are respected; docs/contracts reflect behavior.
- Relevant tests/checks and `scripts/verify.ps1` pass.
- UI work includes accessible states and screenshots at 375/768/1440 px.
- Own LOG, STATUS, and HANDOFF are current; dependency-facing changes are flagged.
- The change is a small Conventional Commit, synced without discarding teammate work.

See `docs/HACKATHON_RULES.md`, `docs/agents/README.md`, and the focused skills in
`.agents/skills/` instead of duplicating their details here.
