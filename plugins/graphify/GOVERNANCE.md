# graphify — Governance

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
| `graphify-core` (skill) | generate | Canonical runner protocol: corpus directory in, knowledge-graph artifacts out. Builds the graph in a scratch directory; produces local artifacts only, does not ship them. |
| `graphify` (command) | generate | Builds a knowledge graph over any directory and writes graph artifacts locally. No external send/publish. |
| `graphify-supabase` (command) | generate | Reads a Supabase schema (tables, FKs, views, functions, RLS) and produces a local graph. Schema read + local artifact generation; no DB writes. |
| `graphify-vault` (command) | side-effectful-gated | Graphs an Obsidian vault and **writes the Obsidian-format graph back into the cloud-synced MoxyWolf Vault** (`--no-obsidian-export` disables the write). Because it writes into a shared, Drive-synced store, confirm scope and the bulk-download/cloud-only file list before writing (Tests 1, 5). Graph-build itself is `generate`; the vault write-back is the gated surface. |
