# Team Kanban Plugin

Keeps the team-visible task board on **Jira (project MOXY)** — the single canonical board. Sweeps non-chat sources for genuinely-new action items, files them to Jira, and maintains board hygiene.

## What It Does

Jira is the one board. Team members file their own tickets directly in Jira — including straight from Slack via the Jira Slack app (new tickets land in Backlog). This plugin adds the automation on top: it sweeps Dorian's non-chat operations sources for action items that would otherwise get lost, dedups them against the board, and files the new ones to MOXY with best-practice issue authoring.

## Sources

| Source | What's Pulled |
|--------|--------------|
| Google Drive Active Tasks | Daily-ops managed task list (P0/P1/P2/P3) |
| Google Calendar | Today's meetings that imply task commitments |
| Gmail | Urgent threads, unanswered action items, VIP contact emails, meeting-summary next-steps |
| Jira (MOXY) | The board itself — the source of truth for what's already tracked and done |

Candidates are deduped against the board (open issues + recently-Done issues) before anything is filed, so finished work isn't resurrected.

## Board Model

- **Jira (project MOXY) is the single source of truth.** There is no vault kanban and no Slack digest.
- Columns map to Jira statuses (discovered at sync time), with label fallbacks (`p0`, `p1`, `backlog`, `blocked`, `in-review`) where a status doesn't exist.
- New tickets default to **Backlog** — they are not auto-added to an active sprint.
- Sub-items become real Jira **Subtasks**; dependencies become **Blocks** issue links; completed work goes through **In Review** (reviewer pairings) before Done.

Columns: Backlog / P0 — Today (max 3) / P1 — This Week (max 7) / Blocked / In Progress / In Review / Done (cleared Mondays)

## Commands

| Command | Description |
|---------|-------------|
| `/team-kanban` | Full sync — sweep Drive + Calendar + Gmail, dedup, file/update issues on MOXY |
| `/team-kanban quick` | Quick refresh — board + Google Drive Active Tasks → Jira only |
| `/team-kanban-setup` | One-time setup — verify Jira, resolve accountIds, approval-gated first sync |

## Setup

1. Connect the Atlassian MCP (moxywolf.atlassian.net) and confirm project MOXY is visible
2. Run `/team-kanban-setup` — it resolves roster accountIds, checks board statuses (recommends adding Blocked / In Review columns), runs the approval-gated first sync, and stores the config note
3. Optionally set up a daily scheduled task for automated morning syncs

## Required Connections

- **Atlassian MCP** — for Jira issue creation, updates, and transitions (the board)
- **Google Calendar MCP** — for today's meeting scanning
- **Gmail MCP** — for inbox intelligence
- **Google Drive MCP** — for the Active Tasks document

## Team Input

Team members add tasks by creating a MOXY issue directly in Jira — from the Jira UI or straight from a Slack message via the Jira Slack app. New tickets land in Backlog by default; the creator can set title, description, project, and issue type before filing.

## Governance

This plugin conforms to the [MoxyWolf AI Governance Manifesto](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md). Bulk Jira creation (first sync, or >5 new issues at once) is confirm-before-write through a named approver. Jira issues are never deleted or closed autonomously. See [`GOVERNANCE.md`](GOVERNANCE.md).

## Changelog

### v0.6.0

Jira (project MOXY) becomes the single canonical board. The vault kanban (`KANBAN_VIEW.md`) and all Slack task flows are retired — no Obsidian source-of-truth, no dual-authority sync-back, no Slack scraping, no #general digest. Team members file tickets directly in Jira (including from Slack via the Jira Slack app). The skill now sweeps only Google Drive / Calendar / Gmail for new action items, dedups against the board (open + recently-Done), and files to MOXY with the same issue-authoring standard (Context/Acceptance/Notes, real Subtasks, Blocks links, Backlog default). Board hygiene (priorities, column limits, In Review reviewer pairings) preserved.

### v0.5.1

Subtask capture is end-to-end — every source parser emits a `subtasks` array that the Jira sync creates as real Subtasks under the parent issue. Sub-items are never flattened into description checklists.

### v0.5.0

Jira replaces the Slack Canvas as the team-visible board (org decision: Jira is the org-wide tracker, TECH-STACK v4.7). Columns map to discovered Jira statuses with label fallbacks. (Superseded by v0.6.0, which made Jira the *only* board.)
