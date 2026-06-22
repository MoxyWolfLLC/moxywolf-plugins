# gstack-execution — Governance

This plugin is held to the MoxyWolf plugin conformance standard. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
for the full standard. Every skill/command passes each of the five tests that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

The code-write path (`gstack-ship`) carries the no-auto-merge rule: **never auto-push to a
protected branch and never auto-merge — a named human owns the merge; the pipeline prepares the
PR and stops.**

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `gstack-ship` | side-effectful-gated | Prepares PR only. No auto-push to protected branch, no auto-merge; a named human owns the merge (Tests 1, 5). Stops on blocking test/CRITICAL review findings. |
| `gstack-review` | read-only | Pre-landing structural review; reports findings, no writes. |
| `gstack-codex-review` | read-only | Adversarial review of just-committed code; reports only. |
| `gstack-cso` | read-only | Security audit (OWASP, STRIDE, supply chain, secrets); reports only. |
| `gstack-investigate` | read-only | Root-cause debugging with hypothesis testing; analysis only. |
| `gstack-qa` | side-effectful-gated | Browser QA; any code fixes are local edits offered to the human, not pushed (Tests 1, 5). |
| `gstack-browse` | read-only | Browser-based page verification / dogfooding; observation only. |
| `gstack-design` | generate | Design-system consultation + local UI generation; no deploy. |
| `gstack-execution` (skill) | side-effectful-gated | Shared methodology; governs the commit/push/PR boundary above — no autonomous irreversible action. |
