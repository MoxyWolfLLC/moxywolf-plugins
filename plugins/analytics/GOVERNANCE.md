# analytics — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

LOW-RISK. The plugin runs read-only GA4 reports via the GA4 Data API (credentials from env). It reads and reports; it writes nothing, sends nothing, and moves no money. No gate required beyond declaring the tier.

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `google-analytics` | read-only | Read-only GA4 reporting via the Data API; no writes or sends |
| `google-analytics` | read-only | Runs a read-only GA4 report (generic or Lens-Test campaign) |
