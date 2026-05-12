# project-init

Cowork project lifecycle for MoxyWolf projects — scaffold once with `/init-project`, start every session with `/session-start`, end every session with `/session-end`.

## What it does

This plugin handles three phases of a MoxyWolf Cowork project:

### `/init-project` — first-time setup

When you start a new Cowork project, run `/init-project` to scaffold the Project Instructions. It assumes the three standard MoxyWolf roots are mounted in Cowork → Folders:

1. **MoxyWolf Vault**
2. **GitHub**
3. **Taskade**

It asks for your project name, then opens the **native Finder picker** so you can select the active Taskade subfolder and each active GitHub repo (no typing folder names). Then it generates tailored Project Instructions following the canonical MoxyWolf template.

The filled-in instructions are saved to the project's `00 – Project Hub/cowork-project-instructions.md` for future reference and displayed in chat for you to paste into Cowork → Settings → Project Instructions.

### `/session-start` — every-session resume

When you open a new Cowork session on an already-configured project, run `/session-start [project-name]`. It:

- Resolves which project (uses the argument or lists candidates)
- Reads the saved `cowork-project-instructions.md` to learn the active Taskade subfolder and GitHub repo(s)
- Mounts the three standard roots for this session via `mcp__cowork__request_cowork_directory`
- **Reads `cowork-session-handoff.md`** (written by the previous session's `/session-end`) and surfaces its "What landed", "Open work", and "Suggested opening line" at the top of the briefing
- Surfaces a focused briefing: handoff state, kanban P0/P1 tasks, recent decisions, open GitHub PRs and issues
- Asks what you want to focus on first, with options pulled from the handoff first (then kanban)

You go from "fresh Cowork window" to "loaded and oriented" in one step.

### `/session-end` — every-session wrap-up

When you're done for the day (or wrapping a focused session), run `/session-end [project-name]`. It:

- Resolves which project (argument, mounted-folder inference, or picker)
- Scans the conversation for what shipped, what's still open, what's uncommitted, and procedural reminders
- Composes a canonical-structured handoff document
- **Refreshes each writable GitHub repo's `README.md`** against a canonical 16-section structure (Header + badges, TOC, Environments, Quick Start, Architecture with Mermaid, Database Schema with ERD, Data Initialization, Key Features, API / Server Actions, Common Workflows, Troubleshooting, Security, Technology Stack, Project Structure, Deployment, License). Read-only repos are skipped. The README diff is surfaced as a separate commit block in the handoff so it pushes alongside the code it documents.
- Writes it to **`[project]/00 – Project Hub/cowork-session-handoff.md`** — fixed filename, overwritten each session, Drive versioning preserves history
- Optionally (`--archive` flag) also writes a dated copy to `00 – Project Hub/Session Handoffs/handoff-YYYY-MM-DD-HHMM.md`
- **Automatically runs `/obsidian-update`** at the end to capture durable knowledge — decisions, research findings, meeting discussions, cross-project insights, action items, new contacts — into the MoxyWolf vault. You no longer need to remember to run `/obsidian-update` separately.

The next time you run `/session-start [project-name]`, that handoff is the first thing the briefing surfaces.

## How to use

**To set up a new project:** type `/init-project` or say "set up a new project", "init a new Cowork project", "configure project instructions". The skill walks through the rest interactively with Finder pickers for folder selection.

**To resume an existing project:** type `/session-start [project-name]` or say "resume [project]", "start a session for [project]", "load [project] context". The skill mounts the standard roots and surfaces the briefing.

**To end a session:** type `/session-end [project-name]` or say "session-end", "end session", "wrap session", "save handoff". The skill writes the handoff that `/session-start` will read tomorrow.

## What gets generated

A filled-in Project Instructions document covering:

- **Mounted roots** — the three constants (MoxyWolf Vault, GitHub, Taskade) every project mounts
- **Project Setup** — declares the active Taskade subfolder and active GitHub repo subfolder(s) for *this* project
- **Three-directory model** — Taskade subfolder (read/write), MoxyWolf Vault (read for shared knowledge), GitHub repo(s) (read-only)
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

- **0.7.0** — `/session-end`'s "Suggested opening line" now always ends with an explicit pointer to the full handoff file's path (e.g. *"The full handoff is at `Taskade/Nexus/00 – Project Hub/cowork-session-handoff.md`."*). When the user pastes the opening line into a fresh Cowork chat, next-Cowork can immediately read the full handoff instead of working from the one-paragraph orientation alone.
- **0.6.0** — `/session-end` now automatically invokes `/obsidian-update:obsidian-update` as its final step. The wrap-up is now one command: write the project-scoped handoff, update the Cowork session-memory if warranted, then capture cross-project durable knowledge into the MoxyWolf Obsidian vault. No more remembering to run two commands at the end of every session.
- **0.5.0** — Added `/session-end` skill for wrapping a session. Writes a canonical-named handoff at `[project]/00 – Project Hub/cowork-session-handoff.md` covering what landed, open work in priority order, uncommitted code with full commit messages drafted, procedural reminders, and a suggested opening line for next session. `/session-start` now reads that handoff and surfaces it at the top of the briefing — including handoff items as the first focus options. Stale handoffs (>14 days) are flagged. Optional `--archive` flag on `/session-end` also writes a dated copy under `00 – Project Hub/Session Handoffs/`.
- **0.4.0** — Added `/session-start` skill for resuming work on an already-configured project. Mounts the three standard roots, reads the saved Project Instructions, surfaces a briefing (kanban P0/P1, recent decisions, open GitHub PRs/issues).
- **0.3.0** — `/init-project` now uses the native macOS Finder picker for selecting the active Taskade subfolder and each GitHub repo. No more typing folder names.
- **0.2.0** — Standardized on three mounted roots (MoxyWolf Vault, GitHub, Taskade). Project Instructions now declare *which subfolder* of each is active, instead of asking for full paths each time.
- **0.1.0** — Initial release with per-project primary working folder + full GitHub repo path collection.
