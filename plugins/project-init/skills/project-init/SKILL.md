---
name: project-init
description: This skill should be used when the user says "set up a new project", "init a new project", "new Cowork project", "start a new project", "set up project", "/init-project", or any request to scaffold Project Instructions for a project that does NOT already have them. It assumes the three standard MoxyWolf roots (MoxyWolf Vault, GitHub, Taskade) are mounted in Cowork, then interactively gathers the active Taskade subfolder and active GitHub repo subfolder(s), and produces tailored Project Instructions following the MoxyWolf template, with shared-knowledge writes routed to the MoxyWolf Vault for end-of-session obsidian-updates. Saves the full instructions on disk as the single source of truth and emits a thin loader stub for Cowork's settings field (the stub points at the on-disk file, so the embedded copy never drifts). Before doing anything else it checks whether the resolved project already has a saved cowork-project-instructions.md — if it does, it stops and redirects to /refresh-project-instructions instead of asking "which project" and re-scaffolding, since re-running this skill on an already-initialized project would silently overwrite the on-disk file (including any hand-written Project-Specific Overrides). For "update/refresh/fix this project's instructions" on an already-set-up project, use /refresh-project-instructions directly, not this skill.
---

# Project Init

Generate tailored Project Instructions for a new Cowork project. The MoxyWolf convention is that every Cowork project mounts the same three roots — MoxyWolf Vault, GitHub, and Taskade — and the Project Instructions just declare *which* subfolder of Taskade is the active project and *which* subfolder of GitHub is the active repo. Read the MoxyWolf template, gather per-project specifics through AskUserQuestion, substitute placeholders, save the full filled instructions to the project's Project Hub folder (the single source of truth), and display a thin **loader stub** for the user to paste into Cowork's settings — the stub points at the on-disk file rather than duplicating it, so the embedded copy can never drift out of sync with the source.

## When to use

Trigger when the user is starting a **new** Cowork project and needs Project Instructions configured for the first time. Common triggers:

- "set up a new project"
- "init a new project"
- "new Cowork project"
- "start a new project"
- "/init-project"

**Do not trigger on "configure project instructions", "update project instructions", "fix the project instructions", or similar phrasing about a project that's already running in this Cowork session** — that almost always means the project already has a saved `cowork-project-instructions.md` and the user wants `/refresh-project-instructions` (surgical, non-destructive), not a from-scratch re-scaffold. If genuinely unsure which the user means, run this skill's **Step 0 guard** below rather than guessing from phrasing alone — it settles the question by checking whether saved instructions already exist.

The one case this skill legitimately handles for an existing project is the user explicitly asking to **regenerate Project Instructions from scratch** (full re-scaffold, not a rules update) — Step 0 still runs first and requires explicit confirmation before overwriting anything.

## Step 0 — Guard: is this project already initialized?

**Run this before asking anything, including the project name.** The failure mode this prevents: running `/init-project` again on an already-initialized project silently overwrites its on-disk `cowork-project-instructions.md` — including any hand-written `## Project-Specific Overrides` — with a freshly-generated file, and along the way asks "which project are we initializing" even when the answer (e.g. "Team Plugins") is already sitting in the current session's mounted context. Never let Step 3's write execute without this guard having run first.

1. **Resolve the current project from context — the same way `/session-start` does — before asking the user anything.** Check, in order: (a) an explicit project name if the user already stated one this turn, (b) the launch directory / currently mounted Taskade subfolder for this Cowork session (a mounted path matching `.../Taskade/<NAME>/...` or `.../MoxyWolf Vault/Projects/<NAME>/...` resolves to project `<NAME>`), (c) otherwise, no project resolves yet — that's fine, skip to step 4.
2. **If a project resolved in step 1, check whether it already has saved instructions:** does `Taskade/<NAME>/00 – Project Hub/cowork-project-instructions.md` (or `MoxyWolf Vault/Projects/<NAME>/00 – Project Hub/cowork-project-instructions.md` for vault-only) exist?
3. **If it exists: stop.** Do not proceed to "Inputs to collect" or ask "which project are we initializing" — the project name is already known (`<NAME>`), and re-running this skill would overwrite the very file that answers that question. Tell the user, in one line, that `<NAME>` already has saved Project Instructions. Then ask via AskUserQuestion:
   - **`Run /refresh-project-instructions instead`** (default/recommended) — the surgical, non-destructive path that applies pending team-wide fixes without touching anything else. If chosen, hand off to that command's procedure directly.
   - **`Show me the current file`** — read and display it; don't modify anything.
   - **`Regenerate it from scratch anyway`** — explicitly destructive. Only take this path if the user picks it. Warn first that any `## Project-Specific Overrides` section will be lost unless saved elsewhere, get an explicit second confirmation, and only then proceed to "Inputs to collect" for a full re-scaffold.
4. **If no project resolves from context, or the resolved project has no saved instructions yet:** proceed normally to "Inputs to collect" — this is a genuinely new project, and Section 1 (Project name) is the right place to ask.
5. **If the user's answer to Section 1 (Project name) turns out to name a project that already has saved instructions** (only discoverable after asking, e.g. context didn't resolve it in step 1 but the user typed an existing name): apply the same stop-and-redirect as step 3 before touching Step 3's write.

## Standard mounted roots

Every MoxyWolf Cowork project assumes these three roots are mounted in Cowork → Folders. The skill does not ask about them — they're constants:

1. **MoxyWolf Vault** — `/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/MoxyWolf Vault`
2. **GitHub** — `/Users/doriancougias/Documents/GitHub`
3. **Taskade** — `/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/Taskade`

If the user mentions that one of these isn't mounted yet, auto-mount it before proceeding — see **Folder access** below; don't just remind them to add it manually.

## Folder access — works online (cloud) or offline (on-computer)

Cowork runs either **online** (cloud) or **offline** (on the user's computer), and folder picking differs. **Don't hard-depend on any one mount/pick tool** — detect each capability by whether its tool is present, with a filesystem fallback that works in both modes. This convention governs every folder-pick step below.

- **Pick a subfolder.** If `mcp__cowork__request_cowork_directory` is present, open the native picker by calling it with **no `path` argument**; take the basename of the resolved path. If it isn't present, enumerate the relevant root's immediate subfolders (`mcp__remote-devices__device_list_dir` online, or `ls` on the path offline) and present them via `AskUserQuestion` chips — the user clicks a folder, never types — with a free-text "Other" fallback.
- **Detect what's available** (mode-agnostic): `mcp__remote-devices__get_device_info` → `connectedFolders` when present (online), else probe the path directly by listing it (offline). A successful listing = available; an error = missing.
- **Get a missing root mounted — auto-mount first, ask only as fallback.** **Online:** if `mcp__remote-devices__device_request_folder_access` is present, proactively request every currently-missing root's exact absolute path in **one call** (single approval dialog covering all of them) — this is the default action, not something to try only after asking the user. **On-computer:** if `request_cowork_directory` is present, call it with the explicit `path`. **Fallback only** — if neither tool is present, or the user declines the request/approval: ask the user to add the exact path (**online:** the desktop app's **Add folder** button; **offline:** Cowork → Folders → Add), then re-detect.

Nothing here requires `request_cowork_directory` or `device_request_folder_access` specifically — each is used when present, with the manual-ask path as the last resort, so the skill runs online or offline.

## Inputs to collect

**Folder selection rule — never ask the user to type a folder name.** Identify each subfolder with the method from the **Folder access** convention above: the native picker when `request_cowork_directory` is present, otherwise a `device_list_dir` + `AskUserQuestion` chip menu. Either way the user clicks rather than types — much faster and zero typos.

Gather inputs in this order, one decision at a time:

### 1. Project name

Only reached if **Step 0** found no already-initialized project in context. Ask via AskUserQuestion for the project name in kebab-case or original casing as the user prefers (e.g., "Nexus", "SAMS", "Frontier Founder", "STIGViewer"). Free-text via the "Other" option is fine here. This is the canonical project identifier and appears throughout the instructions. If the answer names a project that turns out to already have saved instructions, apply Step 0's stop-and-redirect logic (its point 5) before continuing.

(Tip: if the user has already picked the Taskade folder before answering this, default the suggested project name to the picked folder's basename — they can still override.)

### 2. Active Taskade subfolder — Finder picker

Do **not** ask the user to type the folder name. Instead:

a. First, ask via AskUserQuestion whether this project uses Taskade. Options:
   - **`Yes — pick the Taskade subfolder now`** (default)
   - **`No — vault-only project`** (the project will then write into `MoxyWolf Vault/Projects/[PROJECT_NAME]/` instead)

b. If "Yes": identify the subfolder using the **Folder access** convention. *If `mcp__cowork__request_cowork_directory` is present*: call it with **no `path` argument** so the native picker opens; tell the user — just before the call — to navigate into `MoxyWolf Shared Files/Taskade/` and pick the project's subfolder. *Otherwise*: call `mcp__remote-devices__device_list_dir` on the `Taskade/` root (or `ls` it offline) and present its subfolders via `AskUserQuestion` chips for the user to pick. Either way, take the basename of the chosen path as `[TASKADE_SUBFOLDER]` and confirm back: "Got it — using `Taskade/<basename>`."

c. If the picker is dismissed / the chip menu is declined or returns nothing, fall back to AskUserQuestion with a free-text "type the folder name" option, and surface the issue in the final output.

The full path is always `Taskade/[TASKADE_SUBFOLDER]`.

### 3. GitHub repo count

Ask via AskUserQuestion: how many local GitHub repos under `GitHub/` does this project use? Options: `0`, `1`, `2`, `3 or more`.

### 4. GitHub repo subfolder(s) — Finder picker, one per repo

If repo count >= 1, do **not** ask the user to type repo names. For each repo:

a. Identify the repo folder using the **Folder access** convention. *If `mcp__cowork__request_cowork_directory` is present*: call it with **no `path` argument** to open the native picker; prompt the user first: "Pick repo 1 of N — navigate into `~/Documents/GitHub/` and select the repo folder." *Otherwise*: call `mcp__remote-devices__device_list_dir` on the `GitHub/` root (or `ls` it offline) and present its repo subfolders via `AskUserQuestion` chips for the user to pick (one repo per question).

b. When the pick returns, take the basename of the resolved path as that repo's `[REPO_SUBFOLDER]`. Confirm back: "Got it — `GitHub/<basename>`."

c. After each repo is picked, ask via AskUserQuestion (separately) for a short one-line description (e.g., "Main service code", "Frontend app", "Marketing site") with a "Skip — use repo name only" option.

d. Repeat until all N repos are picked. If the user wants to add a repo that isn't yet cloned under `GitHub/`, offer a follow-up "Type a custom name" option after the picker is dismissed; accept the name as free text and flag in the final output that the repo subfolder doesn't exist locally yet.

### 5. Kanban project tag(s)

The team task board is Jira, project **MOXY** — a single board shared by every MoxyWolf project (the vault `KANBAN_VIEW.md` was retired 2026-07-16 when Jira became the single board). Each issue is scoped by a Jira **label** of the form `project-<slug>`. `/session-start` uses that label to brief the user on this project's tasks only, so every project must declare which `#project/…` scope(s) its issues carry. The `#project/<slug>` value is stored in the instructions for readability and maps to the Jira label `project-<slug>` (Jira labels can't contain `/`).

Ask via AskUserQuestion (multi-select): *"Which `#project/…` scope(s) do this project's tasks carry on the MOXY board?"* Build the options from:

- The kebab-cased project name (e.g. project "Team Plugins" → `#project/team-plugins`)
- Each GitHub repo subfolder name picked in section 4 (e.g. `#project/moxywolf-plugins`)
- `none — this project has no board presence`

The user can pick one option, several (multi-select), or type a custom slug via "Other". Most projects carry exactly one slug, and it usually matches either the kebab-cased project name or a repo name — but not always (the "Team Plugins" project's scope is `moxywolf-plugins`, the repo name, not the project name). Don't assume; let the user confirm. Confirm back: "Got it — board scope `#project/<slug>` (Jira label `project-<slug>`)."

Store the result as `[KANBAN_SLUG]`: a single slug, a comma-separated list of slugs, or `none`.

If the user can't answer a question or wants to defer, accept "skip" and proceed with reasonable defaults; flag deferred items in the output so the user knows to fill them in later.

## Steps

### Step 1: Read the canonical template

Read the template from:

`/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/MoxyWolf Vault/_Templates/Cowork Project Instructions Template.md`

If the template file is missing, stop and tell the user — the template is the source of truth for project instruction structure. Suggest they recreate it from a known-good project (Nexus has a working instantiation in its Project Hub).

The template starts with template-meta-instructions ("Copy everything below..."). The actual instructions begin at the first `---` separator after that. Keep only the content from `# [PROJECT_NAME] Project Instructions` onward.

### Step 2: Substitute placeholders

Replace placeholders with the user's answers:

- Every `[PROJECT_NAME]` → the project name from Step 1
- Every `[TASKADE_SUBFOLDER]` → the active Taskade subfolder from Step 2
- The `[REPO_SUBFOLDER]` placeholder and the section 3 ("GitHub/[REPO_SUBFOLDER]") block:
  - **0 repos:** in *Project Setup*, replace the `Active GitHub repo:` line with `**Active GitHub repo:** none`. Remove the entire section 3 block (heading and body). Leave the *Mounted Roots* section unchanged — the GitHub root stays mounted as a constant even if this project doesn't use a repo, since other Cowork sessions on the same machine will.
  - **1 repo:** substitute the `[REPO_SUBFOLDER]` placeholder with the single repo subfolder name in both *Project Setup* and section 3. If you have a one-line description, append it after the path in section 3.
  - **2+ repos:** in *Project Setup*, replace the `Active GitHub repo:` bullet with multiple bullets under `**Active GitHub repos:**` (plural), one per repo, each formatted as `` `GitHub/[repo-subfolder]` — short description ``. In section 3, pluralize the heading to `### 3. GitHub repos — READ/WRITE (if applicable)` and replace only the opening sentence(s) that name a single repo folder with an enumerated list of the repos (path + description each) — **every other word of section 3 stays exactly as the template has it**, including the "READ/WRITE" designation, the full "Commit & push workflow" subsection (the Reads-vs-Writes split, the classic-PAT Mechanics bullets — PAT location, the no-token-leak per-URL auth header command, the `git config user.email`/`user.name` identity setup, the shallow-clone-to-`/tmp` note, the plain-text commit-authoring rule), the "GitHub Desktop is no longer in the loop" line, the "Consult team-shared memory at session start" paragraph, and the "Never write to `.git/` files" line. **Never downgrade a multi-repo project to READ-ONLY or drop the Commit & push workflow content** — the template's own closing sentence on this section ("the same READ/WRITE posture applies to every listed repo subfolder") already establishes that multi-repo projects get full read/write + commit/push on every listed repo, identical to the single-repo case; this step only ever expands the repo *enumeration*, never the write posture.
- The `[KANBAN_SLUG]` placeholder in the *Project Setup* block's `Kanban project tag(s):` line:
  - **one slug:** substitute `#project/[KANBAN_SLUG]` (e.g. `#project/moxywolf-plugins`).
  - **multiple slugs:** write them comma-separated, each wrapped in backticks as `` `#project/<slug>` `` (e.g. `` `#project/sams`, `#project/ghl` ``).
  - **none:** write `none`.

If the project's Active Taskade subfolder is `none` (vault-only project), replace section 1's heading and body to point at `MoxyWolf Vault/Projects/[PROJECT_NAME]/` instead of `Taskade/[TASKADE_SUBFOLDER]/`, and update the *File Write Path — MANDATORY OVERRIDE* section to reference the vault path. Note that the numbered subfolder structure may not exist in the vault project folder; flag this for the user to create manually if they want it.

### Step 3: Save the filled instructions

**This step only runs if Step 0 confirmed it's safe** — either no existing instructions were found, or the user explicitly chose "Regenerate it from scratch anyway" after the overwrite warning. Never reach this step by falling through from "Inputs to collect" without Step 0 having cleared it.

Write the result to the project's Project Hub:

- Taskade-based project: `Taskade/[TASKADE_SUBFOLDER]/00 – Project Hub/cowork-project-instructions.md`
- Vault-only project: `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md`

If the `00 – Project Hub` folder doesn't exist, create it first via bash. Add a frontmatter block at the top of the saved file:

```yaml
---
title: Cowork Project Instructions — [PROJECT_NAME]
date: [today's date in YYYY-MM-DD]
type: reference
status: active
template_source: _Templates/Cowork Project Instructions Template.md
---
```

The frontmatter is for the saved file only.

### Step 3.5: Compose the loader stub (what goes into Cowork settings)

**Do NOT paste the full instructions into Cowork's settings.** The full file on disk (Step 3) is the single source of truth; the Cowork → Settings → Project Instructions field gets a thin **loader stub** that points at it. This kills the paste-drift failure mode where the embedded copy and the on-disk file fall out of sync (the on-disk file gets edited, the embedded paste never does). The stub carries only what must be in-context *before the first tool call* and can't wait for a file read: the mounts, the file-write-path override, and the imperative to read the full file + team-shared memory first.

**The stub skeleton lives in the vault, not in this skill.** Read it from the canonical spec:

`MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/project-instructions-loader-stub.md`

Use section 1 (Taskade-based projects) or section 2 (vault-only projects). Substitute `<PROJECT_NAME>` and `<SUBFOLDER>` with this project's values; everything else is constant. Sourcing the skeleton from the vault means a change to the stub format (or a new team-wide rule) is a vault edit + a `/refresh-project-instructions` run per project — never a plugin update. If the spec file is missing, stop and tell the user rather than inventing a skeleton; that file is authoritative.

### Step 4: Display the loader stub for copy-paste

Display the **loader stub** (NOT the full instructions) in the chat as a fenced markdown code block. Above the code block, write:

> Copy this into the Project Instructions field of your Cowork **[PROJECT_NAME]** project (Cowork → Settings → Project Instructions). It's a thin pointer — the full instructions live in the file below and are read at session start, so you paste this once and never have to re-paste when the instructions change.

After the code block, link to the saved full file using a `computer://` link so the user can open and edit the source of truth.

If the user has not yet mounted all three standard roots in this Cowork project, also remind them to add any missing roots before the new instructions take effect (on-computer: Cowork → Folders; in the cloud: the **Add folder** button in the Claude desktop app).

## Output

- Full instructions saved to the project's `00 – Project Hub/cowork-project-instructions.md` (the single source of truth)
- The thin **loader stub** displayed in chat as a code block (this is what gets pasted into Cowork settings)
- Computer-link to the saved full file
- A reminder to mount any missing standard roots (MoxyWolf Vault, GitHub, Taskade) — on-computer via Cowork → Folders, in the cloud via the desktop app's **Add folder** button
- Concise note about anything that was deferred or skipped during input gathering

## Routing of shared knowledge

The template (and therefore the filled-in instructions) directs all shared-knowledge writes to the MoxyWolf Vault under `_Shared Knowledge/`. This is intentional and load-bearing for the obsidian-update workflow: when end-of-session memory extraction runs, it expects shared knowledge to live in the vault. Do not modify this routing in the filled-in output.

If the user explicitly asks to override this routing for a specific project, save the override as an addendum at the bottom of the filled-in instructions (under a `## Project-Specific Overrides` heading) rather than altering the canonical routing rules.

## Edge cases

- **Active Taskade subfolder doesn't exist yet.** Normally impossible because the user picks an existing folder via the native Finder picker. Only happens in the free-text fallback path; in that case ask the user whether to create the folder (with the standard numbered subfolder structure) or whether they'll create it manually. Don't proceed with saving until the folder exists.
- **GitHub repo subfolder doesn't exist locally.** Normally impossible via the picker. Only happens via the "Type a custom name" fallback — accept the name and flag it in the output. The user may be planning to clone the repo. Don't block on it.
- **User dismisses the Finder picker (on-computer) or declines the chip menu (cloud).** Treat as "skip" — fall back to the AskUserQuestion free-text path for that one input and continue.
- **One of the three standard roots isn't mounted.** Generate the instructions anyway, and surface the missing mount as an action item at the end of the chat reply.
- **Template missing or out of date.** If the template is missing or the user wants a fresh template, point them at the most recent working instantiation (e.g., Nexus's `00 – Project Hub/cowork-project-instructions.md`) as a reference; do not invent a new template structure on the fly.
- **Repo count says 0 but the user mentions code work.** Politely surface the discrepancy: "You said no GitHub repos but mentioned engineering work. Want to add a repo subfolder now?" Don't insist; the user may keep code elsewhere.
- **Multiple repos with overlapping concerns.** Section 3 lists each repo with its description. Don't try to merge them; let the user keep the distinction.

## Notes

- The plugin reads from the vault but writes to the project's Taskade (or vault Projects) folder — never to the vault's `_Templates/` directory itself.
- When the project name has spaces or special casing (e.g., "Frontier Founder"), preserve that casing in the output. Use kebab-case only for filenames if needed.
- The Active Taskade subfolder name often matches the project name but doesn't have to — preserve whatever capitalization the actual folder uses.
- The displayed code block can be long. That's expected — the user is going to paste it whole.
