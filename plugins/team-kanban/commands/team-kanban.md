---
description: Sync tasks to the team Slack kanban board
argument-hint: [full|quick]
---

Run the team-kanban skill to aggregate tasks from all sources and post to the Slack Canvas and #general digest.

If the argument is "quick" or "refresh", run Mode 2 (Quick Update) — skip calendar and email scanning, just sync Obsidian + Google Drive to Slack.

If the argument is "full" or no argument is provided, run Mode 1 (Full Sync) — aggregate from all sources including calendar and email intelligence.

If the argument is "setup", run Mode 3 (Setup) — create the Canvas and configure the board for the first time.

Steps:
1. Read the team-kanban skill at `${CLAUDE_PLUGIN_ROOT}/skills/team-kanban/SKILL.md`
2. Follow the appropriate mode based on the argument
3. Report results: items synced, Canvas updated, digest posted
