# team-kanban — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md).

Every skill and command below declares a risk tier and is held to the five tests:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action (sending, posting publicly, writing to shared systems).
2. **A named human signs** — high-tier output requires one *named* human to approve, and the approval is recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

## Risk surface

team-kanban writes to two **team-visible spaces**: the shared Jira board (project MOXY) and the #general Slack digest. The public #general broadcast and any bulk write to the shared tracker (first sync, >5 new issues at once) are the highest-stakes actions in this plugin and are treated as such — Dorian (named approver) sees the exact content and destination and approves before anything posts or bulk-creates. Incremental issue updates mirror an already-approved board state; task sync (reading sources, merging, writing back to the Obsidian vault) is gated for new tasks and confirmed before any side-effectful write. Jira issues are never deleted or closed autonomously.

## Skill / command risk tiers

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `team-kanban` (skill) — #general digest broadcast | high-stakes | Public broadcast. Show the exact digest + destination (#general); named human (Dorian) approves before `slack_send_message`. Never auto-post. |
| `team-kanban` (skill) — bulk Jira issue creation (first sync, or >5 new issues) | high-stakes | Shared-tracker bulk write. Show the exact issue list + destination (MOXY); named human approves before `createJiraIssue` runs. Never auto-create in bulk. |
| `team-kanban` (skill) — task sync (read sources, merge, incremental Jira update, sync-back to vault) | side-effectful-gated | Incremental issue edits/transitions mirror the approved board; completion sync-back is confirmed; new-task sync-back is approval-gated before any write. Never deletes/closes issues autonomously. |
| `/team-kanban` (command) | side-effectful-gated | Dispatches the skill's modes; inherits the gates above — the #general broadcast + bulk Jira creation stay high-stakes. |
| `/team-kanban-setup` (command) | high-stakes | One-time setup bulk-creates the board's issues in MOXY and posts the first #general intro — both team-visible. Show exact content + destination; named human approves before creating/posting. |
