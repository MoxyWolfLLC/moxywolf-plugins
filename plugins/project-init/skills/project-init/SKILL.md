---
name: project-init
description: This skill should be used when the user says "set up a new project", "init a new project", "new Cowork project", "configure project instructions", "start a new project", "set up project", "/init-project", or any request to scaffold the Project Instructions for a fresh Cowork project. It assumes the three standard MoxyWolf roots (MoxyWolf Vault, GitHub, Taskade) are mounted in Cowork, then interactively gathers the active Taskade subfolder and active GitHub repo subfolder(s), and produces tailored Project Instructions following the MoxyWolf template, with shared-knowledge writes routed to the MoxyWolf Vault for end-of-session obsidian-updates.
---

# Project Init

Generate tailored Project Instructions for a new Cowork project. The MoxyWolf convention is that every Cowork project mounts the same three roots — MoxyWolf Vault, GitHub, and Taskade — and the Project Instructions just declare *which* subfolder of Taskade is the active project and *which* subfolder of GitHub is the active repo. Read the MoxyWolf template, gather per-project specifics through AskUserQuestion, substitute placeholders, save the filled instructions to the project's Project Hub folder, and display the result for the user to paste into Cowork's settings.

## When to use

Trigger when the user is starting a new Cowork project and needs Project Instructions configured. Common triggers:

- "set up a new project"
- "init a new project"
- "new Cowork project"
- "configure project instructions"
- "start a new project"
- "/init-project"

Also trigger if the user asks how to scaffold Project Instructions for an existing project they're re-organizing.

## Standard mounted roots

Every MoxyWolf Cowork project assumes these three roots are mounted in Cowork → Folders. The skill does not ask about them — they're constants:

1. **MoxyWolf Vault** — `/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/MoxyWolf Vault`
2. **GitHub** — `/Users/doriancougias/Documents/GitHub`
3. **Taskade** — `/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/MoxyWolf Shared Files/Taskade`

If the user mentions that one of these isn't mounted yet, remind them to add it via Cowork → Folders before the new Project Instructions can take effect, but proceed with generating the instructions anyway.

## Inputs to collect

**Folder selection rule — never ask the user to type a folder name.** Use the native Finder picker (`mcp__cowork__request_cowork_directory` called with **no `path` argument**) every time the skill needs to identify a subfolder under one of the standard mounted roots. The user clicks through Finder, picks the folder, and Cowork returns the resolved path — much faster and zero typos.

Gather inputs in this order, one decision at a time:

### 1. Project name

Ask via AskUserQuestion for the project name in kebab-case or original casing as the user prefers (e.g., "Nexus", "SAMS", "Frontier Founder", "STIGViewer"). Free-text via the "Other" option is fine here. This is the canonical project identifier and appears throughout the instructions.

(Tip: if the user has already picked the Taskade folder before answering this, default the suggested project name to the picked folder's basename — they can still override.)

### 2. Active Taskade subfolder — Finder picker

Do **not** ask the user to type the folder name. Instead:

a. First, ask via AskUserQuestion whether this project uses Taskade. Options:
   - **`Yes — pick the Taskade subfolder now`** (default)
   - **`No — vault-only project`** (the project will then write into `MoxyWolf Vault/Projects/[PROJECT_NAME]/` instead)

b. If "Yes": call `mcp__cowork__request_cowork_directory` with **no `path` argument** so the native macOS Finder picker opens. Tell the user in chat — just before the call — to navigate into the `MoxyWolf Shared Files/Taskade/` directory and pick the project's subfolder. When the tool returns, take the basename of the resolved path as `[TASKADE_SUBFOLDER]`. Confirm back: "Got it — using `Taskade/<basename>`."

c. If the picker is dismissed or returns nothing, fall back to AskUserQuestion with a free-text "type the folder name" option, and surface the issue in the final output.

The full path is always `Taskade/[TASKADE_SUBFOLDER]`.

### 3. GitHub repo count

Ask via AskUserQuestion: how many local GitHub repos under `GitHub/` does this project use? Options: `0`, `1`, `2`, `3 or more`.

### 4. GitHub repo subfolder(s) — Finder picker, one per repo

If repo count >= 1, do **not** ask the user to type repo names. For each repo:

a. Call `mcp__cowork__request_cowork_directory` with **no `path` argument** to open the native Finder picker. Before the call, prompt the user in chat: "Pick repo 1 of N — navigate into `~/Documents/GitHub/` and select the repo folder."

b. When the picker returns, take the basename of the resolved path as that repo's `[REPO_SUBFOLDER]`. Confirm back: "Got it — `GitHub/<basename>`."

c. After each repo is picked, ask via AskUserQuestion (separately) for a short one-line description (e.g., "Main service code", "Frontend app", "Marketing site") with a "Skip — use repo name only" option.

d. Repeat until all N repos are picked. If the user wants to add a repo that isn't yet cloned under `GitHub/`, offer a follow-up "Type a custom name" option after the picker is dismissed; accept the name as free text and flag in the final output that the repo subfolder doesn't exist locally yet.

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
  - **2+ repos:** in *Project Setup*, replace the `Active GitHub repo:` bullet with multiple bullets under `**Active GitHub repos:**` (plural), one per repo, each formatted as `` `GitHub/[repo-subfolder]` — short description ``. Update section 3's heading to "GitHub repos — READ-ONLY" and write its body as a list of repos with paths and descriptions, retaining the READ-ONLY rule for every repo.

If the project's Active Taskade subfolder is `none` (vault-only project), replace section 1's heading and body to point at `MoxyWolf Vault/Projects/[PROJECT_NAME]/` instead of `Taskade/[TASKADE_SUBFOLDER]/`, and update the *File Write Path — MANDATORY OVERRIDE* section to reference the vault path. Note that the numbered subfolder structure may not exist in the vault project folder; flag this for the user to create manually if they want it.

### Step 3: Save the filled instructions

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

The frontmatter is for the saved file only. The version pasted into Cowork's settings (displayed in chat) should NOT include this frontmatter, since Cowork's Project Instructions field is plain text.

### Step 4: Display the result for copy-paste

Display the filled-in Project Instructions in the chat as a fenced markdown code block. Above the code block, write:

> Copy this into the Project Instructions field of your Cowork **[PROJECT_NAME]** project. Cowork → Settings → Project Instructions.

After the code block, link to the saved file using a `computer://` link so the user can re-open it later.

If the user has not yet mounted all three standard roots in this Cowork project, also remind them to add any missing roots via Cowork → Folders before the new instructions take effect.

## Output

- File saved to the project's `00 – Project Hub/cowork-project-instructions.md`
- Filled-in Project Instructions displayed in chat as a code block
- Computer-link to the saved file
- A reminder to mount any missing standard roots (MoxyWolf Vault, GitHub, Taskade) in Cowork → Folders
- Concise note about anything that was deferred or skipped during input gathering

## Routing of shared knowledge

The template (and therefore the filled-in instructions) directs all shared-knowledge writes to the MoxyWolf Vault under `_Shared Knowledge/`. This is intentional and load-bearing for the obsidian-update workflow: when end-of-session memory extraction runs, it expects shared knowledge to live in the vault. Do not modify this routing in the filled-in output.

If the user explicitly asks to override this routing for a specific project, save the override as an addendum at the bottom of the filled-in instructions (under a `## Project-Specific Overrides` heading) rather than altering the canonical routing rules.

## Edge cases

- **Active Taskade subfolder doesn't exist yet.** Normally impossible because the user picks an existing folder via the native Finder picker. Only happens in the free-text fallback path; in that case ask the user whether to create the folder (with the standard numbered subfolder structure) or whether they'll create it manually. Don't proceed with saving until the folder exists.
- **GitHub repo subfolder doesn't exist locally.** Normally impossible via the picker. Only happens via the "Type a custom name" fallback — accept the name and flag it in the output. The user may be planning to clone the repo. Don't block on it.
- **User dismisses the Finder picker.** Treat as "skip" — fall back to the AskUserQuestion free-text path for that one input and continue.
- **One of the three standard roots isn't mounted.** Generate the instructions anyway, and surface the missing mount as an action item at the end of the chat reply.
- **Template missing or out of date.** If the template is missing or the user wants a fresh template, point them at the most recent working instantiation (e.g., Nexus's `00 – Project Hub/cowork-project-instructions.md`) as a reference; do not invent a new template structure on the fly.
- **Repo count says 0 but the user mentions code work.** Politely surface the discrepancy: "You said no GitHub repos but mentioned engineering work. Want to add a repo subfolder now?" Don't insist; the user may keep code elsewhere.
- **Multiple repos with overlapping concerns.** Section 3 lists each repo with its description. Don't try to merge them; let the user keep the distinction.

## Notes

- The plugin reads from the vault but writes to the project's Taskade (or vault Projects) folder — never to the vault's `_Templates/` directory itself.
- When the project name has spaces or special casing (e.g., "Frontier Founder"), preserve that casing in the output. Use kebab-case only for filenames if needed.
- The Active Taskade subfolder name often matches the project name but doesn't have to — preserve whatever capitalization the actual folder uses.
- The displayed code block can be long. That's expected — the user is going to paste it whole.
