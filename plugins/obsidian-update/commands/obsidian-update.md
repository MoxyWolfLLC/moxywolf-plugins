---
description: Capture session knowledge to the Obsidian vault
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite", "mcp__cowork__request_cowork_directory"]
---

Read the obsidian-update skill at `${CLAUDE_PLUGIN_ROOT}/skills/obsidian-update/SKILL.md` and follow its complete workflow:

1. Locate the MoxyWolf Vault (workspace mount → Google Drive mount → `scripts/drive_rest.py` REST API for scheduled-task VMs → ask to mount)
2. Load context: read vault's CLAUDE.md, _System/MEMORY.md, and project indices
3. Scan the current conversation for extractable knowledge
4. Present the extraction plan for approval
5. Write approved notes to the vault (with proper frontmatter, cross-links, tags)
6. Update MEMORY.md if session produced significant new context
7. Report what was written

If the user provided arguments, treat them as guidance for what to focus on (e.g., `/obsidian-update just the SAMS decision` means only extract that specific item).
