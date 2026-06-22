# council — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

LOW-RISK / advisory. The plugin runs multi-model AI deliberations for decision support — it advises, it does not take irreversible external action. Two things are worth flagging: deliberation **spends API credits** (a metered cost, not a side effect on customer systems), and it **writes deliberation memory** to the vault. The vault write is the only persistent side effect and is treated as side-effectful-gated.

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `deliberation-engine` | generate / advisory | Runs the deliberation; spends API $; advisory output, no external action |
| skill: `smart-router` | read-only | Routes the question to models/strategy; reads + decides routing |
| skill: `pattern-memory` | side-effectful-gated | Writes deliberation history/patterns to the vault (persistent store) |
| `deliberate` | generate / advisory | Multi-model deliberation on a question; spends API $; advisory |
| `council-stats` | read-only | Views learning metrics + deliberation history |
| `council-config` | side-effectful-gated | Views or modifies plugin settings (config write) |
| `council-optimize` | side-effectful-gated | Runs the optimization loop; spends API $ and writes back optimized prompts |
