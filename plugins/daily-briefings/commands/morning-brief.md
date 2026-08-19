---
description: "Render today's briefing as a self-contained HTML page — today and tomorrow, what arrived overnight, what still needs an answer, close deadlines, today's flags. Usage: /morning-brief"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "SendUserFile", "mcp__Google_Calendar__list_calendars", "mcp__Google_Calendar__list_events", "mcp__Gmail__search_threads", "mcp__Gmail__get_thread", "mcp__Slack__slack_read_channel", "mcp__Slack__slack_read_thread", "mcp__Slack__slack_search_public_and_private", "mcp__remote-devices__get_device_info", "mcp__remote-devices__device_request_folder_access", "mcp__remote-devices__device_commit_files", "mcp__remote-devices__Control_Chrome__open_url", "mcp__remote-devices__Control_your_Mac__osascript"]
---

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/morning-brief/SKILL.md` and follow it end to end.

If a Slack connector is not available, that is a source in the `unavailable` state — name it in the footer as chat not checked. It is not a reason to skip the run, and it is never rendered as silence.

If this is a scheduled or otherwise unattended run, do not ask clarifying questions and do not offer connector suggestions.
