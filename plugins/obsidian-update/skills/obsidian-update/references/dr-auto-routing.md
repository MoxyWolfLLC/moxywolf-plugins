# Decision Record Auto-Routing + Master Index

This reference is loaded by the `obsidian-update` skill when it is about to write a Decision Record. It supersedes any earlier ad-hoc placement rule.

## Rule 1 — Pick the destination folder by topic

Classify the DR by primary topic, then route:

| Topic class | Destination | Rationale |
|---|---|---|
| Engineering / architecture / tech-stack / infra | `Projects/<P>/06-Engineering/` (project-scoped) **or** `_Shared Knowledge/Tech Stack/` (cross-project) | Engineering decisions belong next to the code that implements them. |
| GTM / pricing / messaging / channels | `Projects/<P>/08-GTM/` | GTM decisions stay with the project's GTM artifacts. |
| Brand / voice / visual identity | `_Shared Knowledge/Brand and Voice/` | Cross-project by design. |
| Compliance / control / framework mapping | `_Shared Knowledge/Compliance Frameworks/` | Cross-project; framework-keyed. |
| Operating norm / cross-cutting team rule | `_Shared Knowledge/Operating Norms/` | The default for company-wide DRs. |
| Product decision (priorities, roadmap, scope) | `_Shared Knowledge/Product Decisions/` | Cross-product portfolio decisions. |
| Council / model selection / agent behavior | `_Shared Knowledge/Agents and Plugins/` | Where Council deliberation logs live. |
| Personnel / people / hiring | `People/` index, plus a one-line entry in `_Shared Knowledge/Operating Norms/` if rule-bearing | Sensitive — keep the durable rule in Operating Norms, the person-specific note in People. |

**Decision rule:** if a DR is genuinely cross-cutting, prefer the shared destination. If it's about a specific project AND not generalizable, prefer the project subfolder. When in doubt, default to `_Shared Knowledge/Operating Norms/`.

If a DR resolves a debate or supersedes a prior DR, add `supersedes: [[<old-DR>]]` to its frontmatter and add `superseded-by: [[<new-DR>]]` to the old one.

## Rule 2 — Always append to the Company Decision Log master index

Every DR write — regardless of destination folder — must append one row to:

```
${VAULT}/_Shared Knowledge/Operating Norms/_INDEX.md
```

If `_INDEX.md` doesn't exist, create it with this exact preamble:

```markdown
---
title: Company Decision Log — Master Index
type: index
tags:
  - decision-log
  - operating-norms
---

# Company Decision Log — Master Index

This file is the single canonical index of every Decision Record written across the MoxyWolf knowledge base. It is auto-updated by `obsidian-update` on every DR write. Do not hand-edit row order — append-only, newest at the bottom.

| Date | DR ID | Project | Title | Destination | Supersedes |
|---|---|---|---|---|---|
```

Then append a single row per DR with this format:

```
| YYYY-MM-DD | [[DR-XXX-slug]] | <project or `shared`> | <one-line title> | <destination folder, vault-relative> | <[[DR-YYY-slug]] or empty> |
```

Use the same `DR-XXX` numbering scheme already in use across the vault. If the next number is ambiguous (project-local vs global), pick the next **global** number — the master index keeps numbering globally unique so any DR ID can be looked up here.

## Rule 3 — Update the project hub when applicable

If the DR is project-scoped, also append a one-line `- YYYY-MM-DD [[DR-XXX-slug]] <title>` bullet to `Projects/<P>/00-Hub/<P> Decisions.md` (create the file from `_Templates/Project Decisions Index.md` if it doesn't exist).

## Rule 4 — Council-verified DRs

When the Council Verification Gate ran and approved the DR, add `council-verified: true` and `council-deliberation: [[<deliberation-log-anchor>]]` to the DR's frontmatter. The master-index row gets a `✓` suffix on the title cell.

## Idempotence

If a DR with the same ID already exists in `_INDEX.md`, **do not append a second row** — update the existing one in place. The index is keyed by DR ID.

## Backfill

The first time this routing reference runs in a vault that already has DRs scattered across folders, walk every `DR-*.md` file under `_Shared Knowledge/`, `Projects/*/`, and any other historical location, and seed `_INDEX.md` with one row per discovered DR before appending the new one. Sort the backfill rows by file mtime ascending so the table reads chronologically.
