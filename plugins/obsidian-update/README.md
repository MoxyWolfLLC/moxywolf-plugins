# Obsidian Update Plugin v2.5.3

Vault-native personal operating system for MoxyWolf with bidirectional Council integration. The Obsidian vault is the brain. The Council plugin is the verification layer. Together they form a loop where organizational knowledge informs deliberations, and deliberation outcomes refine the vault.

## What Changed in v2.5.3

Tombstone check before re-adding kanban tasks. The `personal-os` standup and triage modes (Modes 1 and 2) now dedup any task derived from Slack, Gmail, calendar, or Drive against **both** the `## ✅ Done` column of `KANBAN_VIEW.md` and the done-archive (`team-kanban-done-archive.md`) before adding it. A recency gate suppresses a candidate that matches a completed or archived item unless its source signal is newer than the completion date — so a finished task whose Slack/email signal still exists no longer gets rewritten onto the board. Card column and `#priority/pN` tag are kept in agreement. Backed by the team rule `feedback_kanban_check_tombstones_before_readd.md`.

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

## Composio fallback

For apps with no native MCP connector, this plugin can reach them through Composio's Tool Router when the Composio connector is installed. See the `composio` plugin.

## Governance

This plugin conforms to the [MoxyWolf AI Governance Manifesto](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md). Every skill declares a risk tier, and high-stakes actions route through a named Release Owner who signs before anything irreversible ships. See [`GOVERNANCE.md`](GOVERNANCE.md) for the per-skill tier table.

External sends require a named approver before anything leaves the vault.

## Concept-ported from claude-mem

The memory search uses a 3-layer progressive-disclosure pattern (index → timeline → fetch) and an as-it-happens capture principle concept-ported from [claude-mem](https://github.com/thedotmack/claude-mem) (Apache-2.0, © Alex Newman). Only the ideas were adapted; claude-mem's Bun/SQLite/Chroma runtime and token were not vendored. See `NOTICE`.
