---
description: "Run Daily Ops: morning standup, backlog triage, weekly review, or fitness coach. Usage: /daily-ops [standup|triage|review|fitness]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "TodoWrite", "AskUserQuestion", "mcp__c1fc4002-5f49-5f9d-a4e5-93c4ef5d6a75__google_drive_search", "mcp__c1fc4002-5f49-5f9d-a4e5-93c4ef5d6a75__google_drive_fetch", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_SEARCH_TOOLS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MANAGE_CONNECTIONS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MULTI_EXECUTE_TOOL", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_GET_TOOL_SCHEMAS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_WORKBENCH", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_BASH_TOOL", "mcp__50d37d97-704a-41ad-82c9-63bafa29236e__gmail_search_messages", "mcp__50d37d97-704a-41ad-82c9-63bafa29236e__gmail_read_message", "mcp__50d37d97-704a-41ad-82c9-63bafa29236e__gmail_read_thread", "mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__gcal_list_events", "mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__gcal_find_my_free_time", "mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__create_event", "mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__list_events", "mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__update_event", "mcp__Read_and_Send_iMessages__send_imessage", "mcp__Read_and_Send_iMessages__search_contacts"]
---

Read the skill at ${CLAUDE_PLUGIN_ROOT}/skills/daily-ops/SKILL.md and follow its instructions.

Determine the mode from the argument provided:
- No argument or "standup" → Mode 1: Morning Standup
- "triage" → Mode 2: Backlog Triage
- "review" → Mode 3: Weekly Review
- "fitness" or "workout" → Mode 4: Fitness Coach (reads Apple Health, prescribes today's workout, adds it to Google Calendar, iMessages a short summary)

If the argument is ambiguous or missing, default to Morning Standup and offer to switch modes at the end.

For Mode 4, before doing anything else:
1. Read the Fitness Coach profile at `<MoxyWolf Vault>/_Shared Knowledge/Fitness Coach/profile.md`.
2. If the profile is empty or marked `setup_complete: false`, run Step 1: Learn the User from the skill — ask the 10 intake questions and write the answers back to `profile.md`.
3. Otherwise proceed to Step 2: Read Today's Health Data.

Use TodoWrite to track progress through each step.
