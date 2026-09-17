# project-init — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
and its five tests for the full standard. Every skill/command passes each test that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

| Skill / command | risk_tier | note |
|---|---|---|
| `init-project` (command) | side-effectful-gated | Mounts the standard MoxyWolf roots, gathers active Taskade/GitHub subfolders, and **writes tailored Project Instructions plus `project-surfaces.json` into the project hub**. Confirm the Taskade workspace, Vault memory path, repository access, aliases, and task scope before writing (Tests 1, 5). |
| `project-init` (skill) | side-effectful-gated | Underlying setup protocol for `init-project`: writes Project Instructions, scaffolding, and the machine-readable `project-surfaces.json` mapping into the project hub. Same gated write surface. |
| `session-start` (command) | read-only | Mounts standard folders, loads Project Instructions, reads the previous handoff, and surfaces a briefing (kanban tasks, recent decisions, open PRs/issues). Reads and reports only. |
| `session-start` (skill) | read-only | Briefing/context-load protocol behind `session-start`. No writes. |
| `session-end` (command) | side-effectful-gated | **Writes the session handoff** to the project hub and **refreshes each writable GitHub repo's `README.md` (committed as its own atomic commit)**, then chains `/obsidian-update`. The README commit and handoff write are side-effectful; read-only repos are skipped, and the user spot-checks the reported paths/commits. Confirm before the write/commit (Tests 1, 5). |
| `session-end` (skill) | side-effectful-gated | Handoff-compose + README-refresh protocol behind `session-end`. It also merges schema-valid durable-knowledge proposals into Taskade `knowledge-candidates.json`; this transport is not Vault-write approval. Same gated write/commit surface. |
