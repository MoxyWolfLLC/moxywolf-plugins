---
description: Test, review, and prepare PR for shipping
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: [branch-name]
---

Ship pipeline: run tests, review code, prepare PR. Adapted from gstack's `/ship` methodology.

Read the gstack-execution skill for context.

## Pre-Flight

1. Check git status — working tree must be clean. If dirty, offer to commit or stash.
2. Identify current branch and base branch.
3. Run `git fetch origin` to get latest base.
4. Check for merge conflicts with base. If conflicts exist, report them and stop.

## Step 1: Merge Base

Run `git merge origin/{base-branch}` to incorporate latest changes. If conflicts arise, report them for manual resolution.

## Step 2: Run Tests

Detect test framework:
- `package.json` scripts → `npm test` or `bun test`
- `pytest.ini` / `pyproject.toml` → `pytest`
- `Gemfile` → `bundle exec rspec`
- `go.mod` → `go test ./...`

Run the test suite. Classify failures:
- **In-branch failures** (tests that pass on base but fail here) → BLOCKING
- **Pre-existing failures** (tests that also fail on base) → NON-BLOCKING, triage separately

If blocking failures exist, report them with file:line and stop. The branch isn't ready to ship.

## Step 3: Coverage Audit

Trace code paths introduced by this branch's diff. For each untested path, either:
- Generate a test (with user approval)
- Flag it as a known gap in the PR description

## Step 4: Pre-Landing Review

Run the `/gstack-review` checklist against this branch. If CRITICAL findings exist, report them and stop.

## Step 5: Prepare PR

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
Coverage: {new paths tested}/{total new paths}
PR: {URL or "ready to create manually"}
Status: SHIPPED | BLOCKED (reason)
```
