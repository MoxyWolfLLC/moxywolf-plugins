# team-kanban — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md).

Every skill and command below declares a risk tier and is held to the five tests:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action (sending, posting publicly, writing to shared systems).
2. **A named human signs** — high-tier output requires one *named* human to approve, and the approval is recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

## Risk surface

team-kanban writes to a **public, team-visible Slack space**: it publishes a shared Canvas in #general and broadcasts a daily digest message to #general. A public/shared-channel broadcast is the highest-stakes action in this plugin and is treated as such — Dorian (named approver) sees the exact content and destination and approves before anything posts. Task sync (reading sources, merging, writing back to the Obsidian vault) is gated for new tasks and confirmed before any side-effectful write.

## Skill / command risk tiers

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `team-kanban` (skill) — #general digest broadcast | high-stakes | Public broadcast. Show the exact digest + destination (#general); named human (Dorian) approves before `slack_send_message`. Never auto-post. |
| `team-kanban` (skill) — first Canvas publish | high-stakes | Public/shared write. Show the exact Canvas content + destination; named human approves before `slack_create_canvas`. Never auto-create. |
| `team-kanban` (skill) — task sync (read sources, merge, Canvas refresh, sync-back to vault) | side-effectful-gated | Completion sync-back is confirmed; new-task sync-back is approval-gated before any write. No autonomous irreversible action. |
| `/team-kanban` (command) | side-effectful-gated | Dispatches the skill's modes; inherits the gates above — the #general broadcast + first Canvas publish stay high-stakes. |
| `/team-kanban-setup` (command) | high-stakes | One-time setup creates the first shared Canvas and the first #general intro post — both public. Show exact content + destination; named human approves before publishing/posting. |
