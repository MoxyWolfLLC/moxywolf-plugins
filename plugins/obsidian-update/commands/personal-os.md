---
description: "Personal OS: vault-native standup, triage, review, or memory operations. Usage: /personal-os [standup|triage|review|extract|recall <topic>]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite", "AskUserQuestion", "Agent", "mcp__c1fc4002-5f49-5f9d-a4e5-93c4ef5d6a75__google_drive_search", "mcp__c1fc4002-5f49-5f9d-a4e5-93c4ef5d6a75__google_drive_fetch", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_SEARCH_TOOLS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MANAGE_CONNECTIONS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MULTI_EXECUTE_TOOL", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_GET_TOOL_SCHEMAS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_WORKBENCH", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_BASH_TOOL", "mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__gcal_list_events", "mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__gcal_find_my_free_time", "mcp__50d37d97-704a-41ad-82c9-63bafa29236e__gmail_search_messages", "mcp__50d37d97-704a-41ad-82c9-63bafa29236e__gmail_read_message", "mcp__cowork__request_cowork_directory"]
---

# Personal OS — Vault-Native Operating System

## STEP 0: ALWAYS BOOTSTRAP MEMORY FIRST

Before doing ANYTHING else, resolve the vault and read memory files:

1. **Resolve vault path** — check in order:
   a. Current workspace folder contains `CLAUDE.md` → that IS the vault
   b. Google Drive mount path
   c. Google Drive API via RUBE_REMOTE_WORKBENCH
   d. Ask Dorian to mount via `request_cowork_directory`
2. Read `${VAULT}/_System/IDENTITY.md` — internalize identity
3. Read `${VAULT}/_System/MEMORY.md` — internalize tacit knowledge
4. Read the 3 most recent files in `${VAULT}/Daily Journal/` — internalize recent context
5. Do NOT recite memory back to Dorian. Just internalize it silently.
6. If `_System/` doesn't exist, run first-run initialization (see memory-system skill).

## STEP 1: DETERMINE MODE

Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/personal-os/SKILL.md` and follow its instructions.

Determine mode from the argument:
- No argument or "standup" → Mode 1: Morning Standup
- "triage" → Mode 2: Backlog Triage
- "review" → Mode 3: Weekly Review
- "extract" → Mode 4: Memory Extract (Nightly Extraction)
- "recall [topic]" → Mode 5: Memory Query

## STEP 2: EXECUTE MODE

Follow the mode instructions in the skill file. Use TodoWrite to track progress through each step.

## STEP 3: ALWAYS WRITE MEMORY

At the end of EVERY session (regardless of mode), update the daily note for today:
- Write/append to `${VAULT}/Daily Journal/YYYY-MM-DD.md`
- Include: key events, decisions made, facts extracted, open threads
- If this was a standup, extraction, or review: also update `${VAULT}/_System/MEMORY.md` if warranted

This step is NON-NEGOTIABLE. Memory persistence is the entire point of this system.
