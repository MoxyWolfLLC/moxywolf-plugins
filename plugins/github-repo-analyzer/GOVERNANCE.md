# github-repo-analyzer — Governance

This plugin is held to the MoxyWolf plugin conformance standard. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
for the full standard. Every skill/command passes each of the five tests that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

The GitHub MCP write capabilities (`create_pr`, `create_issue`, `push_file`) carry the blanket rule:
**never open a PR, push a file, or create an issue without explicit human approval of the exact
change.** All analysis and reporting capabilities are read-only and run freely.

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `analyze-repo` | read-only | Health/quality/stack-conformance analysis; reads the repo, writes a local report only. |
| `reverse-prd` | read-only | Reverse-engineers a PRD from the repo; reads only, writes a local artifact. |
| `review-issues` | read-only | Structured security issue review (CWE/OWASP/NIST); reads issues, no writes. |
| `verify-fix` | read-only | Verifies whether closed issues were actually fixed; read-only audit. |
| `suggest-fixes` | side-effectful-gated | Generates fix suggestions one-at-a-time with HITL approval. Already HITL; never opens a PR / pushes / creates an issue without explicit approval of the exact change (Tests 1, 5). |
| `github-repo-analyzer` (skill) | side-effectful-gated | Shared workflow; any `create_pr` / `create_issue` / `push_file` write requires explicit human approval — no autonomous writes. |
