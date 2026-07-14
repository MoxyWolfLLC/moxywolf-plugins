---
description: Migrate or refresh THIS Cowork project to the loader-stub model — apply the vault's on-disk reconciliation directives to the project's instructions file and emit its loader stub. Content comes from the vault spec, so no plugin update is needed when rules change.
argument-hint: ""
allowed-tools: [Read, Edit, Bash, AskUserQuestion]
---

# /project-init:refresh-project-instructions — re-stamp this project from the vault spec

Bring the current project's instructions up to date with the canonical loader-stub model (DR-010), reading everything from the vault spec so a rules change never requires touching this plugin. Run it once per existing project (and again any time the vault spec's `spec_version` bumps). **Surgical only** — never run `/init-project` from here, never regenerate or overwrite the instructions file wholesale.

## STEP 1 — Load the vault spec (the source of truth)

Read `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/project-instructions-loader-stub.md`. It holds the loader-stub skeleton (section 1, or section 2 for vault-only projects) and the on-disk reconciliation directives (section 3). If the file is missing, **stop** and tell the user — do not fall back to an inline copy; this file is authoritative. Note its `spec_version`.

## STEP 2 — Identify this project

Determine the project's display name (`PROJECT_NAME`) and active Taskade subfolder (`SUBFOLDER`) from the project's own context: its current Cowork instructions, the mounted Taskade folder, and the `Project Setup` block of its on-disk `cowork-project-instructions.md`. If the project is vault-only (no Taskade subfolder), note that and use the section-2 paths. If you can't resolve the subfolder confidently, ask via AskUserQuestion rather than guess.

## STEP 3 — Apply the reconciliation directives (surgical)

Open `Taskade/<SUBFOLDER>/00 – Project Hub/cowork-project-instructions.md` (or the vault path for vault-only projects). For each directive in the vault spec's section 3, in order:

- Find the stale shape it describes. If present, replace exactly the matched bullet/line with the directive's current text, using the Edit tool. Change nothing else.
- If the file is already current for that directive (idempotency check), make no change.

Never rewrite untouched sections. Never regenerate the file from the template. If a directive's stale shape is ambiguous in this file, surface it to the user instead of editing blindly.

## STEP 4 — Create or validate `project-surfaces.json`

Resolve the project's primary Taskade workspace (or explicit vault-only exception), Vault company-memory folder and MOC, aliases, task tags, related Taskade workspaces, and zero or more Git repositories with roles and access. Read the schema at `${CLAUDE_PLUGIN_ROOT}/schemas/project-surfaces.schema.json`.

- If `project-surfaces.json` is missing, present the proposed complete mapping and **confirm** it with the user before creating the file in the project hub.
- If it exists, run `${CLAUDE_PLUGIN_ROOT}/scripts/project_surfaces.py resolve` and report missing, ambiguous, or invalid surfaces. Do not silently rewrite a valid mapping.
- If the existing instructions and manifest disagree, present both sources and ask which is current before editing either one.

## STEP 5 — Stamp + emit the loader stub

Take the skeleton from the vault spec (section 1 for Taskade projects, section 2 for vault-only), substitute `<PROJECT_NAME>` and `<SUBFOLDER>`, and output the result **verbatim in a fenced code block**. Above it, tell the user:

> Copy this into Cowork → Settings → Project Instructions for **<PROJECT_NAME>**, replacing the full text currently there. The full instructions stay on disk; this stub just points at them, so you paste it once and never re-paste when rules change.

## STEP 6 — Report

State, concisely: which directives applied vs were already current (cite each by ID, e.g. D1), whether `project-surfaces.json` was created or validated, the `spec_version` this project is now aligned to, and a reminder that the stub still needs pasting into Cowork settings (the one manual, possibly per-machine step; the on-disk edits are on Drive and apply everywhere at once).

## Notes

- Idempotent and safe to re-run, including across machines.
- This command changes *content* sourced from the vault spec. To change what the stub says or to add a new fix that should reach every project, edit `project-instructions-loader-stub.md` in the vault and bump its `spec_version`, then re-run this command per project. The plugin stays untouched.
