---
description: Sync tasks to the team Jira board (MOXY)
argument-hint: [full|quick]
---

Run the team-kanban skill to aggregate tasks from all sources, sync the board to Jira (project MOXY), and post the slim #general digest.

If the argument is "quick" or "refresh", run Mode 2 (Quick Update) — skip calendar and email scanning, just sync Obsidian + Google Drive to Jira. No digest.

If the argument is "full" or no argument is provided, run Mode 1 (Full Sync) — aggregate from all sources including calendar and email intelligence.

If the argument is "setup", run Mode 3 (Setup) — verify Jira access, resolve accountIds, run the first sync, and configure the board.

Steps:
1. Read the team-kanban skill at `${CLAUDE_PLUGIN_ROOT}/skills/team-kanban/SKILL.md`
2. Follow the appropriate mode based on the argument
3. Report results: items synced, issues created/updated/transitioned, digest posted
