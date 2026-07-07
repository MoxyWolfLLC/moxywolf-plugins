---
description: Set up the team kanban on the Jira board (MOXY)
---

Run the team-kanban skill in Mode 3 (Setup) to initialize the team kanban board on Jira.

> **Confirm before sending.** Show the exact content (issue list or message) and the destination, then wait for explicit human approval before writing or posting. The human can stop at any point. Never auto-send. For a public/shared-channel broadcast or a bulk tracker write, treat it as high-stakes: a named person approves first.

This is a one-time setup that:
1. Verifies Jira access and confirms project MOXY (cloudId, issue types)
2. Resolves the team roster's Jira accountIds and checks the board's statuses (recommends adding Blocked / In Review columns if missing)
3. Runs the first full sync — shows the complete list of MOXY issues to be created and waits for explicit approval before the bulk create
4. Posts an introductory message to #general explaining the Jira board — show the exact message and destination and wait for explicit approval before posting
5. Stores the config note (cloudId, project key, accountIds, channel ID, column mapping, last_standup_read) in the Obsidian vault
6. Offers to create a scheduled task for daily automated syncs

Read the team-kanban skill at `${CLAUDE_PLUGIN_ROOT}/skills/team-kanban/SKILL.md` and follow Mode 3 instructions.
