---
description: The MoxyWolf coding loop — design doc first, build one item against it (or amend the doc with approval), push to a feature branch and pull back, cross-tool review until clean, hand off to the named human for merge, record the merge before marking done
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, AskUserQuestion, Agent
argument-hint: [--builder claude|codex] [--repo <path>] [item-id | what to build ...]
---

Every piece of coding at MoxyWolf goes through this loop (rule set by Dorian 2026-09-11, canonical in `Taskade/_Shared Files/_shared-memory/`). It exists so that code follows a written design, the design is amended before the code drifts from it, every push lands on the remote and back in the local clone, and nothing is called done until the other tool has reviewed it clean.

```
create/reuse the authorized feature branch before any commit
   ↓
DESIGN.md exists and covers the ask?
   no  → draft the doc or the amendment → Dorian approves → commit the doc → then code
   yes ↓
build the item on a feature branch, against its acceptance criteria
   ↓
commit → push → verify ls-remote → pull back into the local clone
   ↓
/gstack-peer-review (the other tool) → fix → push → pull back → re-verify   (bounded)
   ↓ clean
prepare revision-bound handoff → named human merges in GitHub → record-release verifies merge
   ↓
mark done through a separate authorized branch/PR → mirror to Taskade
   ↓
next item, only when asked
```

Raw slash-command arguments: `$ARGUMENTS`

## Step 0: Refuse to recurse, resolve the repo

If `GSTACK_PEER_REVIEW_SESSION` is set, this is a reviewer session: stop. Resolve the repo from `--repo`, else the project's declared GitHub repo(s) in `cowork-project-instructions.md`. `--builder` defaults to `claude`; pass `codex` when Codex is doing the building.

Before any DESIGN.md or E2E write/commit, create `build/<item-id>-<slug>` from up-to-date `main`, or reuse the existing authorized feature branch for this item. If the item ID is not known yet, use a descriptive feature branch name and retain it throughout the loop. Never commit these prerequisites on main or another protected branch. Keep approved design, E2E, implementation, and fix commits on this same branch through review and human merge; do not restart from main in Step 3.

## Step 1: The design document

`DESIGN.md` at the repo root is canonical; `Taskade/<project>/06 – Engineering/DESIGN-<repo>.md` is a mirror, rewritten on every doc commit. Template: `references/design-doc-template.md`.

- **Missing:** do not write code. Run `/gstack-design-doc` (drafts the document, publishes it as an editable artifact, and on **Mark approved** writes it to the repo and Taskade, commits on the Step 0 feature branch, pushes, pulls back). For anything larger than one item, run `/gstack-plan-review` on the draft first. Then continue.
- **Present:** read it in full. Match `$ARGUMENTS` to an item by ID or by meaning.

## Step 2: The gate: covered, or amend first

- **Covered** (an item exists, its acceptance criteria describe the ask, no constraint forbids it, and its **Links this item introduces** column is filled in): proceed to Step 3 with that item. An item that introduces state and declares no links is not covered yet; amend it first. Derive the list from what this change adds, never by copying another item's: a new identifier, cache, retained handle, resume point, or declaration of what a handler reads or writes is a link, and each one is a place the record will hold a name where a reader assumes a relationship.
- **Not covered, or in conflict** (no item; the ask contradicts a settled decision; the criteria are too vague to test): draft the amendment as a diff to `DESIGN.md`: a new item with acceptance criteria, or a changed constraint with the reason, plus a line in the Amendments log. Ask via AskUserQuestion: approve / edit / decline (for a larger edit, reopen the `/gstack-design-doc` editor instead). On approve (or after edits), commit the doc alone on the Step 0 feature branch (`design: <item-id> <title>`), push, pull back, mirror, then proceed. On decline, stop and say what was declined; no code.

Never silently widen an item to fit the ask, and never code the uncovered part "while we're here". The doc moves first.

## Step 3: Build the item

**E2E gate first (Vercel-deployed repos).** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/endform_workflow.py" preflight --repo <path>`, once per repository, before the first item. It answers locally, with no network, whether the gate can actually run here, and it names every condition it examined. It catches the topology defects that otherwise surface as a red check several minutes after a push: the workflow running from a directory that is not the Playwright project root, a tsconfig the test project extends resolving outside that root or through a workspace package the remote runner must also receive, and the `secrets.*` names the workflow references. It exits non-zero on any failed condition **and on any condition it could not examine**, because skipped is not passed (EV-001); `n/a` marks a condition that does not apply to this repo and is not a gap. Fix what it names before pushing. Until preflight is green, a red E2E check is a setup defect, not a code defect, and the loop does not treat it as one. `check` remains the narrow "is the workflow file there" probe. If preflight reports the workflow absent and the repo deploys on Vercel (look the project up with the Vercel connector's `list_projects`, matching the repo; ask the user only when nothing matches), write it: `endform_workflow.py ensure --repo <path> --project <vercel-project-name>` (template `references/endform-e2e.yml`; the install step follows the repo's lockfile), then commit it alone as `ci: add Endform e2e workflow`, push, verify, pull back (Step 4) before any feature code. A repo with no Vercel project gets no workflow; record that under the design doc's constraints so the check is not repeated. If the repo has no Playwright suite (no `package.json` or no `playwright.config.*`), run `endform_workflow.py scaffold --repo <path> --title-regex "/<home page title>/"`: it adds `package.json` (devDependency `@playwright/test` only), `playwright.config.ts` reading `BASE_URL`, and `e2e/smoke.spec.ts`, and runs `npm install` under `NODE_ENV=development` (the team machines export `NODE_ENV=production`, which silently drops devDependencies and writes a lockfile `npm ci` rejects). Verify locally before pushing: serve the site, then `BASE_URL=<url> ./node_modules/.bin/playwright test`; the repo's binary, never `npx playwright`, which resolves a global package that is not `@playwright/test`. The scaffold commit goes with the workflow commit, before feature code. A repo that already has a suite is not necessarily covered: a spec that skips itself when its backing service is absent (a live SAMS, a database) proves nothing on a preview, so a deploy smoke spec (`/` returns 200 with the expected title and no page errors) is required alongside it. `ensure` reads the env var the repo's `playwright.config` uses for `baseURL` and exports the preview URL under that name; a pnpm repo must carry `"packageManager": "pnpm@<version>"` in `package.json` or `pnpm/action-setup` fails with "No pnpm version is specified" (`ensure` refuses until it is there). Local verification of a Next app needs its `.env.local`; when that is not available the preview run on the PR is the verification, and the commit says so instead of claiming a local pass.

**The repo's own harness suites, if it has any (Vercel or not).** Endform exercises the browser against a preview; it says nothing about the API and the database underneath. A repo carrying `tests/container/run.sh` has a pinned Docker stack for exactly that, and it is the cheapest real evidence available: `tests/container/run.sh <suite>` builds PostgreSQL, PostgREST and Node at pinned versions, mounts both repositories read-only, clones them inside, and tears the cluster down. Run every suite the item touches.

**Run it through the macOS shell, not `device_bash`.** `device_bash` is a Linux VM on the user's machine and cannot see Docker Desktop or the macOS toolchain; a session that concludes "Docker is unavailable" from that shell has looked in the wrong place. Use Desktop Commander (`start_process`), which is a real macOS zsh. Two things it needs: `PATH` must start with `/Applications/Xcode.app/Contents/Developer/usr/bin` because `/usr/bin/git` is a license-gated shim that fails every git call with an Xcode licence message, and the runner needs both repositories checked out as siblings (`--oc <path>` otherwise). Launch it with `nohup … > /tmp/<suite>.log 2>&1 &` and poll; a first run builds the image and outlasts any single call's timeout.

**The record is the evidence, not the exit code.** Each run writes `tests/container/results/<suite>-<timestamp>/run-record.json` with `pass_lines`, `fail_lines`, `skips`, both commit ids, the pinned image versions, and the harness's teardown proof. Quote those counts into the review packet's `tests.results`. A record showing `pass_lines: 0`, or skips where the item's criteria live, has examined nothing and is not a green gate - the same rule as a `0 passed` Endform run (EV-001). A suite that skips because a prerequisite is genuinely absent reports SKIPPED; the runner's exit code 3 says so distinctly from 0.

**Expect it to fail the first time on the harness, not the code.** These suites drift: a hardcoded package manager, a dead default branch ref, a migration that grants nothing. Fix the harness in its own commit, say so in the message, and re-run - a suite nobody can start has been protecting nothing, and that is the finding.

Reuse the Step 0 feature branch, including its approved design and E2E commits. Set the item's status to `building` in `DESIGN.md` (this commit rides with the code). Build only what the item's acceptance criteria require; ponytail applies. Run the tests that demonstrate the criteria and keep the exact commands and results; they go into the review packet. Exercise the user's workflow, not just the helpers, and note which. For a Vercel-deployed repo the user's workflow is the Playwright suite run by Endform against the branch's preview deployment: a web acceptance criterion names the spec that proves it (`e2e/<area>.spec.ts: <test title>`), Step 4 opens the pull request on the first push (`gh pr create --base main`, draft is fine) and updates it on every push after; Endform runs the suite against the preview deployment and reports the result as a **Vercel check on the PR** with a link to the full run. A run that reports `0 passed` is not a green gate, whatever the check says: a suite whose specs all skip themselves because their backing service is absent has examined nothing, and a check that passes work it did not do is worse than no check (EV-001). Read the counts, not only the colour. Read it with `gh pr checks <number>` when `gh` is installed, otherwise the GitHub API: `GET /repos/{owner}/{repo}/commits/{sha}/check-runs` for the `e2e` check-run and `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` (follow the redirect with `curl -sL`; the job log prints `Deployment ready: <preview url>`, the per-test lines, `N passed`, and `Results of this suite run: <endform.dev url>`). Those two, check state and suite-run URL, are the `tests.results` evidence. **There is no Endform connector and none is needed**: Endform runs inside the workflow; a session that goes looking for an Endform tool or a "disposable target" has misread this step. Local `npx playwright test` is fine while iterating; it is not the evidence.

## Step 4: Commit, push, pull back

Claude authors the commit (plain text, Summary + Description). The agent-accessible vault PAT must lack authority to merge or push to protected targets; the named human Release Owner’s merge credentials remain outside agent access. Use only credentials constrained to the authorized feature-branch and PR work. Then, every time, in this order (substitute the retained branch name if Step 0 used a descriptive name):

```bash
git push origin build/<item-id>-<slug>          # PAT over a per-URL header, never in the URL or echoed
git ls-remote origin refs/heads/build/<item-id>-<slug>   # must equal git rev-parse HEAD
```

On the first push of the branch, open the pull request (`gh pr create --base main --title … --body …` when `gh` is installed; otherwise `POST /repos/{owner}/{repo}/pulls` with the vault PAT as a Bearer token) so the Endform check has somewhere to report. Then pull back into the user's local clone (`~/Documents/GitHub/<repo>`): if the work happened there, `git status -sb` shows level; if it happened in a sandbox clone, `git fetch origin && git checkout build/<item-id>-<slug> && git pull --ff-only` there via Desktop Commander. Report the SHA on remote and local. A push that is not verified and pulled back is not done.

## Step 5: Review loop until clean

Run `/gstack-peer-review --builder <tool>` with the packet built from the design doc: `outcome` = the item, `acceptance_criteria` = the item's criteria verbatim, `exclusions` = the doc's Constraints and settled decisions, `tests` = Step 3's commands and results, `release_owner` = the accountable human's GitHub login, one `{path, base=main, head=branch HEAD}` pair per repo. Follow that command's loop: substantiate, fix in scope, commit, **push and pull back (Step 4) after every fix commit**, disposition, next round.

Exit only on `no_blocking_findings` or `fixes_verified`, and, for a Vercel-deployed repo, a green Endform check on the PR at the final head (`gh pr checks` shows it passing, with the run link). `rounds_exhausted` → present the escalation and stop; the item stays `review`. `review_unavailable`, `model_below_floor`, and the other non-pass outcomes → report them as such and stop; do not merge on an unreviewed item.

## Step 6: Human release handoff, then record completion

Routine feature-branch commits, pushes, and PR preparation remain authorized. Never auto-merge or push to a protected branch. After Step 5 passes, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/peer_review.py" release <review-id>
```

**Say which checks actually gate the merge.** A workflow that runs is not a gate: until its check is required on the protected branch, a red suite merges as easily as a green one, and the team believes it is covered because the run exists. Before reporting `ready_for_human_release`, run:

```bash
GITHUB_TOKEN=<vault PAT, this call only> python3 "${CLAUDE_PLUGIN_ROOT}/scripts/repo_gates.py" check --repo <path>
```

It lists the check-runs the protected branch actually produced and what it requires. **Exit 3 means required checks are not available on this repository's plan at all** - a private repository on a free plan cannot have them, GitHub says so in the message rather than the status, and no credential changes it. On such a repository say so in the handoff and say what follows: the merge is unprotected, GitHub will not refuse a red head, and the only gate is this loop's own refusal - so do not report `ready_for_human_release` while any suite is red or has examined nothing. Never call a suite a gate on a repository that cannot require it. **Reading branch protection needs admin rights the agent token is deliberately not given** (GOVERNANCE.md), so expect `UNREADABLE (HTTP 403)`, and report that as what it is: not evidence that nothing is required, and not evidence that anything is. Include the observed check names in the handoff so the Release Owner can confirm in Settings > Branches which of them gate. Configuring them is their act, not the agent's; `repo_gates.py ensure --require "<context>"` exists for when an admin token is supplied, preserves every other protection setting, and never removes a context or relaxes protection. Never present a suite as a gate on the strength of a green run alone.

This revalidates the review and requires clean local HEADs matching the reviewed commits. It writes `release.json` and intentionally exits nonzero as `awaiting_human_release`; it never merges or accepts approval flags. Report `ready_for_human_release` with the PR URL, review ID, exact heads, and named Release Owner. The item stays `review`.

The named human merges the exact reviewed head in GitHub under their own login. Do not use their merge credential on their behalf. After they merge, record each repository's GitHub merge:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/peer_review.py" record-release <review-id> --repo <path> --pr <number>
```

The recorder requires the exact reviewed head and the named human's GitHub `User` identity. Only after every repository's merge is recorded may the item be marked `done` with the review ID and merge SHA. Make that administrative DESIGN.md update through a separate authorized branch/PR, with its own applicable review and human merge, never a direct main push. Mirror the committed design to Taskade and pull back as in Step 4. Changed implementation requires a new review and handoff.

These are governance controls, not an OS security sandbox: local review files are agent-writable. Human merge credentials must remain outside agent authority and protected-branch enforcement is configured externally. See [GOVERNANCE.md](../GOVERNANCE.md).

## Step 7: Report, then stop

```
BUILD LOOP
══════════
Repo:      {path}   Item: {id} {title}
Design:    {covered | amended (approved) | created}
Branch:    build/{id}-{slug} → {PR URL}
Release:   {ready_for_human_release | human_merge_recorded}   Owner: {GitHub login}
Pushed:    remote {sha} == local {sha}   (pulled back: yes)
Review:    {review-id}  {builder} → {reviewer}  {rounds}/{max}  {outcome}   Model: {model}
Tests:     {commands, results, through which path}
E2E:       {Endform run URL + pass/fail on final head | not a Vercel repo | workflow added this loop}
Verified:  {what was exercised, and how}
Unverified:{what was not, and why}
Next item: {next planned item id, or "none in DESIGN.md"}
```

Move to the next item only when the user says so. One item per loop keeps the review packet small and the design doc honest.
