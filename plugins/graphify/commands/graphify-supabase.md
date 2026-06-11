---
description: Graph a Supabase database schema — tables, FKs, views, functions, RLS — as a graphify knowledge graph
argument-hint: "[project-ref] [--dsn <postgres-url>] [--schema <name>]... [--format py|sql] [--keyless] [--obsidian] [--out <dir>]"
---

Build a graphify knowledge graph of a Supabase database's schema. Hub tables surface as god nodes, schema domains as named communities, orphan tables as isolated nodes.

## Steps

1. Parse `$ARGUMENTS`: optional project ref (if absent, call the Supabase MCP `list_projects` and ask the user to pick when more than one), `--dsn` (a Postgres connection string — see step 2a), `--schema` (repeatable; default `public`), `--format py|sql` (default `py`; see step 3), `--keyless`, `--obsidian`, `--out <dir>`.

2a. **Preferred path — native live introspection (when a DSN is available).** Upstream graphify introspects PostgreSQL directly: `uv tool install "graphifyy[postgres]"` (or pip equivalent), then `graphify extract --postgres "<DSN>"`. If the user provides `--dsn` (e.g. the Supabase session-pooler connection string), use this path and **skip steps 2–3 entirely** — no corpus emit needed. Never print, log, or persist the DSN or its password; pass it via an environment variable in the same shell call. The user supplies the DSN themselves (it carries the database password; the Supabase MCP does not expose it, and Claude must not ask the user to paste credentials into chat if they'd rather export it into the shell host-side). Then continue at step 4 (cluster + label per graphify-core).

2b. **Fallback path — MCP corpus emit (no DSN).** Pull the schema via the Supabase MCP (read-only — never mutate):
   - `list_tables` for the selected schemas.
   - `execute_sql` against `information_schema` / catalogs for what `list_tables` doesn't carry: column types and nullability, foreign keys (`table_constraints` + `key_column_usage` + `constraint_column_usage`), views and their definitions (`pg_views`), functions (`pg_proc` filtered to the schemas), and RLS policies (`pg_policies`).

3. **Emit the corpus** (one scratch directory, package-per-schema):
   - **`py` format (default).** Graphify's AST pass reads Python natively, so relations become real graph edges:
     - One module per table: `corpus/<schema>/<table>.py` containing a class per table with one typed attribute per column.
     - Foreign key → `from <schema>.<ref_table> import <RefTable>` plus a typed attribute — this is what turns FKs into edges.
     - View → a class in `corpus/<schema>/views/<view>.py` importing every table it selects from.
     - Function → a `def` stub in `corpus/<schema>/functions.py` whose body references the table classes it touches.
     - RLS policy → a method stub on the owning table's class (name = policy name).
   - **`sql` format.** Dump straight DDL (`.sql` files, one per table/view/function). Simpler and faithful, but FK edges depend on graphify's SQL parsing rather than explicit imports — communities are usually weaker. Offered for A/B comparison; if the two formats disagree materially on community structure for a given database, note it and prefer whichever matches the team's mental model of the schema domains.

4. Read `${CLAUDE_PLUGIN_ROOT}/skills/graphify-core/SKILL.md` and **run the protocol** over the corpus (keyed by default; `--keyless` skips naming).

5. **Obsidian export** (if `--obsidian`): per graphify-core's *Export surfaces*, generate the Obsidian-format output and copy it to `MoxyWolf Vault/Projects/<project>/06-Engineering/graphs/supabase-<project-ref>/`, in its own subfolder.

6. **Report in chat:** hub tables (god nodes) with edge counts, named schema domains (largest communities), circular FK chains (cycles), and orphan/weakly-connected tables. Link `GRAPH_REPORT.md` and `graph.html`. Offer to save `graphify-out/` to the active project's `06 – Engineering/graphs/supabase-<project-ref>/`.

## Notes

- Never run DDL/DML against the database — every query in step 2 is a read.
- Multi-schema databases: pass `--schema` more than once; cross-schema FKs become cross-package imports and will show up as bridges between communities.
- Big databases (500+ tables) hit the same sandbox time-box as big repos — the two-pass split in graphify-core handles it; don't attempt a single keyed `extract`.
