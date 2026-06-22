# vtt-to-text — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests for the full standard. Every skill/command passes each test that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

This plugin is a pure local transform — VTT captions in, clean text out. No sends, no external writes.

| Skill / command | risk_tier | note |
|---|---|---|
| `convert-vtt` (command) | generate | Converts pasted VTT captions into a clean local text file. Pure local transform; output not auto-shipped. |
| `vtt-to-text` (skill) | generate | Underlying VTT→text conversion protocol. Local transform only. |
