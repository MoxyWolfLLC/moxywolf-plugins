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

- **Missing:** do not write code. Run `/gstack-design-doc` (drafts the document, publishes it as an editable artifact, and on **Mark approved** writes it to the repo and Taskade, commits, pushes, pulls back). For anything larger than one item, run `/gstack-plan-review` on the draft first. Then continue.
- **Present:** read it in full. Match `$ARGUMENTS` to an item by ID or by meaning.

## Step 2: The gate: covered, or amend first

- **Covered** (an item exists, its acceptance criteria describe the ask, no constraint forbids it): proceed to Step 3 with that item.
- **Not covered, or in conflict** (no item; the ask contradicts a settled decision; the criteria are too vague to test): draft the amendment as a diff to `DESIGN.md`: a new item with acceptance criteria, or a changed constraint with the reason, plus a line in the Amendments log. Ask via AskUserQuestion: approve / edit / decline (for a larger edit, reopen the `/gstack-design-doc` editor instead). On approve (or after edits), commit the doc alone (`design: <item-id> <title>`), push, pull back, mirror, then proceed. On decline, stop and say what was declined; no code.

Never silently widen an item to fit the ask, and never code the uncovered part "while we're here". The doc moves first.

## Step 3: Build the item

**E2E gate first (Vercel-deployed repos).** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/endform_workflow.py" check --repo <path>`. If it prints `missing` and the repo deploys on Vercel (look the project up with the Vercel connector's `list_projects`, matching the repo; ask the user only when nothing matches), write it: `endform_workflow.py ensure --repo <path> --project <vercel-project-name>` (template `references/endform-e2e.yml`; the install step follows the repo's lockfile), then commit it alone as `ci: add Endform e2e workflow`, push, verify, pull back (Step 4) before any feature code. A repo with no Vercel project gets no workflow; record that under the design doc's constraints so the check is not repeated. If the repo has no Playwright suite (no `package.json` or no `playwright.config.*`), run `endform_workflow.py scaffold --repo <path> --title-regex "/<home page title>/"`: it adds `package.json` (devDependency `@playwright/test` only), `playwright.config.ts` reading `BASE_URL`, and `e2e/smoke.spec.ts`, and runs `npm install` under `NODE_ENV=development` (the team machines export `NODE_ENV=production`, which silently drops devDependencies and writes a lockfile `npm ci` rejects). Verify locally before pushing: serve the site, then `BASE_URL=<url> ./node_modules/.bin/playwright test`; the repo's binary, never `npx playwright`, which resolves a global package that is not `@playwright/test`. The scaffold commit goes with the workflow commit, before feature code. A repo that already has a suite is not necessarily covered: a spec that skips itself when its backing service is absent (a live SAMS, a database) proves nothing on a preview, so a deploy smoke spec (`/` returns 200 with the expected title and no page errors) is required alongside it. `ensure` reads the env var the repo's `playwright.config` uses for `baseURL` and exports the preview URL under that name; a pnpm repo must carry `"packageManager": "pnpm@<version>"` in `package.json` or `pnpm/action-setup` fails with "No pnpm version is specified" (`ensure` refuses until it is there). Local verification of a Next app needs its `.env.local`; when that is not available the preview run on the PR is the verification, and the commit says so instead of claiming a local pass.

Branch `build/<item-id>-<slug>` from up-to-date `main`. Set the item's status to `building` in `DESIGN.md` (this commit rides with the code). Build only what the item's acceptance criteria require; ponytail applies. Run the tests that demonstrate the criteria and keep the exact commands and results; they go into the review packet. Exercise the user's workflow, not just the helpers, and note which. For a Vercel-deployed repo the user's workflow is the Playwright suite run by Endform against the branch's preview deployment: a web acceptance criterion names the spec that proves it (`e2e/<area>.spec.ts: <test title>`), Step 4 opens the pull request on the first push (`gh pr create --base main`, draft is fine) and updates it on every push after; Endform runs the suite against the preview deployment and reports the result as a **Vercel check on the PR** with a link to the full run. Read it with `gh pr checks <number>` when `gh` is installed, otherwise the GitHub API: `GET /repos/{owner}/{repo}/commits/{sha}/check-runs` for the `e2e` check-run and `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` (follow the redirect with `curl -sL`; the job log prints `Deployment ready: <preview url>`, the per-test lines, `N passed`, and `Results of this suite run: <endform.dev url>`). Those two, check state and suite-run URL, are the `tests.results` evidence. **There is no Endform connector and none is needed**: Endform runs inside the workflow; a session that goes looking for an Endform tool or a "disposable target" has misread this step. Local `npx playwright test` is fine while iterating; it is not the evidence.

## Step 4: Commit, push, pull back

Claude authors the commit (plain text, Summary + Description). Then, every time, in this order:

```bash
git push origin build/<item-id>-<slug>          # PAT over a per-URL header, never in the URL or echoed
git ls-remote origin refs/heads/build/<item-id>-<slug>   # must equal git rev-parse HEAD
```

On the first push of the branch, open the pull request (`gh pr create --base main --title … --body …` when `gh` is installed; otherwise `POST /repos/{owner}/{repo}/pulls` with the vault PAT as a Bearer token) so the Endform check has somewhere to report. Then pull back into the user's local clone (`~/Documents/GitHub/<repo>`): if the work happened there, `git status -sb` shows level; if it happened in a sandbox clone, `git fetch origin && git checkout build/<item-id>-<slug> && git pull --ff-only` there via Desktop Commander. Report the SHA on remote and local. A push that is not verified and pulled back is not done.

## Step 5: Review loop until clean

Run `/gstack-peer-review --builder <tool>` with the packet built from the design doc: `outcome` = the item, `acceptance_criteria` = the item's criteria verbatim, `exclusions` = the doc's Constraints and settled decisions, `tests` = Step 3's commands and results, one `{path, base=main, head=branch HEAD}` pair per repo. Follow that command's loop: substantiate, fix in scope, commit, **push and pull back (Step 4) after every fix commit**, disposition, next round.

Exit only on `no_blocking_findings` or `fixes_verified`, and, for a Vercel-deployed repo, a green Endform check on the PR at the final head (`gh pr checks` shows it passing, with the run link). `rounds_exhausted` → present the escalation and stop; the item stays `review`. `review_unavailable`, `model_below_floor`, and the other non-pass outcomes → report them as such and stop; do not merge on an unreviewed item.

## Step 6: Merge, mark done, mirror

Merge to `main` through the pull request (`gh pr ready` then `gh pr merge --squash` or the repo's convention); push; pull back. Set the item to `done` with the review ID and merge SHA in `DESIGN.md`, add the Amendments-log line if the build changed anything in the doc, commit (`design: <item-id> done`), push, pull back, mirror to Taskade. Delete the feature branch on both ends.

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
E2E:       {Endform run URL + pass/fail on final head | not a Vercel repo | workflow added this loop}
Verified:  {what was exercised, and how}
Unverified:{what was not, and why}
Next item: {next planned item id, or "none in DESIGN.md"}
```

Move to the next item only when the user says so. One item per loop keeps the review packet small and the design doc honest.
