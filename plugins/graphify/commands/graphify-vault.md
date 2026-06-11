---
description: Graph an Obsidian vault (default — the MoxyWolf Vault) and write the graph back into the vault, Obsidian-format
argument-hint: "[vault-path | Projects/<project>] [--keyless-cluster] [--no-obsidian-export]"
---

Build a graphify knowledge graph of an Obsidian vault and land the Obsidian-format output back inside the vault, so the graph cross-links with the notes it was built from.

## Steps

1. Parse `$ARGUMENTS`: optional vault path or a `Projects/<project>` scope (default: the mounted MoxyWolf Vault root); `--no-obsidian-export` (graph artifacts only).

2. Read the runner protocol at `${CLAUDE_PLUGIN_ROOT}/skills/graphify-core/SKILL.md`, especially *Docs-first corpora* and *Export surfaces*.

3. **Build the corpus** in a scratch directory (never extract in place — the vault is cloud-synced Google Drive):
   - Copy `.md` files from the scope. Add a `.graphifyignore` excluding `_Templates/`, `99 – Archive/`, `.obsidian/`, and any generated graph output folders (`Vault Graph/`, `graphs/`) so the graph never ingests itself.
   - The vault is cloud-synced: if many files are cloud-only, tell the user what will be downloaded and why before copying in bulk.

4. **Run the docs-first protocol** with the mandatory docs-corpus defaults from graphify-core: `GRAPHIFY_OPENROUTER_MODEL=openai/gpt-4o graphify extract <corpus> --backend openrouter --mode deep --token-budget 4000 --no-cluster`. There is no keyless fallback for docs. Mind the cache trap: after changing mode/model/budget, `rm -rf <corpus>/graphify-out` before re-running. Then `cluster-only` + `label` per the core protocol.

5. **Export and place** (unless `--no-obsidian-export`): generate the Obsidian-format output from `graph.json` per graphify-core's *Export surfaces* (the headless CLI has no `--obsidian` flag) and copy it per the core routing convention:
   - Whole-vault corpus → `MoxyWolf Vault/_Shared Knowledge/Vault Graph/`
   - `Projects/<project>` scope → `MoxyWolf Vault/Projects/<project>/06-Engineering/graphs/vault/`

   Keep `graph.json` and `GRAPH_REPORT.md` alongside the export in the same folder.

6. **Report in chat:** god nodes (the vault's most-connected concepts), the largest named communities (knowledge domains), surprising cross-folder connections, and isolated notes (orphans worth linking or archiving). Suggest 3–4 questions the graph can now answer via `graphify query`.

## Notes

- Generated graph notes use `[[wikilinks]]` and will appear in Obsidian's graph view alongside real notes — that's the point, but they live in their own subfolder so they're filterable.
- Generated notes are derived artifacts: obsidian-update / memory extraction must not mine them as session knowledge.
- Re-runs are cheap-ish (semantic chunk cache) but not free — the keyed pass costs OpenRouter tokens proportional to changed notes. Use upstream `--update` semantics on re-runs where possible.
