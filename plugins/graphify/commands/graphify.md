---
description: Build a graphify knowledge graph over any directory — no repo analysis attached
argument-hint: <path> [--keyless] [--with-docs] [--obsidian] [--out <dir>]
---

Build a graphify knowledge graph over the directory at $1.

## Steps

1. Parse `$ARGUMENTS`: the target path (required), `--keyless` (skip the keyed naming pass), `--with-docs` (run optional Pass C), `--obsidian` (also export an Obsidian vault of the graph into the MoxyWolf Vault), `--out <dir>` (where `graphify-out/` lands; default: alongside a scratch corpus, with the report surfaced in chat).

2. Read the runner protocol at `${CLAUDE_PLUGIN_ROOT}/skills/graphify-core/SKILL.md`.

3. **Build the corpus** (this command's job — core doesn't do it):
   - Create a scratch corpus directory.
   - Copy in code files per the skill's *Corpus rules* (code extensions only; exclude `node_modules`, `.next`, `dist`, `.git`; strip `.md`/`.mdx`/images).
   - If the target is already a clean code-only directory, it may be used in place.

4. **Run the protocol** from graphify-core: install check → key + OpenRouter backend (skip if `--keyless`) → Pass A (`extract --no-cluster`) → Pass B (`cluster-only` then `label --backend openrouter`; skip `label` if `--keyless`) → optional Pass C if `--with-docs`.

5. **Verify** real community names landed (unless `--keyless`), per the skill's confirmation step.

6. **Obsidian export** (if `--obsidian`): per graphify-core's *Export surfaces*, generate the Obsidian-format output (fall back to `--wiki` if the CLI rejects the flag) and copy it to `MoxyWolf Vault/Projects/<project>/06-Engineering/graphs/<target-name>/`, in its own subfolder.

7. **Report in chat:** top god nodes with edge counts, the largest named communities, any import cycles, and notable isolated nodes. Link the output directory (`graph.json`, `GRAPH_REPORT.md`, `graph.html`). If the user wants the artifacts kept, copy `graphify-out/` to the active project's `06 – Engineering/graphs/<target-name>/` folder.
