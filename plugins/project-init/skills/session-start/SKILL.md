---
name: session-start
description: This skill should be used when the user says "start a session for [project]", "resume [project]", "load [project] context", "/session-start", "open [project] in Cowork", "pick up where I left off on [project]", or any request to begin or resume work on an existing MoxyWolf project. It assumes the project has already been initialized via /init-project (i.e. has a saved cowork-project-instructions.md in its `00 – Project Hub/`). It mounts the three standard MoxyWolf roots, reads the project's saved Project Instructions, and surfaces a briefing — kanban tasks, recent decisions, open PRs/issues — so the session can pick up immediately.
---

# Session Start

Start or resume a Cowork session for an existing MoxyWolf project. Mount the three standard roots (MoxyWolf Vault, GitHub, Taskade) for this session, read the project's saved Project Instructions to learn the active Taskade subfolder and GitHub repo(s), then surface a focused briefing — kanban P0/P1 tasks, recent decisions, open GitHub PRs and issues — so the user can dive straight into work.

## When to use

Trigger when the user is starting or resuming a Cowork session on an existing MoxyWolf project. Common triggers:

- `/session-start [project-name]`
- "start a session for [project]"
- "resume [project]"
- "load [project] context"
- "open [project] in Cowork"
- "pick up where I left off on [project]"

The skill assumes the project has already been initialized via `/init-project` and has a saved `cowork-project-instructions.md` in its `00 – Project Hub/`. If no such file exists, route the user to `/init-project` first instead of inventing a config.

## Standard mounted roots

Every MoxyWolf Cowork project assumes these three roots:

1. **MoxyWolf Vault** — `/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/MoxyWolf Vault`
2. **GitHub** — `/Users/doriancougias/Documents/GitHub`
3. **Taskade** — `/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/Taskade`

The skill mounts these three constants every time. The Project Instructions assume them.

## Steps

### Step 1: Resolve which project

If the user passed a project name with the slash command (e.g. `/session-start SAMS`), use it directly. Otherwise:

a. Scan `Taskade/` for subfolders that contain `00 – Project Hub/cowork-project-instructions.md`. Also scan `MoxyWolf Vault/Projects/` for vault-only projects with the same file.

b. Sort candidates by recency of modification of the saved instructions file (most-recently-edited first).

c. Present the top ~6 candidates as multiple-choice options via AskUserQuestion. The final option is "Other — type a project name" for the rare case where the user wants a project not yet in the list.

d. If the user types a name that doesn't match any folder, list the available project folders and ask them to pick from the list (don't try to create a new project — that's `/init-project`'s job).

### Step 2: Read the saved Project Instructions

Read `Taskade/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` (or `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` for vault-only projects).

Parse to extract:

- The active Taskade subfolder name (or `none` for vault-only projects)
- The list of active GitHub repos (subfolder names + descriptions) — there may be 0, 1, or many
- Any `## Project-Specific Overrides` block at the bottom

If the file doesn't exist, abort with: *"No saved Project Instructions found for [PROJECT_NAME]. Run `/init-project` first to set this project up."*

### Step 3: Mount the three standard roots

For each of the three standard roots, call `mcp__cowork__request_cowork_directory` with the explicit `path` argument. The user sees the path and approves; the folder is then mounted for this session. Make these calls in a single message (parallel) so all three approval prompts surface together.

If a root is already mounted, `request_cowork_directory` is effectively a no-op — record that in the briefing as "already mounted" rather than "newly mounted".

If the user declines to approve a particular root, note it in the briefing and continue with whichever roots were approved.

### Step 4: Gather context (parallel)

In a single message, run these reads in parallel:

a. **Session handoff (highest priority)** — Read `[project]/00 – Project Hub/cowork-session-handoff.md` if it exists. This is the canonical handoff written by `/session-end` at the end of the previous session. Parse the handoff's frontmatter (`session_ended` timestamp, plus the optional `author` and `for` fields — both lowercase first names) and these sections:
   - `## What landed this session`
   - `## Open work, in priority order`
   - `## Uncommitted code`
   - `## Procedural reminders for next-Claude`
   - `## Suggested opening line`

   The `author` and `for` frontmatter fields tell next-Claude who wrote the handoff and whether it was an explicit baton-pass. They're optional — older handoffs predating the auto-write feature won't have them; treat the absence as "author unknown, no explicit baton-pass" and surface that in the briefing rather than guessing.

   Stale-detection: if `session_ended` is more than 14 days old, flag the handoff as **stale** in the briefing. The user may want to skip the suggested-opening-line and focus on current kanban state instead.

   If the file doesn't exist, that's fine — older projects predating `/session-end` won't have one. Note "no handoff from previous session" in the briefing and continue.

b. **Kanban / task board** — Read `MoxyWolf Vault/Tasks/KANBAN_VIEW.md`. Filter to items tagged with this project's name or its known acronym/alias (e.g. SAMS, STIGViewer, RegGenome). Pull:
   - Top 3 P0 items
   - Top 3 P1 items
   - All Waiting items for this project

c. **Recent decision records** — Search the project's folder structure (Taskade subfolder + the project's `MoxyWolf Vault/Projects/[PROJECT_NAME]/` mirror, if it exists) for files matching `DR-*.md` modified in the last 14 days. Extract the title and one-line summary from each file's frontmatter. Cap at 5 items.

d. **Open GitHub PRs and recent issues** — For each repo in the parsed GitHub repo list, query the GitHub MCP for:
   - All open PRs (title, author, last-updated)
   - Top 5 most-recently-updated open issues (title, author, last-updated)

If any of these sources is unavailable (file missing, MCP not connected), capture the failure in the briefing instead of aborting. The remaining context is still useful.

### Step 5: Display the briefing

Output a structured briefing in chat. The session handoff (if found) is the most important section because it's the freshest source of state. Use these sections in this order:

```
## Project: [PROJECT_NAME]

**Mounted folders**
- MoxyWolf Vault — [newly mounted | already mounted]
- GitHub — [newly mounted | already mounted]
- Taskade — [newly mounted | already mounted]

**Active subfolders**
- Taskade/[active-taskade-subfolder]
- GitHub/[repo-1] — [description]
- GitHub/[repo-2] — [description]   (if applicable)

**Last session ended:** YYYY-MM-DD HH:MM PT  [— stale (>14 days)]   (if handoff found)
**Authored by:** [author, title-cased]   [— **explicit baton-pass to [for, title-cased]**]   (skip the "explicit baton-pass…" suffix if no `for`; skip the whole line if no `author`)

**Last session left off with**
[the "What landed this session" paragraph from the handoff, verbatim]

**Top of next-session stack** (from the handoff's "Open work, in priority order")
1. [title of first open-work item from handoff]
2. [title of second open-work item from handoff]
3. [title of third open-work item from handoff, if applicable]

**Suggested opening line from previous session**
> *"[the handoff's suggested-opening-line, verbatim]"*

[If the handoff has uncommitted code:]
**Uncommitted code drafted in the handoff**
- [N] commits with summary + description ready to paste into GitHub Desktop. See handoff §Uncommitted code.

[If no handoff was found, replace the four sections above with:]
**Last session left off with**
- _(no handoff from previous session — pre-`/session-end` project, or first session)_

**Top tasks (kanban)**
- P0: …
- P1: …
- Waiting: …

**Recent decisions (last 14 days)**
- [DR title] — [one-line summary]

**Open PRs**
- [repo-name]
  - #123 [title] — [author], updated [date]

**Open issues** (top 5 per repo)
- [repo-name]
  - #456 [title] — [author], updated [date]
```

Keep each line tight. This is a briefing, not a report.

If a section had no findings (e.g. "no DRs in last 14 days", "no open PRs in [repo]"), say so on one line rather than omitting the section silently.

### Step 6: Ask what to work on first

End with a single AskUserQuestion: *"What do you want to focus on first?"* with options pulled, in this order of priority:

- The handoff's first open-work item (if a handoff was found and not stale)
- The handoff's second open-work item (if applicable)
- Top 1 P0 from kanban (if any, and not duplicating a handoff item)
- "Just brief me — I'll decide"

Do not exceed 4 options total.

If the handoff was stale (>14 days old), drop the handoff items from the focus options and fall back to kanban-only — stale handoffs probably don't reflect current priorities.

If no handoff was found, options pull from kanban only:

- Top 1–2 P0 items (if any)
- Top 1–2 P1 items (if any)
- "Just brief me — I'll decide"
- "Something else" (free-text fallback)

## Output

- Three standard roots mounted (or confirmed already-mounted)
- A structured briefing in chat covering the project's current state
- A focus question to start the work

## Edge cases

- **No saved Project Instructions for this project.** Stop and route to `/init-project`. Do not invent a config.
- **No `cowork-session-handoff.md` file.** Treat as "no previous handoff" and skip the handoff sections of the briefing. The kanban / DRs / GitHub MCP sections still surface project state. This is normal for projects predating `/session-end` or for a project's first session.
- **`cowork-session-handoff.md` is malformed (can't parse expected sections).** Surface the parse failure in the briefing as a one-line warning ("handoff file at [path] couldn't be parsed; falling back to kanban / DRs / GitHub state"). Continue with the rest of the briefing. Don't try to fix the file — let the user reconcile it.
- **`cowork-session-handoff.md` is stale (`session_ended` > 14 days old).** Surface the staleness in the "Last session ended" line and drop the handoff's open-work items from the focus options in Step 6. The kanban is the more current source of priorities at that point.
- **One of the three standard roots not approved.** Note it in the briefing's "Mounted folders" section and continue with whichever were approved.
- **GitHub MCP not connected.** Skip the open-PRs and open-issues sections, note that the GitHub MCP isn't available, and suggest connecting it.
- **Kanban view file missing.** Skip the kanban section, note that the file wasn't found at `MoxyWolf Vault/Tasks/KANBAN_VIEW.md`, and continue.
- **Project name passed with slash command doesn't match any folder.** List the available project folders (sorted by recency) and ask the user to pick from the list.
- **Vault-only project (no Taskade subfolder).** Read the Project Instructions from `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` instead. Look for the handoff at the same vault path. Skip Taskade-subfolder references in the briefing.
- **Project Instructions file is malformed (can't parse the active Taskade subfolder or GitHub repo list).** Surface the parse failure to the user and ask them to either edit the file by hand or rerun `/init-project`. Don't proceed with a guessed config.

## Notes

- This skill complements `/init-project` and `/session-end`. `/init-project` configures a project once; `/session-end` writes the per-session handoff at the end of each session; `/session-start` reads that handoff to brief next-session Claude in one step.
- The briefing is intentionally short. Detailed exploration is a follow-up task within the session.
- The skill reads but does not write. It does not modify the kanban, the project instructions, the session handoff, or any decision records. End-of-session writing is `/session-end`'s job (project-scoped handoff) and `/obsidian-update`'s job (cross-project knowledge to vault).
- The standard roots are constants. Don't ask the user to confirm which roots to mount — always mount the same three.
- The handoff file path is fixed: `[project]/00 – Project Hub/cowork-session-handoff.md`. Don't fall back to other filenames (`continuation-prompt-*.md`, etc.) — those are free-form, written before this contract existed, and not parseable. If the user wants those surfaced too, they can ask explicitly.
