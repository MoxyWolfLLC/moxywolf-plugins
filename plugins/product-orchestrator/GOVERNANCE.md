# product-orchestrator — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests for the full standard. Every skill/command passes each test that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

This plugin is **advisory**: it wraps the Council deliberation engine with product-specific
roles and produces decision support, not external action. The execution skills it routes to
carry their own risk tiers and gates.

| Skill / command | risk_tier | note |
|---|---|---|
| `product-orchestrator` (skill) | read-only / generate | Orchestrates multi-model deliberation and routes to downstream execution skills. Deliberation is advisory (`read-only`); any artifact it composes is `generate`. Takes no irreversible external action itself. |
| `product-scope` (command) | generate | Structured deliberation on a scope decision; produces a decision-support write-up. Advisory output, not auto-shipped. |
| `product-arch` (command) | generate | Deliberation on an architecture decision; produces an analysis/recommendation. Advisory. |
| `product-gtm` (command) | generate | Deliberation on go-to-market positioning; produces a recommendation. Advisory. |
| `product-prd` (command) | generate | Generates a Product Requirements Document (local artifact). Does not ship or execute. |
| `product-sprint` (command) | generate | Full sprint orchestration with deliberation gates; produces planning artifacts. The deliberation gates are advisory; downstream execution skills own their own risk. |
| `project-charter` (command) | side-effectful-gated | Creates/updates a project's **`CHARTER.md` written to the project root / vault** (and pulls candidate principles from decision records). Interactive (AskUserQuestion) and durable-governance-shaping, so the write is confirmed with the user before landing (Tests 1, 5). The decision-record / charter write is the gated surface; the deliberation that informs it is `generate`/`read-only`. |
