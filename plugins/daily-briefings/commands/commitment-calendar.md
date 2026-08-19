---
description: "Build the rolling N-day commitment calendar as a self-contained HTML file — calendar plus dated commitments from the inbox, with clash and unprepped-deadline flags. Usage: /commitment-calendar [days]"
argument-hint: "[days]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "SendUserFile", "mcp__Google_Calendar__list_calendars", "mcp__Google_Calendar__list_events", "mcp__Gmail__search_threads", "mcp__Gmail__get_thread", "mcp__remote-devices__get_device_info", "mcp__remote-devices__device_request_folder_access", "mcp__remote-devices__device_commit_files", "mcp__remote-devices__Control_Chrome__open_url", "mcp__remote-devices__Control_your_Mac__osascript"]
---

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/commitment-calendar/SKILL.md` and follow it end to end.

The argument, if present, is the window length in days and overrides `window.days` from the config for this run only. It does not change the config. If no argument is given, use the config.

If this is a scheduled or otherwise unattended run, do not ask clarifying questions — resolve from the config and put anything unresolved in the footer caveats.
