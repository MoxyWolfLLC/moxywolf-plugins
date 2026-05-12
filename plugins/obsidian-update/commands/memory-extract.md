---
description: "Nightly memory extraction — reviews today's work, extracts durable facts, updates all memory layers in the vault. Designed for scheduled task automation."
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite", "mcp__c1fc4002-5f49-5f9d-a4e5-93c4ef5d6a75__google_drive_search", "mcp__c1fc4002-5f49-5f9d-a4e5-93c4ef5d6a75__google_drive_fetch", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_SEARCH_TOOLS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MANAGE_CONNECTIONS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MULTI_EXECUTE_TOOL", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_GET_TOOL_SCHEMAS", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_WORKBENCH", "mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_BASH_TOOL", "mcp__cowork__request_cowork_directory"]
---

# Nightly Memory Extraction

This command runs Mode 4 (Memory Extract) from the Personal OS, writing all updates to the vault.

**Note:** This typically runs as an automated scheduled task at 11 PM nightly. In the scheduled task VM, the vault is NOT mounted locally — all reads/writes go through Google Drive API via RUBE_REMOTE_WORKBENCH.

1. **Resolve vault** — try workspace mount first, then Google Drive API fallback
2. **Pre-flight check** — Read today's daily note. If `## Extraction Status` shows `Extracted: yes`, exit immediately without modifying any files.
3. Read `${VAULT}/_System/IDENTITY.md`
4. Read `${VAULT}/_System/MEMORY.md`
5. Read `${CLAUDE_PLUGIN_ROOT}/skills/personal-os/SKILL.md`
6. Execute Mode 4: Memory Extract as described in the skill (includes Kanban Done cleanup)
7. Write all updates to vault: MEMORY.md, daily note, vault knowledge notes, cleaned KANBAN_VIEW.md
