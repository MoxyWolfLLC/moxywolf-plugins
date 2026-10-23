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
| `init-project` (command) | side-effectful-gated | Mounts the standard MoxyWolf roots, gathers active Taskade/GitHub subfolders, and **writes tailored Project Instructions into the project hub** — scaffolding writes to shared Drive/repo locations. Confirm the roots and subfolders with the user before writing (Tests 1, 5). |
| `project-init` (skill) | side-effectful-gated | Underlying setup protocol for `init-project`: writes Project Instructions / scaffolding into the project hub. Same gated write surface. |
| `session-start` (command) | side-effectful-gated | Mounts standard folders, loads Project Instructions, reads the previous handoff, and surfaces a briefing (kanban tasks, recent decisions, open PRs/issues). For an org-shared project it also fast-forwards the local clones (`GitHub/Projects` and each listed repo). That's the only write, and its gate is mechanical: `--ff-only` on a clean tree, so local work is never touched; anything else is reported and left alone. |
| `session-start` (skill) | side-effectful-gated | Briefing/context-load protocol behind `session-start`. The one write is Step 3b's fast-forward-only pull of org-shared clones. |
| `session-end` (command) | side-effectful-gated | **Writes the session handoff** to the project hub and **refreshes each writable GitHub repo's `README.md` (committed as its own atomic commit)**, then chains `/obsidian-update`. The README commit and handoff write are side-effectful; read-only repos are skipped, and the user spot-checks the reported paths/commits. Confirm before the write/commit (Tests 1, 5). |
| `session-end` (skill) | side-effectful-gated | Handoff-compose + README-refresh protocol behind `session-end`. Same gated write/commit surface. |
