# graphify

Standalone graphify knowledge-graph runner for Cowork. Point graphify at a thing — a directory of code, a Supabase database, any prepared corpus — and get a full LLM-named-community knowledge graph (god nodes, communities, import cycles, isolated nodes) without dragging a whole repo analysis along.

## Why this exists

graphify started life embedded as "Step 0" inside `github-repo-analyzer`. That coupled a general-purpose structural tool to one consumer. This plugin breaks it out on a corpus-adapter pattern: graphify doesn't analyze repos, it analyzes *file corpora* — so the runner protocol lives here once, and adapters build corpora from different targets.

- **`graphify-core` skill** — the canonical runner protocol (single source of truth): install, team OpenRouter key (DR-010), custom backend registration, the two-pass AST-then-label split that survives the Cowork sandbox's per-command time box, keyless fallback, graceful degradation. `github-repo-analyzer` delegates its Step 0 here.
- **`/graphify <path>`** — graph any directory. Builds a code-only scratch corpus, runs core, reports god nodes / named communities / cycles / isolated nodes.
- **`/graphify-supabase [project-ref]`** — graph a Supabase database schema via the Supabase MCP (read-only). Tables become classes, FKs become imports (= edges), views and functions fold in, RLS policies attach to their tables. Hub tables surface as god nodes; schema domains as named communities; orphan tables as isolated nodes. Supports a `py` (default) vs `sql` corpus format A/B.

## Requirements

- MoxyWolf Vault mounted (team OpenRouter key at `_Shared Knowledge/Agents and Plugins/openrouter.env`, per DR-010) for the keyed naming pass; keyless code-only graphs work without it.
- Supabase MCP connected for `/graphify-supabase`.
- `pip` available in the sandbox (the protocol installs `graphifyy` + `openai` idempotently).

## Outputs

`graphify-out/` with `graph.json`, `GRAPH_REPORT.md`, `graph.html`. Keep-worthy graphs go to the active project's `06 – Engineering/graphs/<target>/`.

## Versioning

- **0.1.0** — initial breakout from github-repo-analyzer 0.8.0: graphify-core skill (protocol lifted verbatim, generalized corpus-in/graph-out contract), `/graphify`, `/graphify-supabase`.
