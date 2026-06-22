# board-deck — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

LOW-RISK. The plugin reads data sources (LivePlan / GA4 / Taskade / GitHub / Gmail) and generates the monthly board deck locally. Ingestion is read-only; deck production is generate. It presents the deck — it does not send or distribute it. Stat slides that carry factual claims should cite source + date (Test 3, optional).

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `board-deck-builder` | read-only ingestion + generate | Reads data sources (read-only), generates the deck locally; no send |
| `board-deck` | read-only ingestion + generate | Generates the monthly board deck from data sources; presents, does not send |
