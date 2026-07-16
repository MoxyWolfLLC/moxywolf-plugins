# team-kanban — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md).

Every skill and command below declares a risk tier and is held to the five tests:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action (sending, posting publicly, writing to shared systems).
2. **A named human signs** — high-tier output requires one *named* human to approve, and the approval is recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

## Risk surface

team-kanban writes to one **team-visible space**: the shared Jira board (project MOXY). Any bulk write to the shared tracker (first sync, or >5 new issues at once) is the highest-stakes action in this plugin — Dorian (named approver) sees the exact issue list and destination and approves before anything bulk-creates. Incremental issue updates mirror an already-approved board state. Jira issues are never deleted or closed autonomously. (As of v0.6.0 the plugin no longer touches Slack or a vault kanban — there is no digest broadcast and no Obsidian sync-back.)

## Skill / command risk tiers

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `team-kanban` (skill) — bulk Jira issue creation (first sync, or >5 new issues) | high-stakes | Shared-tracker bulk write. Show the exact issue list + destination (MOXY); named human (Dorian) approves before `createJiraIssue` runs. Never auto-create in bulk. |
| `team-kanban` (skill) — incremental sync (sweep sources, merge, dedup, file/update issues) | side-effectful-gated | Incremental issue edits/transitions mirror the approved board; new issues below the bulk threshold are filed to Backlog. Never deletes/closes issues autonomously. |
| `/team-kanban` (command) | side-effectful-gated | Dispatches the skill's modes; inherits the bulk-create gate above. |
| `/team-kanban-setup` (command) | high-stakes | One-time setup bulk-creates the board's issues in MOXY — team-visible. Show exact issue list + destination; named human approves before creating. |
