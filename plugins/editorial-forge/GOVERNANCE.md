# editorial-forge — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests for the full standard. Every skill/command passes each test that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

This plugin produces author-owned creative work plus an authorship record. There is no publish or
send step — output stays local for the author to use. The authorship record is itself the provenance
trail for every copyrightable decision.

| Skill / command | risk_tier | note |
|---|---|---|
| `forge-start` / `forge-resume` / `forge-status` (commands) | generate | Scaffold, resume, or report an authoring project locally. No external writes. |
| `editorial-forge` (skill) | generate | Transforms AI-generated content into author-owned work; writes chapters + authorship record locally. No publish/send. |
| `voice-architect` (skill) | generate | Extracts an author's voice via interview into a local voice profile. No external writes. |
