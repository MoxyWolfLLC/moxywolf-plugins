---
description: "Nightly memory extraction — reviews today's work, extracts durable facts, updates all memory layers in the vault. Designed for scheduled task automation."
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite", "mcp__cowork__request_cowork_directory"]
---

# Nightly Memory Extraction

This command runs Mode 4 (Memory Extract) from the Personal OS, writing all updates to the vault.

**Note:** This typically runs as an automated scheduled task at 11 PM nightly. In the scheduled-task VM, the vault is NOT mounted locally — all reads/writes go through the Google Drive REST API via `scripts/drive_rest.py` (one-time service-account setup required; see `references/scheduled-task-vm-setup.md`).

1. **Resolve vault** — try workspace mount first, then Google Drive API fallback
2. **Pre-flight check** — Read today's daily note. If `## Extraction Status` shows `Extracted: yes`, exit immediately without modifying any files.
3. Read `${VAULT}/_System/IDENTITY.md`
4. Read `${VAULT}/_System/MEMORY.md`
5. Read `${CLAUDE_PLUGIN_ROOT}/skills/personal-os/SKILL.md`
6. Execute Mode 4: Memory Extract as described in the skill (includes Kanban Done cleanup)
7. Write all updates to vault: MEMORY.md, daily note, vault knowledge notes, cleaned KANBAN_VIEW.md
