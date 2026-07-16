---
description: Sync tasks to the team Jira board (MOXY)
argument-hint: [full|quick]
---

Run the team-kanban skill to sweep non-chat sources for action items and sync them to the single canonical board on Jira (project MOXY). There is no vault kanban and no Slack digest — Jira is the board.

If the argument is "quick" or "refresh", run Mode 2 (Quick Update) — skip calendar and email scanning; read the board + Google Drive Active Tasks, merge, and file to Jira.

If the argument is "full" or no argument is provided, run Mode 1 (Full Sync) — sweep Google Drive Active Tasks, Google Calendar, and Gmail for new action items, dedup against the board (open + recently-Done), and file/update issues on MOXY.

If the argument is "setup", run Mode 3 (Setup) — verify Jira access, resolve accountIds, run the first (approval-gated) sync, and store the config.

Steps:
1. Read the team-kanban skill at `${CLAUDE_PLUGIN_ROOT}/skills/team-kanban/SKILL.md`
2. Follow the appropriate mode based on the argument
3. Report results: issues created / updated / transitioned, and anything flagged for triage
