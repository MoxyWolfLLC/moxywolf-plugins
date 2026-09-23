---
description: "Plan the day as ultradian sprint blocks on the measured curve, then verify each block against what the work produced. Usage: /sprint-day [plan|check|close] [blockId]"
argument-hint: "[plan|check|close] [blockId]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebFetch", "mcp__Google_Calendar__list_events", "mcp__Google_Drive__search_files", "mcp__Google_Drive__read_file_content", "mcp__Google_Drive__create_file", "mcp__Google_Drive__update_file", "mcp__Github__list_commits", "mcp__Github__get_commit", "mcp__Github__list_pull_requests", "mcp__Github__search_commits", "mcp__Gmail__search_threads", "mcp__Gmail__send_message", "mcp__claude-code-remote__create_trigger", "mcp__claude-code-remote__list_triggers", "mcp__claude-code-remote__delete_trigger", "mcp__remote-devices__get_device_info"]
---

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/sprint-day/SKILL.md` and follow it end to end. The curve, the ledger schema and the three block statuses are defined in `${CLAUDE_PLUGIN_ROOT}/skills/sprint-day/references/ultradian-ledger.md`.

Arguments:

- `plan` (the default when the mode is absent and no ledger exists for today) builds today's block plan, writes the ledger, and registers its own boundary check-ins.
- `check` resolves one block. It needs a block id, and it reads the block's window from the ledger rather than from the clock.
- `close` reports the day and appends the rollup row.

With no arguments and a ledger already written for today, show the day's state and change nothing.

A block is `verified` only from an artifact whose own timestamp falls inside the block window. The owner saying so produces `self-reported`. Nothing found and nobody answering produces `unknown`. Never report upward from what the evidence supports.

If this is a scheduled or otherwise unattended run, do not ask clarifying questions. Put anything unresolved in the day's caveats.
