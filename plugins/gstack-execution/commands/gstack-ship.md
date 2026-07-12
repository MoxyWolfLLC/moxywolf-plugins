---
description: Test, review, and prepare PR for shipping
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: [branch-name]
---

Ship pipeline: run tests, review code, prepare PR. Adapted from gstack's `/ship` methodology. The isolated-worktree validation and the safe-fix/escalate contract are concept-ported from [no-mistakes](https://github.com/kunchenguid/no-mistakes) (MIT) — behaviors re-specified for this pipeline, no code vendored.

Read the gstack-execution skill for context.

## The Fix Contract (applies to Steps 2–4)

Every finding the pipeline produces is classified before anything is changed:

- **Safe mechanical fix** — auto-apply in the validation worktree, no interruption: formatting/lint corrections, unused imports, typos in comments or docs, dead code that this branch's own diff introduced, and trivially-wrong test assertions whose intended value is unambiguous from the diff. Log every auto-applied fix; all of them appear in the Ship Report.
- **Judgment call** — stop and ask the user: anything that changes behavior, API shape, data handling, dependencies, or architecture; anything ponytail rung 1 would question; and ALL findings touching validation, error handling, security, or accessibility (these are never auto-fixed, mirroring the restraint pre-pass rule). Present the finding, the proposed change, and wait for approval.

When in doubt, escalate. A wrongly-escalated mechanical fix costs one question; a wrongly-auto-applied judgment call ships a decision nobody made.

## Pre-Flight

1. Check git status — working tree must be clean. If dirty, offer to commit or stash.
2. Identify current branch and base branch.
3. Run `git fetch origin` to get latest base.
4. Check for merge conflicts with base. If conflicts exist, report them and stop.

## Step 1: Merge Base

Run `git merge origin/{base-branch}` to incorporate latest changes. If conflicts arise, report them for manual resolution.

## Step 1.5: Isolated Validation Worktree

Validation never runs against the user's working copy. Create a disposable worktree and run Steps 2–4 inside it:

```bash
git worktree add /tmp/gstack-ship-{branch-slug} {branch}
```

- Test artifacts, generated tests, auto-applied fixes, and review churn all land in the worktree — the user's checkout stays untouched throughout.
- Changes that survive the pipeline (auto-applied safe fixes, user-approved fixes, approved generated tests) are committed in the worktree on the same branch; because a worktree shares the repository, those commits are immediately on the branch — nothing to copy back.
- **Teardown always runs**, on success, failure, or user abort: `git worktree remove --force /tmp/gstack-ship-{branch-slug}` (then `git worktree prune`). Never leave a stale worktree behind.
- If `git worktree` is unavailable or fails (rare: very old git, exotic filesystem), say so and fall back to in-place validation — but then downgrade the Fix Contract to escalate-everything, since auto-fixing in the user's live checkout is exactly what the worktree exists to prevent.

## Step 2: Run Tests

Detect test framework:
- `package.json` scripts → `npm test` or `bun test`
- `pytest.ini` / `pyproject.toml` → `pytest`
- `Gemfile` → `bundle exec rspec`
- `go.mod` → `go test ./...`

Run the test suite. Classify failures:
- **In-branch failures** (tests that pass on base but fail here) → BLOCKING
- **Pre-existing failures** (tests that also fail on base) → NON-BLOCKING, triage separately

Apply the Fix Contract to in-branch failures: auto-fix the safe mechanical ones in the worktree and re-run the affected tests; escalate the rest. If blocking failures remain after that, report them with file:line and stop. The branch isn't ready to ship.

## Step 3: Coverage Audit

Trace code paths introduced by this branch's diff. For each untested path, either:
- Generate a test (with user approval)
- Flag it as a known gap in the PR description

## Step 3.5: Restraint Pre-Pass (ponytail)

Before reviewing, run `/ponytail-review` on the branch diff to strip over-built code, so the review and PR cover only what should exist. Apply the cuts the user approves. Never cut validation, error handling, security, or accessibility. If the diff is already lean, note it and move on.

## Step 4: Pre-Landing Review

Run the `/gstack-review` checklist against this branch. Route findings through the Fix Contract: safe mechanical ones are fixed in the worktree, judgment calls are escalated. If CRITICAL findings remain unresolved, report them and stop.

## Step 5: Prepare PR

**Gate:** Never auto-push to a protected branch and never auto-merge. A named human owns the merge; the pipeline prepares the PR and stops.

Build the PR:
- **Title:** Concise description of what this PR does (under 70 characters)
- **Body:** Summary of changes, test results, review findings, any known gaps
- **Labels:** Suggest appropriate labels based on files changed

Attempt to create the PR:
```bash
gh pr create --title "{title}" --body "{body}" --base {base-branch}
```

If `gh` CLI is not available:
1. Report that the PR is ready to create manually
2. Provide the title, body, and base branch
3. Provide the URL pattern: `https://github.com/{owner}/{repo}/compare/{base}...{branch}`

## Step 6: Summary

```
SHIP REPORT
═══════════
Branch: {branch} → {base}
Tests: {passed}/{total} ({N} pre-existing failures excluded)
Review: {N} critical, {N} info findings
Fixes: {N} auto-applied (listed below), {N} escalated ({N} approved, {N} declined)
Coverage: {new paths tested}/{total new paths}
Worktree: removed
PR: {URL or "ready to create manually"}
Status: SHIPPED | BLOCKED (reason)
```
