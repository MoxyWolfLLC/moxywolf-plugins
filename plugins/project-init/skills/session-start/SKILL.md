---
name: session-start
description: This skill should be used when the user says "start a session for [project]", "resume [project]", "load [project] context", "/session-start", "open [project] in Cowork", "pick up where I left off on [project]", or any request to begin or resume work on an existing MoxyWolf project. It assumes the project has already been initialized via /init-project (i.e. has a saved cowork-project-instructions.md in its `00 – Project Hub/`). It mounts the three standard MoxyWolf roots, reads the project's saved Project Instructions, and surfaces a briefing — project-scoped tasks, recent decisions, open PRs/issues — so the session can pick up immediately.
---

# Session Start

Start or resume a Cowork session for an existing MoxyWolf project. Mount the three standard roots (MoxyWolf Vault, GitHub, Taskade) for this session, read the project's saved Project Instructions to learn the active Taskade subfolder and GitHub repo(s), then surface a focused briefing — project-scoped P0/P1 tasks, recent decisions, open GitHub PRs and issues — so the user can dive straight into work.

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

## Folder access — works online (cloud) or offline (on-computer)

Cowork runs either **online** (in the cloud — the `mcp__remote-devices__*` bridge is present) or **offline** (on the user's computer via the desktop app — folders are on the local filesystem). Folder access differs, and you may not know the mode up front. **Do not hard-depend on any one mount tool.** Detect each capability by whether its tool is present, and always keep a filesystem-probe fallback that works in both modes. These three steps govern every mount/pick below.

**Step A — detect which roots are available (mode-agnostic).** For each standard root, decide available vs missing using the first method that works:

1. If `mcp__remote-devices__get_device_info` is present (online), call it — `connectedFolders` is the authoritative mounted-path list; match each root by exact-path / prefix.
2. Otherwise (offline), **probe the path directly** — list the root with whatever filesystem tool is available (`ls`/Read on-computer, `mcp__remote-devices__device_list_dir` online). A successful listing = available; an error/empty = missing.

The probe in (2) is the universal fallback: it never depends on a mount tool existing, so it works in either mode even if tool names change.

**Step B — get a missing root mounted (auto-mount first, ask only as fallback).**

- **Online (cloud): auto-mount is the default action, not a fallback.** If `mcp__remote-devices__device_request_folder_access` is present, proactively request every currently-missing root in **one call** — pass each missing root's exact absolute path together, so the user gets a single approval dialog covering all of them rather than one prompt per root. The folder-access request *is* the mount; there is no separate "wait for the user to add it themselves" step to try first. After the call returns, re-run Step A to confirm what got granted.
- **On-computer: unchanged.** If `mcp__cowork__request_cowork_directory` is present, call it with the explicit `path` to mount/grant the root (no-op if already mounted). This remains the on-computer picker/mount path.
- **Fallback only.** Fall back to asking the user manually — in one line, the exact path — **only** when: the remote-devices bridge is unavailable (no connected device, or the tool isn't present) on cloud, or `request_cowork_directory` isn't present on-computer, or the user declined the request/approval. The manual ask is: **online**, the **Add folder** button in the Claude desktop app; **offline**, **Cowork → Folders → Add**. Then pause. A system-reminder announces newly connected folders (online) or re-probe the path (offline), then re-run Step A to confirm before continuing.
- If the user doesn't add it even after the fallback prompt, mark it "not mounted", continue with whatever is available, and skip briefing sections that read from the missing root with a one-line note.

**Step C — pick a subfolder under an available root (used by project-init).**

- If `mcp__cowork__request_cowork_directory` is present, call it with **no `path`** for the native picker; take the basename of the resolved path.
- Otherwise, enumerate the root's immediate subfolders (`device_list_dir` online, `ls` offline) and present them via `AskUserQuestion` chips (the user clicks, never types), with a free-text "Other" fallback.

Net: nothing here requires `request_cowork_directory`; it's used when present and cleanly replaced by detect-probe-and-prompt when absent — so the same skill runs online or offline.

## Steps

### Step 1: Resolve which project

This skill **never shows a project picker.** It resolves the project on its own and announces the choice in the briefing. The only question the skill asks the user is Step 6's "what to focus on first", scoped to the resolved project.

**Resolution order** (use the first method that yields a project):

1. **Explicit slash-command argument** — if the user invoked `/session-start SAMS`, use `SAMS`. An explicit argument always wins. If the argument doesn't match any project folder, don't ask — fall through to method 3 and note the unmatched argument in the briefing.

2. **Auto-detect from the launch directory.** Inspect the user's selected folder path from the session environment and parse it for a project segment:
   - `.../MoxyWolf Vault/Projects/<NAME>/...` → project is `<NAME>`
   - `.../Taskade/<NAME>/...` where `<NAME>` is not `_Shared Files` → project is `<NAME>`
   - `.../GitHub/<REPO>/...` → look up which project's `cowork-project-instructions.md` lists `<REPO>` as an active GitHub repo; if exactly one match, use it.

   If a project is detected, announce it in the briefing as: *"Detected project from launch directory: **<NAME>**."* and skip to Step 2. This is the expected path — Dorian's normal workflow is to launch Cowork from inside a project folder, so auto-detection should succeed most of the time.

3. **Fall back to auto-selecting the most recently active project** when neither (1) nor (2) produces a project (e.g. the user launched from the vault root, the Taskade root, or the GitHub root). Do **not** ask the user which project — pick it automatically:

   a. Scan `Taskade/` for subfolders that contain `00 – Project Hub/cowork-project-instructions.md`. Also scan `MoxyWolf Vault/Projects/` for vault-only projects with the same file.

   b. Rank the candidates by recency of activity: the most recent `cowork-session-handoff.md` (`session_ended` timestamp) wins; for projects with no handoff, fall back to the modification time of the saved instructions file. The single most-recently-active project is the resolved project.

   c. Use that project directly and skip to Step 2. Announce it at the top of the briefing as: *"No project named in the launch path — resumed the most recently active project: **<NAME>** (last session <DATE>). Say another project name if you meant a different one."* That announced line is the only correction surface — there is no picker, and the user switches projects simply by naming a different one.

### Step 2: Read the saved Project Instructions

Read `Taskade/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` (or `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` for vault-only projects).

Parse to extract:

- The active Taskade subfolder name (or `none` for vault-only projects)
- The list of active GitHub repos (subfolder names + descriptions) — there may be 0, 1, or many
- The **Kanban project tag(s)** — the `Kanban project tag(s):` bullet in the *Project Setup* block. This declares the project's scope on the team Jira board (MOXY); a `#project/<slug>` value maps to the Jira label `project-<slug>`. It may be `none` (the project has no board presence) or absent entirely (instructions written before this field existed). Record whichever you find — Step 4b uses it to scope the board query.
- Any `## Project-Specific Overrides` block at the bottom

If the file doesn't exist, abort with: *"No saved Project Instructions found for [PROJECT_NAME]. Run `/init-project` first to set this project up."*

### Step 3: Ensure the three standard roots are available

Follow the **Folder access — works online (cloud) or offline (on-computer)** convention above; it's mode-agnostic, so the same procedure runs either way.

1. **Detect (Step A).** For each of the three roots, decide available vs missing — `get_device_info` → `connectedFolders` when that tool is present (online), else probe the path directly by listing it (offline). Don't assume the mode; use whichever detector is available.
2. **Get missing roots mounted (Step B) — auto-mount first.** **Online:** if `mcp__remote-devices__device_request_folder_access` is present, proactively request every missing root's exact absolute path in **one call** (single approval dialog for all of them) — this is the default action, not something to try only after asking the user. **On-computer:** if `mcp__cowork__request_cowork_directory` is present, mount each missing root with it (explicit `path`, parallel calls so approval prompts surface together, no-op if already mounted). **Fallback only** — if neither tool is present, or the user declines the request/approval: list the still-missing roots and ask the user, in one line, to add each exact path (**online:** the desktop app's **Add folder** button; **offline:** Cowork → Folders → Add), then wait for the system-reminder (online) or re-probe (offline) and re-run detection.

Record each root in the briefing as "already available", "newly mounted (auto-requested)", or — if still missing after the fallback prompt — "not mounted (user hasn't added it)". If a root stays unavailable, note it and continue with whichever roots are present; a missing root just means the sections that read from it are skipped with a one-line note (e.g. a missing Taskade root means the team-shared `_shared-memory/INDEX.md` can't be read).

### Step 4: Gather context (parallel)

In a single message, run these reads in parallel:

a. **Session handoff (highest priority)** — Read `[project]/00 – Project Hub/cowork-session-handoff.md` if it exists. This is the canonical handoff written by `/session-end` at the end of the previous session. Parse the handoff's frontmatter (`session_ended` timestamp, plus the optional `author` and `for` fields — both lowercase first names) and these sections:
   - `## What landed this session`
   - `## Open work, in priority order`
   - `## Commit & push state` (older handoffs may title this `## Uncommitted code` — accept either)
   - `## Procedural reminders for next-Claude`
   - `## Suggested opening line`

   The `author` and `for` frontmatter fields tell next-Claude who wrote the handoff and whether it was an explicit baton-pass. They're optional — older handoffs predating the auto-write feature won't have them; treat the absence as "author unknown, no explicit baton-pass" and surface that in the briefing rather than guessing.

   Stale-detection: if `session_ended` is more than 14 days old, flag the handoff as **stale** in the briefing. The user may want to skip the suggested-opening-line and focus on current kanban state instead.

   If the file doesn't exist, that's fine — older projects predating `/session-end` won't have one. Note "no handoff from previous session" in the briefing and continue.

b. **Project task board (project-scoped, dual-source)** — Surface only tasks that belong to *this* project. There are two sources; both are scoped to the resolved project, and the skill never shows another project's tasks.

   **Source 1 — the project's own backlog folder (primary).** Scan the project's `04 – Backlog & Sprints/` folder (its `Backlog/`, `Sprint Logs/`, and `Retrospectives/` subfolders) for `.md` files. These are inherently project-scoped — they live inside the project's own directory. For each file, read its frontmatter `title` and `status`; skip anything marked `done` or `archived`. Surface the open ones as the project's backlog. If the folder is empty or missing, note "no project backlog files" and move on — many projects keep granular tasks only in the kanban.

   **Source 2 — the team Jira board (MOXY), strictly filtered (backup).** The single canonical task board is Jira, project **MOXY** (https://moxywolf.atlassian.net) — shared by *every* MoxyWolf project. Query it via the Atlassian MCP (`searchJiraIssuesUsingJql`), scoped to this project's Jira **label**, and pull — from the in-scope issues only — the top 3 P0, top 3 P1, and all Blocked/Waiting items. (There is no vault `KANBAN_VIEW.md` anymore — it was retired 2026-07-16 when Jira became the single board.)

   **Strict project filter (fail-closed).** First decide the in-scope Jira **label** set. Jira labels can't contain `/`, so a `#project/<slug>` scope maps to the label `project-<slug>`:

   1. **Field declared** — Step 2 found a `Kanban project tag(s)` value that is not `none`: that value is authoritative. Map each `#project/<slug>` token to the label `project-<slug>`; the label set is exactly those.
   2. **Field is `none`** — the project has no board presence. Surface zero items, note "this project declares no kanban scope", and skip the board query entirely. Do not filter, do not fall back.
   3. **Field absent** — older instructions: derive an *inferred* label set from the kebab-cased project name plus each active GitHub repo subfolder name (each as `project-<slug>`). Filter on that inferred set, and add this one-line warning to the briefing: *"Kanban Scope not declared — filtered MOXY on inferred labels [list]. Add a `Kanban project tag(s):` line to `00 – Project Hub/cowork-project-instructions.md` (or rerun `/init-project`) to make this exact."*

   Then run the query, fail-closed on the label: `project = MOXY AND labels IN (<label-set>) AND statusCategory != Done ORDER BY priority DESC, updated DESC`. An issue is **in scope only if** it carries a project label in the set. Every other issue is out of scope — including issues with no `project-*` label at all (cross-cutting, personal, or company-wide) and issues whose project label isn't in the set. When in doubt, exclude.

   The skill must **never** widen to "show the whole board" because the filter matched nothing. An empty result is a correct result — if zero issues match, write "no MOXY issues labeled for this project" on one line and move on. A shared board can only be made safe by showing an issue *only* when it is positively labeled for the resolved project; that fail-closed rule is the entire point of this step. If the Atlassian MCP isn't connected, note that and rely on the project's backlog folder (Source 1).

c. **Project map (MOC) + recent decision records** — The durable front door to a project is its vault Map of Content; the recent-DR list is the fresh slice on top of it. Read both.

   First resolve the **vault project folder**, which may not match the Taskade project name (e.g. Taskade `Team Plugins` ↔ vault `Moxywolf Plugins`). If a `project-memory.md` pointer exists in the Taskade `00 – Project Hub/`, read it — it names the vault folder and the MOC path. Otherwise match `MoxyWolf Vault/Projects/<name>/` by best name match. Record the mapping if it isn't 1:1.

   - **MOC index** — read `MoxyWolf Vault/Projects/[VAULT_PROJECT]/00-Hub/[VAULT_PROJECT] Index.md`. Capture what the project is (one line) plus its newest 2-3 Recent Activity entries. If it doesn't exist yet, note "no MOC index yet" and continue.
   - **Recent decision records** — search the vault project folder (and the Taskade subfolder) for `DR-*.md` modified in the last 14 days; title + one-line summary from each frontmatter, cap at 5 items.

d. **Open GitHub PRs and recent issues** — For each repo in the parsed GitHub repo list, query the GitHub MCP for:
   - All open PRs (title, author, last-updated)
   - Top 5 most-recently-updated open issues (title, author, last-updated)

e. **Shared team services probe** — Check the team-shared OpenRouter API key file at `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/openrouter.env`. The canonical setup is documented in [[DR-010-openrouter-key-vault-file]]; it's read by Council, research-pipeline, and product-orchestrator. Surface one of four states in the briefing:

   - **resolved** — file exists and contains a value matching `^sk-or-v1-` (real OpenRouter key prefix). Status line: `OpenRouter key: ✓ resolved from vault`.
   - **placeholder** — file exists but the value is still `REPLACE_WITH_TEAM_SHARED_KEY` (or any value containing `REPLACE` / `PLACEHOLDER`). Status line: `OpenRouter key: ⚠ placeholder — ask Dorian for the real key`.
   - **malformed** — file exists but no `OPENROUTER_API_KEY=` line, or value doesn't match the `sk-or-v1-` prefix. Status line: `OpenRouter key: ⚠ file present but key value looks wrong — check format`.
   - **missing** — file doesn't exist at the canonical path. Status line: `OpenRouter key: ⚠ not found — see DR-010 for the canonical location`.

   Probe implementation (run via `mcp__workspace__bash`, in the same parallel batch as the other reads):

   ```bash
   KEY_FILE="$(ls -d /sessions/*/mnt/MoxyWolf\ Vault 2>/dev/null | head -1)/_Shared Knowledge/Agents and Plugins/openrouter.env"
   if [ ! -f "$KEY_FILE" ]; then
       echo "missing"
   else
       VAL=$(grep -E '^[[:space:]]*(export[[:space:]]+)?OPENROUTER_API_KEY[[:space:]]*=' "$KEY_FILE" \
           | head -1 | sed -E 's/^[^=]*=[[:space:]]*//; s/^["'\'']//; s/["'\'']$//')
       if [ -z "$VAL" ]; then echo "malformed"
       elif echo "$VAL" | grep -qE 'REPLACE|PLACEHOLDER'; then echo "placeholder"
       elif echo "$VAL" | grep -qE '^sk-or-v1-'; then echo "resolved"
       else echo "malformed"; fi
   fi
   ```

   This probe is project-agnostic — the OpenRouter key is shared infrastructure that every council/research-pipeline/product-orchestrator invocation needs regardless of which project session-start was called from. The cost is one bash call and a few-line file read, so run it unconditionally. The probe doesn't read or echo the key value itself — only the resolution status — so the key never leaves the file via the briefing.

f. **Team-shared behavioral memory (authoritative rules)** — Read `Taskade/_Shared Files/_shared-memory/INDEX.md` and parse the entries listed under each section heading. This directory is the canonical source for cross-plugin team-wide behavioral rules — Git/commit workflow, lockfile precautions, plain-text commit-message formatting, the moxywolf-plugins-Claude-authors-commit rule, etc. Surface the parsed entries in the Step 5 briefing under a "Team-shared rules in effect" section so next-Claude SEES the rules rather than having to remember to look them up.

   **Then cross-check the handoff's "Procedural reminders for next-Claude" section against the INDEX.** If a handoff reminder cites a memory file that is no longer in the INDEX (renamed, deleted) or whose current content reverses the reminder's claim, mark the reminder as **STALE** in the briefing's reminders list. Stale-handoff propagation is the documented failure mode this step exists to prevent — see the 2026-06-02 case where a 2026-05-21 handoff carried forward a "never run git from the sandbox" reminder that had actually been reversed on 2026-05-20, and next-session Claude (me) followed the stale handoff instead of the current memory. The cross-check at session-start is the second line of defense — `/session-end` does its own cross-check at write time (belt and braces).

   If the INDEX file is missing entirely at the expected path, capture that as a critical anomaly in the briefing's Shared services line and treat the project's procedural-reminder situation as undefined — but still proceed with the rest of the briefing.

g. **Behavioural hook liveness** — Some plugins inject a ruleset at session start rather than waiting to be invoked: gstack-execution's verification discipline, and ponytail's restraint layer. They are the rules most likely to fail *silently*, because a hook that does not fire looks exactly like one that fired and had nothing to say.

   This probe costs nothing — it reads what is already in this session's context, not the disk:

   - **active** — a `VERIFICATION DISCIPLINE ACTIVE — gstack-execution` block was injected into this session's context at start. Status line: `Verification discipline: ✓ active`.
   - **not loaded** — no such block is present. Status line: `Verification discipline: ⚠ NOT LOADED — the checks are not in context`, followed by the remedy below.

   Report what is actually in context. Do not infer the hook fired because the plugin is installed, because a previous session had it, or because it ought to — that inference is the exact failure this line exists to catch, and a false ✓ is worse than no line at all, because it retires the question.

   On **not loaded**, call `ListPlugins` and report gstack-execution's installed version in the same line, then give the remedy in order:
   1. Version below 0.8.0 — the hook does not exist in that build. Refresh the marketplace (Cowork's **Refresh**, or `claude plugin marketplace update moxywolf-plugins`).
   2. Version 0.8.0 or above and still nothing — the `hooks` key was added to a plugin that was already installed without one, which may need a reinstall to register: `claude plugin uninstall gstack-execution` then `claude plugin install gstack-execution@moxywolf-plugins`.
   3. Still nothing after a reinstall and a fresh session — the wiring is wrong, not the install. Say so plainly rather than repeating the remedy.

   Apply the same two states to ponytail if its activation block is present or absent; report it on the same line. Never gate the session on either — this is a heads-up, exactly like the OpenRouter probe.

If any of these sources is unavailable (file missing, MCP not connected), capture the failure in the briefing instead of aborting. The remaining context is still useful.

### Step 5: Display the briefing

Output a structured briefing in chat. The session handoff (if found) is the most important section because it's the freshest source of state. Use these sections in this order:

```
## Project: [PROJECT_NAME]

**Mounted folders**
- MoxyWolf Vault — [already mounted | newly mounted (auto-requested) | newly mounted (user added)]
- GitHub — [already mounted | newly mounted (auto-requested) | newly mounted (user added)]
- Taskade — [already mounted | newly mounted (auto-requested) | newly mounted (user added)]

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

[If the handoff lists local commits awaiting push:]
**Commits awaiting push**
- [N] commits recorded in last session's handoff. If any are still unpushed, push them via sandbox `git` + the classic PAT. See handoff §Commit & push state.

[If no handoff was found, replace the four sections above with:]
**Last session left off with**
- _(no handoff from previous session — pre-`/session-end` project, or first session)_

**Project tasks** (scoped to [PROJECT_NAME])
- Backlog files: [open files in 04 – Backlog & Sprints/, or "none"]
- MOXY P0: …   (Jira board filtered to label project-[slug])
- MOXY P1: …
- MOXY Blocked/Waiting: …
[If the Kanban Scope was inferred or undeclared, add the one-line "Kanban Scope not declared…" warning here. If it is `none`, write "this project declares no kanban scope" here instead.]

**Project map** (durable front door)
- MOC: `Projects/[VAULT_PROJECT]/00-Hub/[VAULT_PROJECT] Index.md` — [one line: what the project is, from the MOC]. Open it for the full map, or ask "what do we know about X here?" for a scoped memory search.
- Latest: [top 2-3 Recent Activity highlights from the MOC]
[If a Taskade `project-memory.md` pointer was found, add: "- Memory pointer present in the Taskade hub."]
[If no MOC index exists yet, replace this whole block with: "**Project map** — _(no MOC index yet in 00-Hub — consider creating one)_".]

**Recent decisions (last 14 days)**
- [DR title] — [one-line summary]

**Open PRs**
- [repo-name]
  - #123 [title] — [author], updated [date]

**Open issues** (top 5 per repo)
- [repo-name]
  - #456 [title] — [author], updated [date]

**Team-shared rules in effect** (from `Taskade/_Shared Files/_shared-memory/INDEX.md`)
- [Rule title from INDEX] ([filename]) — [the INDEX entry's one-line summary]
- ...
[If the file at the canonical path is missing, write: "⚠ Team-shared memory INDEX not found at expected path — procedural-rule situation is undefined for this session." and skip the rules list.]

**Procedural reminders from handoff** (cross-checked against team-shared memory)
- ✓ [Handoff reminder verbatim] — aligned with current `[file]`
- ⚠ STALE [Handoff reminder verbatim] — cites `[file]` which doesn't exist in current INDEX (or has been revised); follow `[current-file]` instead
- ✓ session-specific: [Handoff reminder verbatim]
[If the handoff had no procedural-reminders section, write "_(none in handoff)_".]
[If the team-shared INDEX is missing, downgrade this section to plain transcription of the handoff's reminders, with a note that no cross-check was possible.]

**Shared services**
- OpenRouter key: [✓ resolved from vault | ⚠ placeholder — ask Dorian for the real key | ⚠ file present but key value looks wrong — check format | ⚠ not found — see DR-010 for the canonical location]
- Verification discipline: [✓ active | ⚠ NOT LOADED — gstack-execution [version] — [remedy]]   ·   Ponytail: [✓ active | ⚠ not loaded]
```

Keep each line tight. This is a briefing, not a report.

If a section had no findings (e.g. "no DRs in last 14 days", "no open PRs in [repo]", "no kanban items tagged for this project"), say so on one line rather than omitting the section silently.

### Step 6: Ask what to work on first

End with a single AskUserQuestion: *"What do you want to focus on first?"* Every option must come from a **project-scoped** source — the handoff, the project's `04 – Backlog & Sprints/` folder, or the project-filtered kanban from Step 4b. Never offer a task that wasn't scoped to the resolved project. Pull options in this order of priority:

- The handoff's first open-work item (if a handoff was found and not stale)
- The handoff's second open-work item (if applicable)
- Top 1 P0 from the project-filtered kanban (if any, and not duplicating a handoff item); if there is no in-scope P0, use the top open backlog file or the top in-scope P1 instead
- "Just brief me — I'll decide"

Do not exceed 4 options total.

If the handoff was stale (>14 days old), drop the handoff items from the focus options and fall back to the project-filtered kanban and backlog folder only — stale handoffs probably don't reflect current priorities.

If no handoff was found, options pull from the project-scoped task board only:

- Top 1–2 in-scope P0 items (if any)
- Top 1–2 in-scope P1 items (if any)
- "Just brief me — I'll decide"
- "Something else" (free-text fallback)

## Output

- Three standard roots confirmed mounted (or, for any missing, the user prompted to Add folder / approve the mount per the Folder access convention)
- A structured briefing in chat covering the project's current state
- A focus question to start the work

## Edge cases

- **No saved Project Instructions for this project.** Stop and route to `/init-project`. Do not invent a config.
- **No `cowork-session-handoff.md` file.** Treat as "no previous handoff" and skip the handoff sections of the briefing. The task-board / DRs / GitHub MCP sections still surface project state. This is normal for projects predating `/session-end` or for a project's first session.
- **`cowork-session-handoff.md` is malformed (can't parse expected sections).** Surface the parse failure in the briefing as a one-line warning ("handoff file at [path] couldn't be parsed; falling back to task-board / DRs / GitHub state"). Continue with the rest of the briefing. Don't try to fix the file — let the user reconcile it.
- **`cowork-session-handoff.md` is stale (`session_ended` > 14 days old).** Surface the staleness in the "Last session ended" line and drop the handoff's open-work items from the focus options in Step 6. The kanban is the more current source of priorities at that point.
- **One of the three standard roots isn't mounted.** Cloud: try `device_request_folder_access` first (auto-mount, single dialog for all missing roots) — only fall back to asking the user to click Add folder if the bridge is unavailable or they decline. On-computer: `request_cowork_directory` mounts it if present; otherwise ask the user. If it's still missing after the fallback attempt, note it in the briefing's "Mounted folders" section as "not mounted" and continue with whichever roots are available. Skip any briefing section that reads from the missing root, with a one-line note saying why.
- **GitHub MCP not connected.** Skip the open-PRs and open-issues sections, note that the GitHub MCP isn't available, and suggest connecting it.
- **Atlassian MCP not connected (can't reach the MOXY board).** Skip the Jira portion of the project-tasks section, note that the Atlassian connector isn't available, and continue with the project's backlog folder (Source 1).
- **Kanban Scope not declared in the Project Instructions.** Don't widen to the whole board. Derive inferred slugs from the kebab-cased project name and the GitHub repo names, filter strictly on those (Step 4b case 3), and add the "add a `Kanban project tag(s):` line" warning to the briefing. If the inferred set matches nothing, show "no kanban items tagged for this project" — still never show the unfiltered board.
- **Kanban Scope declared as `none`.** The project has no kanban presence. Surface zero kanban items with a one-line note; the project's `04 – Backlog & Sprints/` folder and the handoff carry the task state instead.
- **Project's `04 – Backlog & Sprints/` folder is empty or missing.** Normal — many projects track granular tasks only in the kanban. Note "no project backlog files" and rely on the project-filtered kanban.
- **Project name passed with slash command doesn't match any folder.** Don't show a picker. Fall back to Step 1 method 3 — auto-select the most recently active project — and note the unmatched argument in the briefing so the user can correct it by naming a project explicitly.
- **Vault-only project (no Taskade subfolder).** Read the Project Instructions from `MoxyWolf Vault/Projects/[PROJECT_NAME]/00 – Project Hub/cowork-project-instructions.md` instead. Look for the handoff and the `04 – Backlog & Sprints/` folder at the same vault path. Skip Taskade-subfolder references in the briefing.
- **Project Instructions file is malformed (can't parse the active Taskade subfolder or GitHub repo list).** Surface the parse failure to the user and ask them to either edit the file by hand or rerun `/init-project`. Don't proceed with a guessed config.
- **Verification discipline reports `NOT LOADED`.** Surface it and carry on — it is a heads-up, not a gate. But do not quietly drop the line on later sessions if it stays absent: a warning that decays into silence is how the original problem returns. The checks themselves live in `gstack-execution`'s `references/verification-checks.md`; if the hook cannot be made to fire, read that file directly rather than working without them.
- **OpenRouter key probe returns `placeholder` or `missing`.** Surface the warning in the Shared services line but do not block the session — most projects don't use OpenRouter on every task. If the user invokes anything that touches Council, research-pipeline, or product-orchestrator later, those skills do their own preflight check (`python3 plugins/council/scripts/openrouter_key.py --where`) and will halt with an actionable error then. The session-start briefing is a heads-up, not a gate.
- **OpenRouter key probe returns `resolved` but a council/research-pipeline/product-orchestrator skill still errors out later in the session.** The probe only verifies the file exists at the canonical path with a valid-looking value. It doesn't verify the key is actually accepted by OpenRouter (no network call — that would slow down session-start and cost tokens). If the resolved key gets rejected by OpenRouter (rotated, revoked), the user should ask Dorian to update `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/openrouter.env` per DR-010.

## Notes

- This skill complements `/init-project` and `/session-end`. `/init-project` configures a project once; `/session-end` writes the per-session handoff at the end of each session; `/session-start` reads that handoff to brief next-session Claude in one step.
- The briefing is intentionally short. Detailed exploration is a follow-up task within the session.
- The skill reads but does not write. It does not modify the kanban, the project instructions, the session handoff, or any decision records. End-of-session writing is `/session-end`'s job (project-scoped handoff) and `/obsidian-update`'s job (cross-project knowledge to vault).
- The team board is Jira project **MOXY** — a single board shared by every project (the vault `KANBAN_VIEW.md` was retired 2026-07-16). session-start only ever surfaces MOXY issues positively labeled `project-<slug>` for the resolved project — an unlabeled issue, or one labeled for a different project, is never shown. See Step 4b.
- The standard roots are constants. Don't ask the user to confirm which roots to mount — always mount the same three.
- The skill never shows a project picker. When the launch directory names a project (or an explicit argument is given) it uses that; otherwise it auto-resumes the most recently active project and announces the choice. The user switches projects by naming a different one — see Step 1. The only question the skill asks is Step 6's "what to focus on first", scoped to the resolved project.
- The handoff file path is fixed: `[project]/00 – Project Hub/cowork-session-handoff.md`. Don't fall back to other filenames (`continuation-prompt-*.md`, etc.) — those are free-form, written before this contract existed, and not parseable. If the user wants those surfaced too, they can ask explicitly.
