# graphify

Standalone graphify knowledge-graph runner for Cowork. Point graphify at a thing — a directory of code, a Supabase database, any prepared corpus — and get a full LLM-named-community knowledge graph (god nodes, communities, import cycles, isolated nodes) without dragging a whole repo analysis along.

## Why this exists

graphify started life embedded as "Step 0" inside `github-repo-analyzer`. That coupled a general-purpose structural tool to one consumer. This plugin breaks it out on a corpus-adapter pattern: graphify doesn't analyze repos, it analyzes *file corpora* — so the runner protocol lives here once, and adapters build corpora from different targets.

- **`graphify-core` skill** — the canonical runner protocol (single source of truth): install, team OpenRouter key (DR-010), custom backend registration, the two-pass AST-then-label split that survives the Cowork sandbox's per-command time box, the docs-first keyed flow for markdown corpora, export surfaces (Obsidian / wiki / global registry), keyless fallback, graceful degradation. `github-repo-analyzer` delegates its Step 0 here.
- **`/graphify <path>`** — graph any directory. Builds a code-only scratch corpus, runs core, reports god nodes / named communities / cycles / isolated nodes. `--obsidian` lands an Obsidian-format export in the vault.
- **`/graphify-supabase [project-ref]`** — graph a Supabase database schema. Preferred path: native live introspection via `graphify extract --postgres "<DSN>"` when the user supplies a connection string. Fallback (no DSN): read-only schema pull via the Supabase MCP, emitted as a corpus — tables become classes, FKs become imports (= edges), views and functions fold in, RLS policies attach to their tables. Hub tables surface as god nodes; schema domains as named communities; orphan tables as isolated nodes. Supports a `py` (default) vs `sql` corpus format A/B.
- **`/graphify-vault [scope]`** — graph an Obsidian vault itself (default: the MoxyWolf Vault). Markdown is a docs-first corpus (keyed extraction, no keyless path). The Obsidian-format graph is written back into the vault — whole-vault graphs to `_Shared Knowledge/Vault Graph/`, project-scoped graphs to `Projects/<project>/06-Engineering/graphs/vault/` — so generated `[[wikilinks]]` render in Obsidian's graph view alongside real notes, in their own filterable subfolder.

## Obsidian routing convention

Per-project graphs (repo, database) → `MoxyWolf Vault/Projects/<project>/06-Engineering/graphs/<target>/`. Vault-wide graph → `MoxyWolf Vault/_Shared Knowledge/Vault Graph/`. Generated graph notes are derived artifacts — obsidian-update/memory extraction must not mine them as session knowledge.

## Requirements

- MoxyWolf Vault mounted (team OpenRouter key at `_Shared Knowledge/Agents and Plugins/openrouter.env`, per DR-010) for the keyed naming pass; keyless code-only graphs work without it.
- Supabase MCP connected for `/graphify-supabase`.
- `pip` available in the sandbox (the protocol installs `graphifyy` + `openai` idempotently).

## Outputs

`graphify-out/` with `graph.json`, `GRAPH_REPORT.md`, `graph.html`. Keep-worthy graphs go to the active project's `06 – Engineering/graphs/<target>/`.

## Versioning

- **0.2.1** — runtime lessons from the first /graphify-vault proof run (DR-007): mandatory docs-corpus extraction defaults (`--mode deep --token-budget 4000`, `GRAPHIFY_OPENROUTER_MODEL=openai/gpt-4o`), the semantic-cache trap (clear `graphify-out/` after settings changes), and the Obsidian export generated from `graph.json` as the primary path (headless CLI 0.8.37 has no `--obsidian`/`--wiki`).
- **0.2.0** — Obsidian integration: docs-first corpus flow, export surfaces in core (`--obsidian`/`--wiki`/global registry), `/graphify-vault`, `--obsidian` on `/graphify` and `/graphify-supabase`, vault routing convention; `/graphify-supabase` now prefers native `--postgres` DSN introspection with the MCP corpus emit as fallback.
- **0.1.0** — initial breakout from github-repo-analyzer 0.8.0: graphify-core skill (protocol lifted verbatim, generalized corpus-in/graph-out contract), `/graphify`, `/graphify-supabase`.
