---
name: kickoff
description: Start the hackathon project after the official challenge is announced by converting it into an approved MVP plan, ownership split, and minimal verified skeleton.
---

# Kickoff

Use only after a human supplies the official challenge.

1. Preserve the challenge wording and extract constraints and judging criteria into `docs/HACKATHON_RULES.md` with sources.
2. Draft `docs/PROJECT.md`: problem, primary user, main job, MVP achievable in a few hours, non-goals, judging fit, two-minute demo path, risks, and mitigations.
3. Propose one minimal stack and explain tradeoffs. Ask the human before selecting or installing it.
4. With approval, update `docs/ARCHITECTURE.md` and split modules/files between Dima and Azim in their own STATUS sections. Minimize shared-file contention.
5. Create only the minimal project skeleton needed for the happy path; do not implement speculative features.
6. Wire the selected stack's existing lint, typecheck, tests, and build into auto-detection by `scripts/verify.ps1` without duplicating commands.
7. Run verification and record any cross-cutting decisions.

Return the agreed MVP, ownership split, next parallel tasks, and blockers.
