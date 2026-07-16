---
description: Set up the team kanban on the Jira board (MOXY)
---

Run the team-kanban skill in Mode 3 (Setup) to initialize the single canonical task board on Jira (project MOXY).

> **Confirm before writing.** The first sync bulk-creates issues in the shared tracker. Show the exact issue list and destination (MOXY) and wait for explicit approval before the bulk create. Never auto-create in bulk. A named person (Dorian) approves.

This is a one-time setup that:
1. Verifies Jira access and confirms project MOXY (cloudId, issue types)
2. Resolves the team roster's Jira accountIds and checks the board's statuses (recommends adding Blocked / In Review columns if missing)
3. Runs the first full sync — shows the complete list of MOXY issues to be created and waits for explicit approval before the bulk create
4. Stores the config note (cloudId, project key, accountIds, discovered statuses, column mapping, last_standup_read) in the vault
5. Offers to create a scheduled task for daily automated syncs

Read the team-kanban skill at `${CLAUDE_PLUGIN_ROOT}/skills/team-kanban/SKILL.md` and follow Mode 3 instructions.
