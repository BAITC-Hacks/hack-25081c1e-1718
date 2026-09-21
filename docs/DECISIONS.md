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
