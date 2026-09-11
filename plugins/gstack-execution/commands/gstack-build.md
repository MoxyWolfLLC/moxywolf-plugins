---
description: The MoxyWolf coding loop — design doc first, build one item against it (or amend the doc with approval), push to a feature branch and pull back, cross-tool review until clean, merge, mark the item done
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, AskUserQuestion, Agent
argument-hint: [--builder claude|codex] [--repo <path>] [item-id | what to build ...]
---

Every piece of coding at MoxyWolf goes through this loop (rule set by Dorian 2026-09-11, canonical in `Taskade/_Shared Files/_shared-memory/`). It exists so that code follows a written design, the design is amended before the code drifts from it, every push lands on the remote and back in the local clone, and nothing is called done until the other tool has reviewed it clean.

```
DESIGN.md exists and covers the ask?
   no  → draft the doc or the amendment → Dorian approves → commit the doc → then code
   yes ↓
build the item on a feature branch, against its acceptance criteria
   ↓
commit → push → verify ls-remote → pull back into the local clone
   ↓
/gstack-peer-review (the other tool) → fix → push → pull back → re-verify   (bounded)
   ↓ clean
merge to main → push → pull back → mark the item done in DESIGN.md (with the review ID) → mirror to Taskade
   ↓
next item, only when asked
```

Raw slash-command arguments: `$ARGUMENTS`

## Step 0: Refuse to recurse, resolve the repo

If `GSTACK_PEER_REVIEW_SESSION` is set, this is a reviewer session: stop. Resolve the repo from `--repo`, else the project's declared GitHub repo(s) in `cowork-project-instructions.md`. `--builder` defaults to `claude`; pass `codex` when Codex is doing the building.

## Step 1: The design document

`DESIGN.md` at the repo root is canonical; `Taskade/<project>/06 – Engineering/DESIGN-<repo>.md` is a mirror, rewritten on every doc commit. Template: `references/design-doc-template.md`.

- **Missing:** do not write code. Draft `DESIGN.md` from the ask and the codebase (goal, constraints and settled decisions, the first item with acceptance criteria). For anything larger than one item, run `/gstack-plan-review` on the draft. Present it, get approval via AskUserQuestion, commit it (`design: initial DESIGN.md`), push, pull back, mirror. Then continue.
- **Present:** read it in full. Match `$ARGUMENTS` to an item by ID or by meaning.

## Step 2: The gate: covered, or amend first

- **Covered** (an item exists, its acceptance criteria describe the ask, no constraint forbids it): proceed to Step 3 with that item.
- **Not covered, or in conflict** (no item; the ask contradicts a settled decision; the criteria are too vague to test): draft the amendment as a diff to `DESIGN.md`: a new item with acceptance criteria, or a changed constraint with the reason, plus a line in the Amendments log. Ask via AskUserQuestion: approve / edit / decline. On approve (or after edits), commit the doc alone (`design: <item-id> <title>`), push, pull back, mirror, then proceed. On decline, stop and say what was declined; no code.

Never silently widen an item to fit the ask, and never code the uncovered part "while we're here". The doc moves first.

## Step 3: Build the item

Branch `build/<item-id>-<slug>` from up-to-date `main`. Set the item's status to `building` in `DESIGN.md` (this commit rides with the code). Build only what the item's acceptance criteria require; ponytail applies. Run the tests that demonstrate the criteria and keep the exact commands and results; they go into the review packet. Exercise the user's workflow, not just the helpers, and note which.

## Step 4: Commit, push, pull back

Claude authors the commit (plain text, Summary + Description). Then, every time, in this order:

```bash
git push origin build/<item-id>-<slug>          # PAT over a per-URL header, never in the URL or echoed
git ls-remote origin refs/heads/build/<item-id>-<slug>   # must equal git rev-parse HEAD
```

Then pull back into the user's local clone (`~/Documents/GitHub/<repo>`): if the work happened there, `git status -sb` shows level; if it happened in a sandbox clone, `git fetch origin && git checkout build/<item-id>-<slug> && git pull --ff-only` there via Desktop Commander. Report the SHA on remote and local. A push that is not verified and pulled back is not done.

## Step 5: Review loop until clean

Run `/gstack-peer-review --builder <tool>` with the packet built from the design doc: `outcome` = the item, `acceptance_criteria` = the item's criteria verbatim, `exclusions` = the doc's Constraints and settled decisions, `tests` = Step 3's commands and results, one `{path, base=main, head=branch HEAD}` pair per repo. Follow that command's loop: substantiate, fix in scope, commit, **push and pull back (Step 4) after every fix commit**, disposition, next round.

Exit only on `no_blocking_findings` or `fixes_verified`. `rounds_exhausted` → present the escalation and stop; the item stays `review`. `review_unavailable`, `model_below_floor`, and the other non-pass outcomes → report them as such and stop; do not merge on an unreviewed item.

## Step 6: Merge, mark done, mirror

Merge to `main` the way the repo does it (fast-forward or `gh pr create` + merge when main is protected); push; pull back. Set the item to `done` with the review ID and merge SHA in `DESIGN.md`, add the Amendments-log line if the build changed anything in the doc, commit (`design: <item-id> done`), push, pull back, mirror to Taskade. Delete the feature branch on both ends.

## Step 7: Report, then stop

```
BUILD LOOP
══════════
Repo:      {path}   Item: {id} {title}
Design:    {covered | amended (approved) | created}
Branch:    build/{id}-{slug} → main @ {merge-sha}
Pushed:    remote {sha} == local {sha}   (pulled back: yes)
Review:    {review-id}  {builder} → {reviewer}  {rounds}/{max}  {outcome}   Model: {model}
Tests:     {commands, results, through which path}
Verified:  {what was exercised, and how}
Unverified:{what was not, and why}
Next item: {next planned item id, or "none in DESIGN.md"}
```

Move to the next item only when the user says so. One item per loop keeps the review packet small and the design doc honest.
