# composio — Governance

This plugin is held to the MoxyWolf plugin conformance standard. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
for the full standard. Every skill/command passes each of the five tests that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

**Downstream inheritance:** Composio is an additive reach layer, never a gateway the other
plugins route through. Any side-effectful action taken through a Composio toolkit is governed by
the same risk tiers and Release-Owner gate as native skills; do not let an external toolkit bypass
the gate. A third-party toolkit reached via Composio inherits this fleet's gate rules and is tiered
by the action it performs (e.g. a Stripe charge or HubSpot send is `high-stakes`, a Notion read is
`read-only`).

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `composio-setup` (command) | read-only | Sets up the Composio MCP connector (retire Rube, create Tool Router URL, add custom connector); connector configuration, no third-party account writes. |
| `composio-tools` (skill) | read-only (setup) / inherits downstream | Explains the discover/authenticate/execute loop and when to use Composio vs. native MCP. Any write executed through a discovered toolkit inherits this fleet's gate rules and is tiered by its action; confirm intent before any write (Tests 1, 5). |
