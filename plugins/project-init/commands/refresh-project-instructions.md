---
description: Migrate or refresh THIS Cowork project to the loader-stub model — apply the vault's on-disk reconciliation directives to the project's instructions file and emit its loader stub. Content comes from the vault spec, so no plugin update is needed when rules change.
argument-hint: ""
allowed-tools: [Read, Edit, Bash, AskUserQuestion]
---

# /project-init:refresh-project-instructions — re-stamp this project from the vault spec

Bring the current project's instructions up to date with the canonical loader-stub model (DR-010), reading everything from the vault spec so a rules change never requires touching this plugin. Run it once per existing project (and again any time the vault spec's `spec_version` bumps). **Surgical only** — never run `/init-project` from here, never regenerate or overwrite the instructions file wholesale.

## STEP 1 — Load the vault spec (the source of truth)

Read `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/project-instructions-loader-stub.md`. It holds the loader-stub skeleton (section 1 for Taskade projects, section 2 for vault-only, section 2b for org-shared projects in `GitHub/Projects`) and the on-disk reconciliation directives (section 3). If the file is missing, **stop** and tell the user — do not fall back to an inline copy; this file is authoritative. Note its `spec_version`.

## STEP 2 — Identify this project

Determine the project's display name (`PROJECT_NAME`), its workspace and, for a Taskade project, its subfolder (`SUBFOLDER`) from the project's own context: its current Cowork instructions, the mounted project folder, and the `Project Setup` block of its on-disk `cowork-project-instructions.md`. Org-shared projects live in `GitHub/Projects/<PROJECT_NAME>/` and are never stored in Taskade; use the section-2b paths. If the project is vault-only, use the section-2 paths. If you can't resolve the subfolder confidently, ask via AskUserQuestion rather than guess.

## STEP 3 — Apply the reconciliation directives (surgical)

Open the project's `00 – Project Hub/cowork-project-instructions.md` in its workspace: `GitHub/Projects/<PROJECT_NAME>/` (org-shared), `Taskade/<SUBFOLDER>/`, or the vault path for vault-only projects. For an org-shared project, pull `GitHub/Projects` fast-forward-only first, and commit and push the edited file afterwards (that project's folder only, as the `moxywolf-agent` app), then pull back. For each directive in the vault spec's section 3, in order:

- Find the stale shape it describes. If present, replace exactly the matched bullet/line with the directive's current text, using the Edit tool. Change nothing else.
- If the file is already current for that directive (idempotency check), make no change.

Never rewrite untouched sections. Never regenerate the file from the template. If a directive's stale shape is ambiguous in this file, surface it to the user instead of editing blindly.

## STEP 4 — Stamp + emit the loader stub

Take the skeleton from the vault spec (section 1 for Taskade projects, section 2 for vault-only, section 2b for org-shared), substitute `<PROJECT_NAME>` and `<SUBFOLDER>`, and output the result **verbatim in a fenced code block**. Above it, tell the user:

> Copy this into Cowork → Settings → Project Instructions for **<PROJECT_NAME>**, replacing the full text currently there. The full instructions stay on disk; this stub just points at them, so you paste it once and never re-paste when rules change.

## STEP 4b — Mirror to the claude.ai Project

Write four files into the claude.ai Project attached to this session, with the Projects tool's `project_write`, each at the workspace-relative path the loader stub names, so a session with no disk mount (a scheduled run, a phone or web session, a Mac that's asleep) can still read them (SM-008):

- `<WORKSPACE>/00 – Project Hub/cowork-project-instructions.md`
- `<WORKSPACE>/00 – Project Hub/project-surfaces.json`
- `<WORKSPACE>/00 – Project Hub/cowork-session-handoff.md`
- `GitHub/Projects/_shared-memory/INDEX.md`

`<WORKSPACE>` is `GitHub/Projects/<PROJECT_NAME>` for an org-shared project, `Taskade/<SUBFOLDER>` for a personal one, or `MoxyWolf Vault/Projects/<PROJECT_NAME>` for a vault-only one. Pass `local_path` for a file in the session workspace (stage it from the computer first if that's where it lives), otherwise `content`. A file that doesn't exist is skipped and named. With no Project attached (no Projects tool in the session), write nothing and report `not mirrored: no Project attached`. The copies are one-way: never write a Project copy back to disk, because disk wins whenever both are readable.

## STEP 5 — Report

State, concisely: which directives applied vs were already current (cite each by ID, e.g. D1), the `spec_version` this project is now aligned to, the STEP 4b mirror result (the paths written, or `not mirrored: no Project attached`), and a reminder that the stub still needs pasting into Cowork settings (the one manual, possibly per-machine step; the on-disk edits are on Drive and apply everywhere at once).

## Notes

- Idempotent and safe to re-run, including across machines.
- This command changes *content* sourced from the vault spec. To change what the stub says or to add a new fix that should reach every project, edit `project-instructions-loader-stub.md` in the vault and bump its `spec_version`, then re-run this command per project. The plugin stays untouched.
