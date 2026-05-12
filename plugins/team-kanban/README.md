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
