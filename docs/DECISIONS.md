# Decisions (append-only)

Never edit or delete earlier entries. Append corrections as new decisions.

## Template

### YYYY-MM-DD - Decision title

- Decision:
- Why:
- Who: Dima / Azim / both
- Consequences:

### 2026-09-21 - Use a repository-scoped agent harness

- Decision: Keep shared agent guidance, skills, status, and MCP configuration in the repository; keep identity and tokens local.
- Why: Both machines need the same workflow without sharing credentials.
- Who: both
- Consequences: `.agent-identity` and secrets remain untracked; shared workflow changes require review.

### 2026-09-21 - Use bounded challenge-analysis subagents

- Decision: Enable up to three project-scoped subagents for domain-neutral challenge analysis, security review, and verification; specialize challenge analysis to the announced track without presuming a specific challenge. Keep product implementation owned by the main human agents unless files are explicitly isolated.
- Why: Parallel read-heavy work improves coverage while limiting token use and merge conflicts.
- Who: Dima
- Consequences: Subagents must stay within authorized hackathon/local targets and may not edit personal coordination notes.

### 2026-09-23 - Confirm agent architecture from the challenge

- Decision: Treat agentic AI as the event context, but confirm whether a single-agent or multi-agent design is required or preferred from the official challenge and judging criteria. Do not presume an agent count; choose the smallest architecture that meets confirmed requirements.
- Why: The event label alone does not establish the solution architecture expected for this telecom challenge.
- Who: Dima
- Consequences: Kickoff records the requirement and evidence in `docs/HACKATHON_RULES.md` and `docs/PROJECT.md` before implementation.

### 2026-09-23 - Treat web delivery and product name as kickoff decisions

- Decision: Use a web app as the provisional demo format, subject to challenge and team constraints; choose a concise product name and one-line pitch after the problem and user are known.
- Why: The likely web demo should be planned early, while naming before the challenge is known risks a poor fit.
- Who: Dima
- Consequences: Kickoff validates delivery format, proposes a short name list, and records the selected identity in `docs/PROJECT.md`.

### 2026-09-23 - Start ARPU Compass for the announced Beeline case

- Decision: Use the issued participant guide and pasted judging rubric as the specification; plan 300 minutes for two humans. Use one autonomous Python agent with pilot feedback, optional web report and optional bounded LLM advisor.
- Why: The mandatory contract is Agent.act(env), pilots and reproducible submission.csv; historical IDs do not join to the target audience. A working file-based submission has priority.
- Who: Dima, under the user's instruction to prepare the full two-person plan and stack.
- Consequences: [AFFECTS-OTHERS] PROJECT/ARCHITECTURE/WORK_PLAN define Dima and Azim ownership and candidate/report contracts. Use Python 3.12 with verified local pandas/NumPy versions. Azim confirms his own STATUS. Runtime target <5 minutes while guide/template inconsistency is resolved.

### 2026-09-23 - Preserve the participant package and make checkpoint selective

- Decision: Copy organizer files unchanged to repository root because runners import agent from there; retain the original unpacked directory locally and ignore the duplicate. Checkpoint accepts explicit -Paths or a reviewed staged index, checks native Git failures, and autosave only reminds.
- Why: Both developers need identical runnable source data and safe independent commits without staging each other's unfinished files.
- Who: Dima
- Consequences: [AFFECTS-OTHERS] Organizer source/data remain unmodified. Run official commands from root. ARPU_PYTHON optionally selects a local Python for verify.ps1. Generated output/reports are ignored; submission.csv is tracked. Initial baseline is documented as noncompetitive with evaluator status FAIL; it is not the final solution.

### 2026-09-23 - Promote OpenAI integration after explicit user instruction

- Decision: Dima owns llm_advisor.py and integrates OpenAI into pilot prioritization and feedback, immediately after the first scaffold push. Earlier P2 scheduling is superseded for this bounded integration; Azim's data/web areas stay assigned to Azim.
- Why: The user explicitly requested the agent system with OpenAI and an early GitHub handoff.
- Who: Dima under the user's latest instruction.
- Consequences: [AFFECTS-OTHERS] Use Responses structured outputs with a candidate-ID allowlist, at most two short requests, timeout and offline fallback. OPENAI_API_KEY comes only from environment; OPENAI_MODEL selects the model; ARPU_OFFLINE=1 disables network. No full customer records or credentials in reports. Numerical constraints remain enforced by Python. Implementation follows in a separate commit.

### 2026-09-23 - Publish Dima's integrated core while Azim's modules remain separate

- Decision: Implement bounded OpenAI initial/feedback, adaptive confirmation, strict candidate normalization, non-overlapping allocation, report export and a hidden memory-only key launcher. Preserve the three-argument candidate_model interface; Azim owns candidate_model.py, analysis/, web/ and substantive README work. Dima made only factual README status/command updates for this handoff.
- Why: The user asked to finish Dima's current files, commit/push, describe current state and provide a precise independent task for Azim.
- Who: Dima
- Consequences: [AFFECTS-OTHERS] Report v1 is extended compatibly with planned_resources, allocation, events, advisor and evaluation. Checkpoints are offline. API integration is verified live, but economic quality remains below G3: current 3/10 positive and negative median. Early history-transfer experiment was rejected; built-in candidates use cautious price hypotheses until Azim's specialist module. Keep 1a025b4 as the reference; do not present this integration commit as a final winning strategy.
