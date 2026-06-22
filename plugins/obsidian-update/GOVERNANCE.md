# obsidian-update — Governance

This plugin is held to the MoxyWolf plugin conformance standard. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
for the full standard. Every skill/command passes each of the five tests that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

Vault writes present the extraction plan for approval before writing. The external-send path
carries the named-approver rule: **external sends require a named human's approval before they
leave; record who approved.**

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `obsidian-update` (command) | side-effectful-gated | Captures session knowledge to the vault; presents the extraction plan for approval before writing (Tests 1, 5). |
| `personal-os` (command) | side-effectful-gated | Vault-native standup/triage/review/memory ops; task and memory writes confirm-gated; never auto-adds tasks without approval. |
| `memory-extract` (command) | side-effectful-gated | Nightly memory extraction to vault layers; internal writes only. External sends require a named human's approval, recorded (Test 2). |
| `obsidian-update` (skill) | side-effectful-gated | Vault write workflow; approve-before-write; optional Council pre-write evaluation. |
| `memory-system` (skill) | side-effectful-gated | Write path for memory layers (Trust Rung 3 — act within bounds). External sends are drafted and queued; a named human approves before they leave, recorded (Test 2). |
| `personal-os` (skill) | side-effectful-gated | Standup/triage/review engine; writes vault + kanban only after approval. |
