# Team Kanban Plugin

Aggregates tasks from multiple sources into the team-visible Jira board (project MOXY) with a slim daily digest to #general.

## What It Does

This plugin bridges the gap between Dorian's personal operations stack and the team's visibility into current work. It pulls tasks from five sources, merges and deduplicates them, and publishes the board to Jira — plus a slim daily digest message that points the team at the board.

## Sources

| Source | What's Pulled | Priority |
|--------|--------------|----------|
| Obsidian KANBAN_VIEW.md | Full kanban state with tags, projects, and waiting-on context | Primary (source of truth) |
| Google Drive Active Tasks | Daily-ops managed task list (P0/P1/P2/P3) | Secondary (deduped against Obsidian) |
| Google Calendar | Today's meetings that imply task commitments | Supplementary |
| Gmail | Urgent threads, unanswered action items, VIP contact emails | Supplementary |
| Slack DMs/threads/channels | Team commitments and assignments buried in chat | Supplementary |
| Jira (MOXY) + digest replies | Team-contributed tasks | Team input |

## Board Model

- **Obsidian is the source of truth; Jira is the published, team-editable mirror.**
- One card ↔ one MOXY issue, linked by a `#jira/MOXY-NNN` tag on the card.
- Dual-authority completion: done in either Obsidian or Jira wins, and the other side syncs to match.
- Columns map to Jira statuses (discovered at sync time), with label fallbacks (`p0`, `p1`, `backlog`, `blocked`, `in-review`) where a status doesn't exist.

Kanban columns: Backlog / P0 — Today (max 3) / P1 — This Week (max 7) / Blocked / In Progress / In Review / Done (cleared Mondays)

## Commands

| Command | Description |
|---------|-------------|
| `/team-kanban` | Full sync — aggregate all sources, sync to Jira, post digest |
| `/team-kanban quick` | Quick refresh — Obsidian + Google Drive → Jira only, no digest |
| `/team-kanban-setup` | One-time setup — verify Jira, resolve accountIds, first sync |

## Setup

1. Connect the Atlassian MCP (moxywolf.atlassian.net) and confirm project MOXY is visible
2. Run `/team-kanban-setup` — it resolves roster accountIds, checks board statuses, runs the approval-gated first sync, and stores the config note
3. Ensure the Obsidian vault (MoxyWolf Vault) is mounted in the Cowork workspace
4. Optionally set up a daily scheduled task for automated morning syncs

## Required Connections

- **Atlassian MCP** — for Jira issue creation, updates, and transitions
- **Slack MCP** — for the #general digest and chat-source scanning
- **Google Calendar MCP** — for today's meeting scanning
- **Gmail MCP** — for inbox intelligence
- **Google Drive MCP** — for Active Tasks document access
- **Obsidian Vault** — mounted via Cowork workspace directory

## Team Input

Team members add tasks either **directly in Jira** (create a MOXY issue — the sync picks it up and offers it for the Obsidian board) or by replying to the daily digest thread in #general:

```
P1 Review RegGenome press release draft #reggenome
```

Format: `[P0/P1/Backlog] Task description #project-name`

## Governance

This plugin conforms to the [MoxyWolf AI Governance Manifesto](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md). Every skill declares a risk tier, and high-stakes actions route through a named approver who signs before anything team-visible ships. See [`GOVERNANCE.md`](GOVERNANCE.md) for the per-skill tier table.

The #general digest and any bulk Jira creation are confirm-before-post, not auto-broadcast. Jira issues are never deleted or closed autonomously.

## Changelog

### v0.5.1

Subtask capture is end-to-end. Every source parser — Obsidian indented sub-checkboxes, multi-step email action items, multi-step Slack commitments — emits a `subtasks` array on the task object, and the Jira sync creates each entry as a real Subtask under the parent issue with its own assignee and status. Sub-items are never flattened into description checklists.

### v0.5.0

Jira replaces the Slack Canvas as the team-visible board (org decision: Jira is the org-wide tracker, TECH-STACK v4.7). Cards link to MOXY issues via `#jira/MOXY-NNN` tags; dual-authority completion now runs Obsidian ↔ Jira; columns map to discovered Jira statuses with label fallbacks; the #general digest becomes a slim pointer (stats + P0s + escalations + board link). The `last_standup_read` marker moves from the Canvas header into the vault config note. Slack remains a read source for chat-buried action items and the digest channel. The Canvas format reference is replaced by `references/jira-board-mapping.md`.

### v0.4.2

Tombstone check before re-adding tasks. The merge step (Step 6) dedups candidate tasks from Drive, Calendar, Gmail, and Slack against **three** sets — the open board, the `## ✅ Done` column, and the done-archive (`team-kanban-done-archive.md`) — not just the open board. A recency gate suppresses any candidate that matches a completed or archived item unless its source signal is newer than the completion date. Backed by the team rule `feedback_kanban_check_tombstones_before_readd.md`.
