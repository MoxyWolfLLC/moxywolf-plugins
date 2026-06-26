# excalidraw-vault

> Generate Excalidraw diagrams directly into the MoxyWolf Vault.

**Version:** 0.1.0
**Marketplace:** [moxywolf-plugins](https://github.com/MoxyWolfLLC/moxywolf-plugins) v1.16.0

## What it does

Writes Excalidraw diagrams into the MoxyWolf Vault in the [zsviczian Obsidian-Excalidraw plugin's](https://github.com/zsviczian/obsidian-excalidraw-plugin) native `.excalidraw.md` format, so diagrams:

- Render natively when opened in Obsidian.
- Embed inline in any note via `![[<name>.excalidraw]]`.
- Version normally in the git-backed vault.
- Live next to the notes that reference them (no separate canvas server, no excalidraw.com round-trip).

This parallels [`vault-code-learn`](../vault-code-learn) (code axis → vault) and [`graphify-vault`](../graphify) (knowledge axis → vault) on the **diagram axis**.

## Commands

| Command | What it does |
|---|---|
| `/excalidraw <description> [--scope ...] [--name ...] [--type ...]` | Generate a diagram from a natural-language description and save it to a chosen vault location. |
| `/excalidraw-here [--name ...] [--type ...]` | Generate a diagram **of the current document** and save it next to that note, then embed it via wikilink. |

### Examples

```
/excalidraw the uber-brain architecture: vault, obsidian-update, vault-code-learn, graphify-vault, excalidraw-vault, all feeding the brain --scope Projects/uber-brain --type architecture

/excalidraw DR routing flow from author to MoxyWolf Vault to project memory --shared --name dr-routing-flow --type flow

/excalidraw-here --name spec-data-flow --type flow
```

## Output format

Every diagram is written as a `.excalidraw.md` file with this structure:

```
---
excalidraw-plugin: parsed
tags: [excalidraw]
---

==⚠ Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== ...

# Excalidraw Data

## Text Elements

%%
## Drawing
```json
{ "type": "excalidraw", "version": 2, "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin", ... }
```
%%
```

See [`skills/excalidraw-vault-core/SKILL.md`](skills/excalidraw-vault-core/SKILL.md) for the full runner protocol — wrapping format, element schema, depth assessment, routing, and embedding patterns.

## Routing

| Scope | Destination |
|---|---|
| `--shared` or default | `_Shared Knowledge/Diagrams/<name>.excalidraw.md` |
| `--scope Projects/<project>` | `Projects/<project>/06-Engineering/diagrams/<name>.excalidraw.md` |
| `/excalidraw-here` | Sibling to the source note (or its `diagrams/` subfolder) |

Vault root resolves from `$MW_VAULT_PATH` if set, otherwise the canonical Google Drive mount.

## Requirements

- Obsidian with the [Excalidraw plugin by zsviczian](https://github.com/zsviczian/obsidian-excalidraw-plugin) installed (5M+ installs, the canonical one).
- MoxyWolf Vault mounted at the canonical path (Google Drive shared drive).
- Desktop Commander available to write into the cloud-synced vault (the sandbox is not the right environment for writes here).

## Skill

[`excalidraw-vault-core`](skills/excalidraw-vault-core) — single source of truth for the file format, element schema, and routing. Future plugins that need to emit diagrams (board-deck, saas-frontend-designer, github-repo-analyzer) should delegate here.

## Why not the headless Excalidraw MCP?

The official Excalidraw MCP (`mcp.excalidraw.com`) and community Docker MCPs (e.g. `yctimlin/mcp_excalidraw-canvas`) generate diagrams in their own canvas — they **do not** write to the Obsidian Excalidraw plugin's vault format. For MoxyWolf's "everything in the vault" pattern, those diagrams would live outside the knowledge graph. This plugin closes that gap.

## License

Internal — MoxyWolf LLC.
