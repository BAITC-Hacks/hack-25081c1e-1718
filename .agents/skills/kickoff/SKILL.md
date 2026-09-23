---
name: kickoff
description: Start the hackathon project after the official challenge is announced by converting it into an approved MVP plan, ownership split, and minimal verified skeleton.
---

# Kickoff

Use only after a human supplies the official challenge.

1. Preserve the official challenge wording, source, hard constraints, judging criteria, submission format, and deadline in `docs/HACKATHON_RULES.md`. Mark unknowns explicitly. Clarify whether the requirement is an agentic system, specifically multi-agent, or either; capture required autonomy, tools, agent coordination, and judging evidence from official materials or organizer answers. Do not infer a required agent count or architecture from the event label alone.
2. Confirm the expected delivery surface (web, mobile, API, or another format) from the challenge. Treat a web app as the working assumption only until confirmed. Draft `docs/PROJECT.md`: problem, primary user, name and one-line pitch, main job, an MVP sized for the actual remaining time, non-goals, judging fit, two-minute demo path, risks, mitigations, and the smallest agent architecture that satisfies the confirmed requirement. Prefer one agent unless collaboration between distinct roles materially serves the task or rules explicitly require multiple agents.
3. Generate a short list of memorable, pronounceable names tied to the confirmed user/problem; check obvious conflicts and unsuitable meanings, then recommend one with a one-line pitch. Do not spend MVP time on exhaustive naming research. Propose the smallest viable stack and explain tradeoffs. Ask the human before selecting or installing it; after approval, do not wait for further approval for routine reversible implementation choices.
4. Agree a shared project summary and interfaces in `docs/ARCHITECTURE.md`. Split Dima and Azim into non-overlapping file/module ownership in their own STATUS sections. Record API, schema, environment, dependency, and folder decisions once; link to those contracts instead of re-explaining them in chat.
5. Build the thinnest end-to-end happy path first. Defer speculative features and polish until that path works.
6. Wire the selected stack's existing lint, typecheck, tests, and build into `scripts/verify.ps1` without duplicating commands. Run only the checks needed for changed areas during development; run the full verifier at milestones and before delivery.
7. Set a shared deadline and milestone plan from the actual event clock: challenge/MVP agreement, first vertical slice, integrated demo, hardening, submission. Keep a visible time buffer for final integration and demo.
8. Commit and push small coherent units to the team repository as soon as they are verified. Pull/rebase before starting work and before integration; never force-push, reset, or overwrite teammate changes. If push protection or access blocks progress, keep commits local and report the blocker.
9. At each handoff, update your own LOG/HANDOFF and STATUS section with completed work, files/contracts changed, commit or push state, next action, and blockers. Read the teammate's handoff before taking dependent work.
10. Reserve the final phase for `demo-prep`: clean-clone run, verification, README, secrets check, two-minute script, and fallback path.

Return the agreed MVP, shared architecture/contracts, ownership split, milestone times, next parallel tasks, and blockers.
