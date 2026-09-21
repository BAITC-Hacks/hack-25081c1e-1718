---
name: demo-prep
description: Prepare a hackathon submission in the final hours by validating a clean-clone run, polishing the README, capturing screenshots, and tightening a two-minute demo.
---

# Demo preparation

1. Freeze scope to the demonstrated happy path; list known limitations instead of hiding them.
2. Follow the README from a clean clone or clean temporary worktree. Fix every missing prerequisite, environment-variable name, seed step, and run command.
3. Run `pwsh ./scripts/verify.ps1`; repair failures without broad refactors.
4. Polish README sections: problem, solution, team, architecture summary, prerequisites, exact run steps, verification, demo, and known limitations. Follow any newer official submission requirements.
5. Capture clear screenshots of the real app and key result. Do not use mock data without disclosure.
6. Write and rehearse a two-minute script: problem, user action, visible result, differentiator, closing value. Include a fallback if a network/model call fails.
7. Confirm secrets are absent, `.env.example` contains names only, and required links/assets open.
8. Record final blockers and handoff; checkpoint only if event rules and access allow pushing.

Do not add new features unless a human explicitly reprioritizes the final hours.
