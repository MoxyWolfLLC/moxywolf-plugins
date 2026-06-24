# Team Kanban Plugin

Aggregates tasks from multiple sources into a team-visible Slack Canvas kanban board with daily digest messages to #general.

## What It Does

This plugin bridges the gap between Dorian's personal operations stack and the team's visibility into current work. It pulls tasks from four sources, merges and deduplicates them, and publishes a persistent kanban board to Slack — plus a daily digest message that keeps the whole team aligned.

## Sources

| Source | What's Pulled | Priority |
|--------|--------------|----------|
| Obsidian KANBAN_VIEW.md | Full kanban state with tags, projects, and waiting-on context | Primary (source of truth) |
| Google Drive Active Tasks | Daily-ops managed task list (P0/P1/P2/P3) | Secondary (deduped against Obsidian) |
| Google Calendar | Today's meetings that imply task commitments | Supplementary |
| Gmail | Urgent threads, unanswered action items, VIP contact emails | Supplementary |
| Slack threads | Team-contributed tasks from #general digest replies | Team input |

## Kanban Columns

Backlog / P0 — Today (max 3) / P1 — This Week (max 7) / Blocked / In Progress / Done (cleared Mondays)

## Commands

| Command | Description |
|---------|-------------|
| `/team-kanban` | Full sync — aggregate all sources and post to Slack |
| `/team-kanban quick` | Quick refresh — Obsidian + Google Drive only, skip email/calendar |
| `/team-kanban-setup` | One-time setup — create the Canvas and configure |

## Setup

1. Run `/team-kanban-setup` to create the Slack Canvas and configure the channel
2. Ensure the Obsidian vault (MoxyWolf Vault) is mounted in the Cowork workspace
3. Optionally set up a daily scheduled task for automated morning syncs

## Required Connections

- **Slack MCP** — for Canvas creation/updates and #general messaging
- **Google Calendar MCP** — for today's meeting scanning
- **Gmail MCP** — for inbox intelligence
- **Google Drive MCP** — for Active Tasks document access
- **Obsidian Vault** — mounted via Cowork workspace directory

## Team Input

Team members can add tasks by replying to the daily digest thread in #general:

```
P1 Review RegGenome press release draft #reggenome
```

Format: `[P0/P1/Backlog] Task description #project-name`

These tasks are picked up on the next sync and optionally written back to the Obsidian kanban.

## Governance

This plugin conforms to the [MoxyWolf AI Governance Manifesto](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md). Every skill declares a risk tier, and high-stakes actions route through a named Release Owner who signs before anything irreversible ships. See [`GOVERNANCE.md`](GOVERNANCE.md) for the per-skill tier table.

The #general digest and the shared Canvas write are confirm-before-post, not auto-broadcast.

## Changelog

### v0.4.2

Tombstone check before re-adding tasks. The merge step (Step 6) now dedups candidate tasks from Drive, Calendar, Gmail, and Slack against **three** sets — the open board, the `## ✅ Done` column, and the done-archive (`team-kanban-done-archive.md`) — not just the open board. A recency gate suppresses any candidate that matches a completed or archived item unless its source signal is newer than the completion date. This stops finished tasks from being resurrected when their originating Slack/email signal is still present. The reconcile step also now keeps each card's column and its `#priority/pN` tag in agreement. Backed by the team rule `feedback_kanban_check_tombstones_before_readd.md`.
