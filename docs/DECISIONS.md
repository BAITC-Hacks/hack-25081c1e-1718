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

### 2026-09-23 - Keep final decisions within measured channels

- Decision: Estimate each campaign from pilots of that same channel. Remove automatic SMS-to-advertising/call extrapolation. Capture actual public pilot sample size, budget delta, observed total and remaining resources. Add offline controller comparisons via scripts/benchmark.py and scan both working tree and Git index for secrets.
- Why: Guide lists effectiveness multipliers but does not fully specify the semantics needed for transferring observed_lift_ratio. Previously an untested expensive channel could enter the final plan. The public run_pilot response supplies additional useful operational evidence without reading hidden internals.
- Who: Dima, independent of Azim's candidate_model and web work.
- Consequences: [AFFECTS-OTHERS] Optional report-v1 fields added; no candidate interface or Azim-owned files changed. On paired seeds 0..9, median improved from −14 363 to −2 150 and positive runs from 3/10 to 5/10; economic robustness still incomplete. Historical priors no longer reduce the estimated pilot noise variance. New evaluations remain local mock evidence only.

### 2026-09-23 - Synchronize roughly every four active minutes

- Decision: Both owners aim for small verified commits/pushes about every four active minutes, checking remote changed paths and each other's STATUS/HANDOFF first. Fetch can run during evaluation; pull/integration waits for the active evaluation to finish so inputs do not change mid-run. Existing file ownership remains in force.
- Why: Explicit user request to increase cadence and prevent duplicate work or missed changes.
- Who: Dima records the user's instruction for both owners; each edits their own status.
- Consequences: [AFFECTS-OTHERS] AGENTS, agent-sync, team guide, work plan and reminder default updated. No empty/broken timer commits; unpushed remote-machine edits remain invisible. Latest fetch at 14:06 showed no Azim commits yet; work on Dima's controller continues independently.

### 2026-09-23 - Reduce exploration cost and make release evidence reproducible

- Decision: Scout with the cheapest documented available channel while keeping final estimates channel-specific. Anchor PowerShell workflows to repository root; add an explicit offline -Release CSV generation/structure gate. Benchmark records resolved baseline/source/shared-input hashes and requires successful pilots and valid resource counters.
- Why: Pilot spend is part of net revenue. Existing cwd-dependent verification could skip checks; missing CSV freshness and unstable baseline references weakened evidence.
- Who: Dima; candidate and web ownership unchanged.
- Consequences: [AFFECTS-OTHERS] Channel choice changes the default plan, regenerated CSV included. Paired median0..9 improves to +16 068; heldout10..19 median +1 170, 5/10 positive. No final robustness claim. verify -Release rewrites submission.csv explicitly; checkpoint stays selective.

### 2026-09-23 - Confirm paid channels with their own pilot pairs

- Decision: Reserve up to four slots after cheap scouting for paid-channel pairs on confirmed segments. Public multipliers rank hypotheses only; final paid campaigns still require two same-channel observations. Cap promotion pilot spend at20% of budget remaining after scouts and reserve full campaign resources. Independently validate returned campaigns against captured copies of public inputs and resource counters in benchmark.
- Why: With Azim's cautious candidates the earlier SMS-only controller beat push-only. Direct measurement can justify stronger channels without unsupported extrapolation. A self-reported plan alone is insufficient validation evidence.
- Who: Dima; Azim's candidate/web areas untouched. Integrated Azim's217e338 handoff.
- Consequences: [AFFECTS-OTHERS] Optional event action channel_check and channel field; v1/candidate contracts preserved. Heldout30..39 median+607623 versus SMS+579470, both10/10 positive; minimum worsened to+203004 versus+466908. Keep that risk visible; no guarantee of real/judge profit.

### 2026-09-23 - Publish only a validated complete report

- Decision: Validate actual returned campaigns and reported public resource stages before atomic JSON replacement. Preserve the previous report on technical failure, keep a nonzero exit code, and include optional code provenance captured before evaluation. Preserve caller-selected offline/OpenAI modes.
- Why: Azim's interface needs a complete real report and a way to distinguish stale runs from current code. A partial or invalid file could hide a failed evaluation.
- Who: Dima; web/ remains Azim's module.
- Consequences: [AFFECTS-OTHERS] Optional provenance/validation in report1.0; no mandatory UI changes or new dependencies. Corrected WORK_PLAN's old handoff label to prevent duplicate candidate work.

### 2026-09-23 - Bound scout cost before selecting channel strength

- Decision: Choose the strongest documented scout channel whose worst-case exploration cost fits15% of initial available budget, otherwise the cheapest channel. Preserve per-pilot/final resource checks and same-channel confirmation. A missing optional advisor module now fails into autonomous operation.
- Why: Cheap push exploration had a lower worst-case outcome than SMS in earlier comparisons; full-budget bounds permit better signal without blind expensive calls. Official artifact list does not guarantee extra helper modules are uploaded.
- Who: Dima; unchanged Azim ownership and candidate interface.
- Consequences: [AFFECTS-OTHERS] Optional scout_channel in report1.0. Seed42+685150; nine new seeds40,41,43..49 median+657090 versus prior+582083, both9/9 positive. Full40..49 includes known42 and is labeled accordingly. A standalone bundle preserving the full specialist logic follows separately.

### 2026-09-23 - Package the complete strategy as a single upload agent

- Decision: Add package_submission.py to embed our own candidate/advisor sources into a standalone agent without changing their logic. Package the official CSV, requirements and optional provenance manifest. Syntax/shape/secret scan before writes; captured inputs, atomic files/zip. Keep generated output ignored and reproducible from Git.
- Why: Official list names agent.py and CSV, so relying on separately uploaded helper modules would risk failure or weaker fallback. The team still benefits from separate owned source modules.
- Who: Dima; Azim's modules read for packaging only, not edited.
- Consequences: [AFFECTS-OTHERS] Release workflow requires verify -Release then packaging; organizer data remain runtime inputs. Isolated Python run without helper files PASS+685150 and exact CSV hash match. Integrated Azim UI593667d and imported newest report:3 campaigns,20 pilots,685150 net,53402 budget/9394 contacts after plan, no console errors.

### 2026-09-23 - Develop the product interface and grounded OpenAI answers in parallel

- Decision: User confirmed more than two hours remain. Start a120-minute stage: Azim owns web/DESIGN/DEMO/README; Dima owns core/local server/report assistant and API contract. Keep candidate inputs frozen during controller comparisons. Use the existing skills, browser and OpenAI Docs MCP; no heavy framework or arbitrary plugin installation.
- Why: The user wants a more polished usable product, actual OpenAI answers and better campaign decisions. The current viewer cannot start a run or ask questions. Existing API advice and an offline report must be distinguished clearly.
- Who: Dima under explicit user direction; Azim receives a self-contained prompt and can begin design immediately.
- Consequences: [AFFECTS-OTHERS] docs/API.md fixes same-origin run/report/chat contracts, token/origin restrictions, honest offline mode and report citations. New server modules do not enter the official agent bundle. Quality is measured by campaign net/resource safety and evidence, not a fabricated detection-accuracy percentage. Four-minute Git checkpoints continue.

### 2026-09-23 - Deliver the local run and report assistant API

- Decision: Implement the agreed API with Python stdlib, isolated run output identities, immutable server snapshots and Responses API answers constrained to public report references. No new dependencies. Allow api.mjs/integration.mjs requested by Azim; keep his source ownership.
- Why: The interface needs actual analysis and grounded answers while the standalone evaluator contract stays reproducible.
- Who: Dima, with independent read-only review; Azim integrates the frontend.
- Consequences: [AFFECTS-OTHERS] server.py --offline/--ask-key serves loopback 8765. Startup has no report; successful jobs create output/runs/id.json, then an in-memory report_id. Key never enters HTTP/web/files, offline child receives no key. One analysis and one answer at a time, bounded handlers/timeouts/rate limits. Live online advice and report Q&A succeeded; a single net result does not establish economic superiority. CLI --run-id is server-internal; normal report export and official submission remain unchanged.
