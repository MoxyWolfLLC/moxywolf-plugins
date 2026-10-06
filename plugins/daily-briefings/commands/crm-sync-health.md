---
description: "Daily CRM sync pipeline check: stuck runs, budget-exceeded errors, dead-lettered and stale sources. Sweeps orphaned runs and releases a dead-lettered task once a day. One line when healthy. Usage: /crm-sync-health"
allowed-tools: ["Read", "Bash", "Glob", "Grep", "mcp__Supabase__execute_sql", "mcp__remote-devices__get_device_info", "mcp__remote-devices__device_request_folder_access"]
---

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/crm-sync-health/SKILL.md` and follow it end to end.

Two bounded writes only: sweep `running` rows older than 2 hours, and release a dead-lettered `sync_tasks` row at most once a day, never one that died of a budget overrun. No other write, no code or config change, no direct `sync-all` call. If the real fix is outside that, name it and stop.

Target and thresholds come from the `crmHealth` block in the briefings config. If that block is absent, say so and stop rather than guessing a project id.

If this is a scheduled or otherwise unattended run, don't ask clarifying questions. A healthy result is one line.
