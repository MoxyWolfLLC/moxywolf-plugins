# saas-pricing-engine — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests for the full standard. Every skill/command passes each test that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

This plugin produces pricing research, models, and copy locally. It does not publish prices.

| Skill / command | risk_tier | note |
|---|---|---|
| `competitor-scan` (command) | read-only | Scrapes and analyzes a competitor's pricing page (Apify / Claude in Chrome / WebFetch) and reports findings; no writes or publish. **Provenance (Test 3):** any scraped stat or price carried into a model or downstream artifact must keep its source URL + capture date, and unverifiable figures flagged rather than asserted as fact. |
| `price-check` (command) | generate | Quick-checks a price point against market data; produces an analysis artifact. Apply provenance to any cited market figure (Test 3). |
| `tier-builder` (command) | generate | Interactively designs a tier structure from scratch; produces a local pricing model. |
| `pricing-research` (skill) | generate | Pricing/market research synthesis (local artifact). Claim-bearing figures carry source + date (Test 3). |
| `pricing-modeler` (skill) | generate | Builds pricing models locally; no publish. |
| `pricing-copywriter` (skill) | generate | Generates pricing-page copy locally; a human reviews and publishes. |
