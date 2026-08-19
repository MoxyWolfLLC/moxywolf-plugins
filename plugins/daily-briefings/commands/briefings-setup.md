---
description: "Set up or update the briefings config in the vault and register the recurring commitment-calendar and morning-brief scheduled tasks. Idempotent. Usage: /briefings-setup"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "AskUserQuestion", "mcp__Google_Calendar__list_calendars", "mcp__remote-devices__get_device_info", "mcp__remote-devices__device_request_folder_access", "mcp__claude-code-remote__list_triggers", "mcp__claude-code-remote__create_trigger", "mcp__claude-code-remote__update_trigger", "mcp__Supabase__execute_sql", "mcp__Atlassian_Rovo__getAccessibleAtlassianResources", "mcp__Atlassian_Rovo__getVisibleJiraProjects"]
---

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/briefings-setup/SKILL.md` and follow it end to end.

Two hard rules from that skill, repeated here because they are the ones worth not getting wrong:

- Read the existing config and `list_triggers` **before** asking anything. This command is meant to be run more than once, and re-asking questions it could have read is how a setup command stops being run.
- Scheduled tasks go through `mcp__claude-code-remote__create_trigger` / `update_trigger`. Never `CronCreate` — that scheduler lives inside the session and dies with it, so the task would silently never fire.

Nothing is written or registered until the owner has seen the exact content and said yes.
