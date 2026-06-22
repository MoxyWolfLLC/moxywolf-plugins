# frontier-founder — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests for the full standard. Every skill/command passes each test that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

| Skill / command | risk_tier | note |
|---|---|---|
| `blog-post` (command) | generate | Converts a draft markdown file into a publication-ready Frontier Founder blog post (formatted, JSON-LD, brand-aligned hero image) and **saves both files into the FrontierFounder repo — a local file write, no `git` commit/push**. Output does not auto-ship; a human commits and deploys separately. **Flag:** if this command ever gains a publish/push step (commit, push, deploy, or LinkedIn/Company-Page broadcast), that step is `side-effectful-gated`/`high-stakes` and must route through 4d-blog-engine's nonce-bound Release Owner Gate rather than acting autonomously. |
