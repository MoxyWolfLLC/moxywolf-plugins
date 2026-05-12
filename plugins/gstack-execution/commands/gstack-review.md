---
description: Pre-landing code review with structural checklist
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: [branch-or-file-path]
---

Run a structured code review on the current branch's changes. Adapted from gstack's `/review` methodology.

Read the gstack-execution skill for context. Then read `references/review-checklist.md` for the full checklist.

## Execution Steps

### Step 0: Detect Environment
Run via Bash:
- `git rev-parse --abbrev-ref HEAD` to get current branch
- `git remote -v` to detect platform (GitHub/GitLab)
- Identify base branch (main/master/develop)
- If $ARGUMENTS contains a file path, scope review to that file

### Step 1: Check for Diff
Run `git diff --stat $(git merge-base HEAD origin/main)..HEAD` (adjust base branch as needed).
If no diff exists, report "Nothing to review — no changes detected on this branch" and stop.

### Step 2: Scope Drift Detection
If plan files exist (TODOS.md, .gstack/plans/, PR descriptions), cross-reference what was requested against what the diff delivers. Flag:
- Work done that wasn't in any plan (scope creep)
- Planned items not present in the diff (incomplete work)

### Step 3: Generate Full Diff
Run `git diff $(git merge-base HEAD origin/main)..HEAD` to get the complete diff.
For large diffs (>2000 lines), break into per-file analysis.

### Step 4: Two-Pass Review

**Pass 1 — CRITICAL (blocking):**
Apply the checklist from `references/review-checklist.md`. Focus on:
- SQL safety (raw queries, string interpolation in SQL)
- Race conditions (concurrent state mutation without locks)
- LLM trust boundaries (user input flowing to system prompts)
- Auth bypass (missing permission checks on new routes)
- Data loss (destructive operations without confirmation)
- Enum/switch completeness (unhandled cases)

**Pass 2 — INFORMATIONAL (non-blocking):**
- Side effects in unexpected places
- Magic numbers without constants
- Dead code introduced by the diff
- Test coverage gaps
- Frontend accessibility issues
- Performance concerns (N+1 queries, unnecessary re-renders)

### Step 5: Test Coverage Analysis
Trace every code path introduced by the diff. For each:
- Is there a test covering the happy path?
- Is there a test covering the error path?
- Are edge cases tested?

Map this as a coverage diagram showing tested vs untested paths.

### Step 6: Produce Findings

Format each finding as:
```
## [CRITICAL|INFO] Finding: {title}

**File:** {path}:{line}
**What:** {description of the issue}
**Why it matters:** {impact on the user or system}
**Fix:** {specific remediation with code example}
```

### Step 7: Summary

```
REVIEW SUMMARY
══════════════
Branch: {branch} → {base}
Files changed: {N}
Lines: +{added} -{removed}

CRITICAL: {N findings — must fix before merge}
INFO: {N findings — recommended improvements}

Ship readiness: {READY | NEEDS FIXES | BLOCKED}
```

Present all findings. Offer to auto-fix mechanical issues (missing null checks, unused imports, missing error handling) if the user approves.
