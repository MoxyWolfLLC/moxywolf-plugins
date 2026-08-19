---
description: "Read-only health check on the CRM sync pipeline — stuck runs, budget-exceeded errors, stale sources. One line when healthy. Usage: /crm-sync-health"
allowed-tools: ["Read", "Bash", "Glob", "Grep", "mcp__Supabase__execute_sql", "mcp__remote-devices__get_device_info", "mcp__remote-devices__device_request_folder_access"]
---

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/crm-sync-health/SKILL.md` and follow it end to end.

Read-only. Do not fix anything, do not re-run `sync-all`, do not change secrets or data. If the fix is obvious, name it and stop.

Target and thresholds come from the `crmHealth` block in the briefings config. If that block is absent, say so and stop rather than guessing a project id.

If this is a scheduled or otherwise unattended run, do not ask clarifying questions. A healthy result is one line.
