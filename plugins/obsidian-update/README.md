# Obsidian Update Plugin v2.3.0

Vault-native personal operating system for MoxyWolf with bidirectional Council integration. The Obsidian vault is the brain. The Council plugin is the verification layer. Together they form a loop where organizational knowledge informs deliberations, and deliberation outcomes refine the vault.

## What Changed in v2.3.0

The vault now participates in the Council deliberation loop. Two new integration points:

| Integration | Direction | What happens |
|---|---|---|
| Vault context injection | Vault → Council | Council reads MEMORY.md, project knowledge, and past deliberation outcomes before every deliberation |
| Decision record writing | Council → Vault | Council writes structured decision records to the vault after each deliberation |
| Pattern memory sync | Council → Vault | Model performance, routing intelligence, and deliberation logs sync to vault every 5th deliberation |
| Extraction verification | Council ↔ Vault | obsidian-update optionally runs a fast Council evaluation on extraction plans before writing |

The memory-system skill is the sole vault writer. All Council writes go through its Sub-operations B and C to prevent conflicts and ensure frontmatter compliance.

## Components

| Component | Name | Purpose |
|-----------|------|---------|
| Skill | `personal-os` | Energy-aware daily ops: standup, triage, review, memory, tasks |
| Skill | `memory-system` | Sub-skill: memory read/write operations + Council integration gateway |
| Skill | `obsidian-update` | Session knowledge extraction to vault with optional Council verification gate |
| Command | `/personal-os` | Run standup, triage, review, extract, or recall |
| Command | `/memory-extract` | Nightly extraction (designed for scheduled tasks) |
| Command | `/obsidian-update` | End-of-session knowledge capture |

## Vault Requirements

The vault must contain at root:
- `CLAUDE.md` — vault conventions and project list
- `_Templates/` — note templates (Decision Record, Research Note, etc.)
- `Projects/` — project subfolders with numbered structure

The plugin will create on first run (if missing):
- `_System/` — MEMORY.md, IDENTITY.md, backups
- `_Shared Knowledge/Agents and Plugins/` — council-deliberation-log.md and related files
- `Daily Journal/` — daily standup notes with embedded Kanban
- `Tasks/` — KANBAN_VIEW.md and individual task files

## Usage

**Morning standup:** `/personal-os` or `/personal-os standup`

**Triage backlog:** `/personal-os triage`

**Weekly review:** `/personal-os review`

**Memory query:** `/personal-os recall [topic]`

**End-of-session capture:** `/obsidian-update`

**End-of-session capture (skip Council gate):** `/obsidian-update --no-council`

**Nightly extraction (scheduled):** `/memory-extract`

## Council Integration

When the Council plugin is also installed, these two plugins form a bidirectional loop:

1. **Before deliberation:** Council's Pre-Step A calls memory-system Sub-op A to read vault context (MEMORY.md, project knowledge, past deliberation outcomes)
2. **After deliberation:** Council's Step 8d calls memory-system Sub-op B to write a decision record to the vault
3. **Every 5th deliberation:** pattern-memory Operation 7 syncs model performance and routing intelligence to vault
4. **During extraction:** obsidian-update Step 2.5 can optionally run a fast Council evaluation (~$0.05) on the extraction plan before writing

All vault writes go through the memory-system skill, which enforces frontmatter compliance, prevents filename collisions, and manages cross-linking.

## License

MIT — MoxyWolf LLC
