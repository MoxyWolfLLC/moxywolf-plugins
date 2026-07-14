# project-init

Cowork project lifecycle for MoxyWolf projects — scaffold once with `/init-project`, start every session with `/session-start`, end every session with `/session-end`.

## What it does

This plugin handles three phases of a MoxyWolf Cowork project:

### `/init-project` — first-time setup

When you start a new Cowork project, run `/init-project` to scaffold the Project Instructions. It assumes the three standard MoxyWolf roots are mounted in Cowork → Folders:

1. **MoxyWolf Vault**
2. **GitHub**
3. **Taskade**

It asks for your project name, then opens the **native Finder picker** so you can select the active Taskade subfolder and each active GitHub repo (no typing folder names). Then it generates tailored Project Instructions and a `project-surfaces.json` manifest following the canonical MoxyWolf contracts.

The filled-in instructions and surface manifest are saved to the project's `00 – Project Hub/`. The manifest records the Taskade workspace, Vault company-memory folder, zero or more repositories, aliases, related workspaces, and task scope. The thin loader stub is displayed for Cowork → Settings → Project Instructions.

### `/session-start` — every-session resume

When you open a new Cowork session on an already-configured project, run `/session-start [project-name]`. It:

- Resolves which project (uses the argument or lists candidates)
- Reads `cowork-project-instructions.md` and resolves `project-surfaces.json`
- Loads a provenance-aware context packet without collapsing **Project workspace (Taskade)**, **Code workspace (Git)**, or **Company memory (Vault)**
- Registers an automatic SessionStart preflight, so direct MoxyWolf plugin calls still resolve that plugin's declaration even when `/session-start` was not invoked
- Defines the common preflight contract also bundled as a small model-invoked skill in every independently installable MoxyWolf plugin
- Mounts the three standard roots for this session via `mcp__cowork__request_cowork_directory`
- **Reads `cowork-session-handoff.md`** (written by the previous session's `/session-end`) and surfaces its "What landed", "Open work", and "Suggested opening line" at the top of the briefing
- Surfaces a focused briefing: handoff state, kanban P0/P1 tasks, recent decisions, open GitHub PRs and issues
- Asks what you want to focus on first, with options pulled from the handoff first (then kanban)

You go from "fresh Cowork window" to "loaded and oriented" in one step.

### `/session-end` — every-session wrap-up

When you're done for the day (or wrapping a focused session), run `/session-end [project-name]`. It:

- Resolves which project (argument, mounted-folder inference, or picker)
- Scans the conversation for what shipped, what's still open, the commit/push state of the active repo(s), and procedural reminders
- Composes a canonical-structured handoff document
- **Refreshes each writable GitHub repo's `README.md`** against a canonical 16-section structure (Header + badges, TOC, Environments, Quick Start, Architecture with Mermaid, Database Schema with ERD, Data Initialization, Key Features, API / Server Actions, Common Workflows, Troubleshooting, Security, Technology Stack, Project Structure, Deployment, License). Read-only repos are skipped. The README refresh is committed directly as its own atomic commit so it pushes alongside the code it documents.
- Writes it to **`[project]/00 – Project Hub/cowork-session-handoff.md`** — fixed filename, overwritten each session, Drive versioning preserves history
- Optionally (`--archive` flag) also writes a dated copy to `00 – Project Hub/Session Handoffs/handoff-YYYY-MM-DD-HHMM.md`
- **Automatically runs `/obsidian-update`** at the end to capture durable knowledge — decisions, research findings, meeting discussions, cross-project insights, action items, new contacts — into the MoxyWolf vault. You no longer need to remember to run `/obsidian-update` separately.
- Collects structured knowledge candidates with their producing plugin and supporting Taskade/Git sources. Candidates enter the normal `obsidian-update` approval plan; they never authorize a Vault write themselves.
- Persists schema-valid proposals in `00 – Project Hub/knowledge-candidates.json` as machine-readable Taskade transport for `obsidian-update`

The next time you run `/session-start [project-name]`, that handoff is the first thing the briefing surfaces.

### `/refresh-project-instructions` — migrate or re-stamp an existing project

Run this once per existing project to move it to the loader-stub model, or any time the vault stub spec changes. It:

- Reads the canonical spec `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/project-instructions-loader-stub.md` (the single source of truth — skeleton + on-disk fixes)
- Applies the spec's surgical on-disk reconciliation directives to this project's `cowork-project-instructions.md` (idempotent; preserves customizations; never regenerates the file)
- Creates or validates `project-surfaces.json` after the user confirms the project mapping
- Emits this project's loader stub for pasting into Cowork → Settings → Project Instructions

Because the content lives in the vault spec, changing a project-instruction rule is a vault edit + a per-project run of this command — no plugin update. Safe to re-run, including across machines.

## How to use

**To set up a new project:** type `/init-project` or say "set up a new project", "init a new Cowork project", "configure project instructions". The skill walks through the rest interactively with Finder pickers for folder selection.

**To resume an existing project:** type `/session-start [project-name]` or say "resume [project]", "start a session for [project]", "load [project] context". The skill mounts the standard roots and surfaces the briefing.

**To end a session:** type `/session-end [project-name]` or say "session-end", "end session", "wrap session", "save handoff". The skill writes the handoff that `/session-start` will read tomorrow.

**To migrate or refresh a project's instructions:** type `/refresh-project-instructions` in that project, or say "refresh the project instructions", "migrate this project to the loader stub". The command reads the vault spec, fixes the on-disk file surgically, and emits the stub to paste.

## What gets generated

A filled-in Project Instructions document and project surface manifest covering:

- **Mounted roots** — the three constants (MoxyWolf Vault, GitHub, Taskade) every project mounts
- **Project Setup** — declares the active Taskade subfolder and active GitHub repo subfolder(s) for *this* project
- **Three-plane model** — Taskade active work, Vault company memory, and zero or more Git repositories with explicit access
- **File-write override** — prevents the project-name/project-name nesting bug Cowork sometimes produces
- **Numbered-folder routing** — PRDs go to `02 – Product Strategy`, sprint specs to `04 – Backlog & Sprints`, papers to `11 – Project Knowledge/Papers/`, and so on
- **Publication artifacts override** — content-creation skills (editorial-forge, blog-content-ecosystem, etc.) that scaffold elsewhere must move publishable artifacts to Taskade before completion
- **Voice for literature rule** — read the Dorian voice profile (`MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md`) before drafting prose
- **Behavioral rules** — no time estimates in weeks, MoxyWolf is a small team not a solo founder, never fabricate names

## Requirements

- The MoxyWolf Vault must contain the canonical template at `_Templates/Cowork Project Instructions Template.md`. If it's missing, the skill stops and asks you to recreate it from a known-good project.
- The three standard roots (MoxyWolf Vault, GitHub, Taskade) should be mounted in Cowork → Folders. If any are missing the skill still generates the instructions, but flags the missing mount.
- The active Taskade subfolder must exist (or you can have the skill create it during setup).

## Why shared knowledge routes to the vault

The end-of-session **obsidian-update** workflow extracts session knowledge into the MoxyWolf Vault. The template explicitly directs all cross-project knowledge writes there. The plugin preserves this routing — it doesn't let per-project instructions override the vault destination for shared knowledge, because that breaks obsidian-update.

If a specific project genuinely needs a different routing for its own knowledge, the skill will write that as a "Project-Specific Overrides" addendum at the bottom of the filled-in instructions instead of mutating the core routing rules.

## Version history

- **0.21.0** — Adds the federated three-plane project contract (DR-014). `/init-project` creates `project-surfaces.json`; `/session-start` uses packaged deterministic resolvers to preserve Taskade current work, Git executable truth, and Vault company memory as separate authority domains; `/session-end` collects structured knowledge candidates for approval-gated `obsidian-update`. Supports aliases, Vault-only exceptions, multiple repositories, related Taskade workspaces, missing-surface warnings, path confinement, and secret exclusions.
- **0.19.0** — The stub skeleton and the on-disk reconciliation directives move **out of the plugin into a vault spec** — `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/project-instructions-loader-stub.md` — that both `/init-project` and the new **`/refresh-project-instructions`** command read at run time. `/refresh-project-instructions` migrates or re-stamps an existing project from that spec: it applies the spec's surgical on-disk fixes (idempotent; preserves customizations) and emits the project's loader stub for pasting. The point: changing a project-instruction rule is now a **vault edit + a per-project command run**, never a plugin update or reinstall. The plugin holds the process; the vault holds the content.
- **0.18.0** — `/init-project` switches to the **loader-stub model** (DR-010). The full instructions are saved on disk (`00 – Project Hub/cowork-project-instructions.md`) as the single source of truth; the Cowork → Settings → Project Instructions field gets only a thin **loader stub** — mounts, the file-write-path override, and an imperative to read the on-disk file + `_shared-memory/INDEX.md` first. The embedded copy can no longer drift out of sync with the file (paste once, never re-paste). Fixes the failure mode where the on-disk instructions get updated but the pasted Cowork copy keeps a stale rule (e.g. the clipboard-vs-vault PAT method that lingered in pasted copies after DR-011). The canonical Project Instructions template's commit-and-push section was also corrected to read the PAT from the vault file, not the clipboard.
- **0.17.0** — Moved the classic PAT off the clipboard into the **vault file** `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/github-pat.env` (DR-011), loaded by the sandbox like `openrouter.env`. Commit+push authenticate with a per-URL auth header and **verify the push landed via `git ls-remote`** (a SHA match vs `git rev-parse HEAD`). The token is never echoed or committed. See `reference_github_pat_vault`.
- **0.16.0** — Switched the commit/push model to **sandbox `git` + a classic PAT**: Claude now commits AND pushes directly, with no GitHub Desktop in the loop. Reads still go through the official GitHub MCP connector (`https://api.githubcopilot.com/mcp/`), but its OAuth can't write to org repos (`403 Resource not accessible by integration`), so writes use the account-wide classic PAT (token now in the vault file `github-pat.env` per DR-011; originally clipboard-provided). `/session-end` now records the commits that *landed* this session rather than commits awaiting a human push. See `reference_github_pat_vault` and `feedback_repos_writable_commits_via_github_desktop`.
- **0.12.0** — Updated `/session-end` and `/session-start` for the direct-commit workflow (team-shared rule revised 2026-05-20). Claude now commits its code changes directly during the session and at session-end — the Step 5c README refresh is committed directly as its own atomic commit, not left for next session. The handoff's `Uncommitted code` section is renamed `Commit & push state` and records local commits awaiting push rather than draft messages to paste; `/session-start` accepts either title. The plain-text commit-message format is retained as the fallback hand-off path for when Claude can't commit directly. Claude never pushes — the human still reviews and pushes via GitHub Desktop.
- **0.7.0** — `/session-end`'s "Suggested opening line" now always ends with an explicit pointer to the full handoff file's path (e.g. *"The full handoff is at `Taskade/Nexus/00 – Project Hub/cowork-session-handoff.md`."*). When the user pastes the opening line into a fresh Cowork chat, next-Cowork can immediately read the full handoff instead of working from the one-paragraph orientation alone.
- **0.6.0** — `/session-end` now automatically invokes `/obsidian-update:obsidian-update` as its final step. The wrap-up is now one command: write the project-scoped handoff, update the Cowork session-memory if warranted, then capture cross-project durable knowledge into the MoxyWolf Obsidian vault. No more remembering to run two commands at the end of every session.
- **0.5.0** — Added `/session-end` skill for wrapping a session. Writes a canonical-named handoff at `[project]/00 – Project Hub/cowork-session-handoff.md` covering what landed, open work in priority order, uncommitted code with full commit messages drafted, procedural reminders, and a suggested opening line for next session. `/session-start` now reads that handoff and surfaces it at the top of the briefing — including handoff items as the first focus options. Stale handoffs (>14 days) are flagged. Optional `--archive` flag on `/session-end` also writes a dated copy under `00 – Project Hub/Session Handoffs/`.
- **0.4.0** — Added `/session-start` skill for resuming work on an already-configured project. Mounts the three standard roots, reads the saved Project Instructions, surfaces a briefing (kanban P0/P1, recent decisions, open GitHub PRs/issues).
- **0.3.0** — `/init-project` now uses the native macOS Finder picker for selecting the active Taskade subfolder and each GitHub repo. No more typing folder names.
- **0.2.0** — Standardized on three mounted roots (MoxyWolf Vault, GitHub, Taskade). Project Instructions now declare *which subfolder* of each is active, instead of asking for full paths each time.
- **0.1.0** — Initial release with per-project primary working folder + full GitHub repo path collection.
