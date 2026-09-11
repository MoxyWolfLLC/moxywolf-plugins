---
description: Create or refresh a repo's DESIGN.md as an editable artifact; on approval it is written to the repo (canonical) and the Taskade project folder (mirror), committed, pushed, verified, and pulled back
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, AskUserQuestion, Artifact
argument-hint: [--repo <path>] [--taskade <project folder>] [--from <prd/spec paths ...>] [notes about the goal ...]
---

Produce the design document that `/gstack-build` gates on. Format and structure: `references/design-doc-template.md` (Goal, Constraints and settled decisions, Items with checkable acceptance criteria, Amendments log). The user edits it as an artifact and approves it there; nothing is written to disk until they do.

Raw slash-command arguments: `$ARGUMENTS`

## Step 1: Resolve both locations, mount what is missing

Two directories are required:

- **Repo** (canonical `DESIGN.md`): `--repo`, else the project's declared GitHub repo in `cowork-project-instructions.md`, else `~/Documents/GitHub/<repo>`.
- **Taskade project folder** (mirror at `06 – Engineering/DESIGN-<repo>.md`): `--taskade`, else the project's declared Taskade folder.

Check both against `get_device_info().connectedFolders` (or, on-computer, by probing the paths). For any that is not mounted, request it with `device_request_folder_access` in one call. If the request is unavailable or declined, ask the user for the directories with AskUserQuestion (free text is fine) and re-check. Do not proceed with only one of the two; the mirror is part of the contract.

## Step 2: Gather

Read, in this order, whatever exists: the current `DESIGN.md`; the repo README, manifests, and top-level tree; `--from` documents; the project's `02 – Product Strategy/` PRDs and `06 – Engineering/` specs; the team-shared INDEX rules that constrain this repo (commit workflow, version bumps, model floors, coding loop); recent decision records. The notes in `$ARGUMENTS` state the goal in the user's words and win over everything inferred.

## Step 3: Draft

Write the document to the template. Rules that make it usable by `/gstack-build`:

- Goal is one paragraph and says what "working" means to the user of the repo.
- Every constraint is a decision already made, stated so a reviewer cannot reopen it; cite the DR or date where one exists.
- Every item has numbered acceptance criteria that are checkable statements (a command and its expected result, a URL and what renders, a value and its expected value), not intentions. Items already in flight or done carry their status and review ID.
- The Amendments log gets a first line: created, by whom, pending approval.
- Refreshing an existing doc: keep every existing line unless the repo contradicts it; put what changed in the Amendments log.

## Step 4: Publish the editor

Fill `references/design-doc-editor.html`: `{{TITLE}}` → `<repo> Design Doc`; `{{STATE_JSON}}` → `{"repo","repoPath","taskadePath","markdown","approved":false,"savedAt":null}` as JSON with `<` escaped as `<`. Publish it with the Artifact tool, `capabilities: {"artifact": {}}`, favicon `📐`, label `Initial draft` (or `Refresh <date>`). Reuse the same file path (or pass the existing artifact's `url`) when refreshing so the URL stays stable.

Tell the user in one sentence what the page is and that **Mark approved** is what triggers the write. Then stop this turn.

## Step 5: On approval, write both copies on a feature branch

When the user says it is approved (or a republish notice arrives, or they ask you to check): `Artifact read` the page, parse the `design-state` JSON, and require `approved: true`; if it is false, say the page is saved but not approved and stop.

Then, in this order:

1. Before any write or commit, reuse the authorized feature branch supplied by `/gstack-build`. For standalone design work, create or reuse a design feature branch from up-to-date main. Never write or commit the design on main or another protected branch.
2. Write `markdown` to `<repo>/DESIGN.md` and to `<taskade>/06 – Engineering/DESIGN-<repo>.md` (create the folder if missing; note the en dash in `06 – Engineering`).
3. Commit the repo copy alone on that feature branch: `design: create DESIGN.md` or `design: refresh DESIGN.md (<what changed>)`, plain text, Claude-authored.
4. Push that feature branch with a vault PAT constrained to branch/PR work, without protected-target merge or push authority, over a per-URL header; verify `git ls-remote origin refs/heads/<branch>` equals `git rev-parse HEAD`; pull back into the local clone if the commit was made elsewhere.
5. Republish the editor once with `approved` still true and `savedAt` unchanged, so the page and the files agree.

Content approval authorizes saving the design, not its release. When called by `/gstack-build`, retain these commits on the same feature branch through implementation, peer review, and human merge; do not merge the design separately or restart the branch from main. For standalone design work, prepare a PR, complete the applicable peer review and revision-bound release handoff, and stop for the named human to merge in GitHub. Record that merge via `peer_review.py record-release` before claiming it landed. Human Release Owner credentials remain outside agent access.

## Step 6: Report

```
DESIGN DOC
══════════
Repo:     {path}  →  DESIGN.md @ {sha}  (remote == local: yes)
Branch:   {feature branch}  PR: {URL or pending creation}
Release:  {pending review | ready_for_human_release | human_merge_recorded}
Taskade:  {path}/06 – Engineering/DESIGN-{repo}.md
Artifact: {title}  version {n}  approved {savedAt}
Items:    {N planned, N building, N review, N done}
Next:     /gstack-build {first planned item id}
```
