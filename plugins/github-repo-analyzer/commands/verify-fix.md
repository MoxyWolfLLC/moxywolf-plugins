---
description: Verify whether closed GitHub issues were actually fixed with code changes
argument-hint: <github-url> --issue <number> [--batch] [--reopen]
---

Verify whether closed issue(s) for the repository at $1 were actually fixed with code changes, or merely closed without remediation.

## Steps

1. **Parse the repo URL** from `$ARGUMENTS`. Extract the owner and repo name. Check for flags:
   - `--issue <number>`: Verify a specific closed issue (REQUIRED unless `--batch` is set)
   - `--batch`: Verify ALL closed security-labeled issues in the repository instead of a single issue
   - `--reopen`: After verification, reopen any issue confirmed unfixed and post the verification report as a comment

2. **Load the skill and references:**
   - Read the skill file at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/SKILL.md` to load the verify-fix workflow
   - Read the fix patterns catalog at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/fix-patterns.md`
   - Read the verification report template at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/verify-fix-template.md`

3. **Identify target issues:**
   - If `--issue <number>`: fetch that single issue via `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}"`.
   - If `--batch`: fetch all closed security-labeled issues via the native GitHub MCP `list_issues` with `state: "closed"` and label filter, or via `gh api "/repos/${OWNER}/${REPO}/issues?state=closed&labels=security&per_page=100" --paginate`.
   - For each target issue, verify it is in a closed state. If the issue is open, skip it with a note.

4. **BEGIN VERIFICATION LOOP — for each target issue:**

   **4a. Fetch issue metadata:**
   - Full issue body, labels, state, closer, and closure timestamp: `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}"`.
   - All comments via native GitHub MCP `get_issue_comments`.
   - Issue timeline (linked PRs, commits, close events) via `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}/timeline" --paginate` — this is the most useful endpoint for closure auditing because it merges PR links, commit references, and close events into one stream.
   - Record: who closed it, when, linked PRs (count), linked commits (count), comments at closure time.

   **4b. Extract affected file paths — three-tier fallback:**
   - **Tier 1 — Explicit:** Scan issue body and comments for file paths, code blocks, backtick-quoted paths
   - **Tier 2 — Keyword inference:** Map domain terms from labels/title to likely file locations
   - **Tier 3 — Schema/config scan:** `gh api "/repos/${OWNER}/${REPO}/git/trees/${BRANCH}?recursive=1"` for the full file tree, then narrow to plausible config/route/schema files.
   - Present discovered files and ask for confirmation (skip confirmation in `--batch` mode).

   **4c. Fetch current source code:**
   - `gh api "/repos/${OWNER}/${REPO}/contents/${PATH}"` returns base64; decode with `jq -r .content | base64 -d`.
   - For batch verification, consider cloning once at the start (`gh repo clone "${OWNER}/${REPO}" /tmp/verify-$$`) and `Read`-ing files locally — fewer API calls, faster.

   **4d. Match to fix patterns catalog:**
   - Identify the CWE class from the issue body, labels, and title
   - Look up the corresponding fix pattern from `references/fix-patterns.md`
   - Determine what a proper fix WOULD look like for this vulnerability class

   **4e. Compare actual code vs. expected fix:**
   - Scan the current source code for evidence that the fix pattern was applied:
     - Validation functions, sanitization calls, authorization guards, allowlists, etc.
   - Check whether the specific vulnerable code described in the issue has been modified
   - Search the broader codebase for any new utility/helper that implements the fix pattern

   **4f. Determine verdict:**
   - **FIXED** — Code changes found that address the vulnerability. Link the specific commit/PR if discoverable.
   - **PARTIALLY FIXED** — Some aspects addressed but gaps remain. Document what was fixed and what wasn't.
   - **UNFIXED** — No code changes found. Vulnerable code is in the same state as when the issue was opened.
   - **INCONCLUSIVE** — Unable to determine (e.g., file paths changed, code reorganized, insufficient evidence).

   **4g. Assess closure context:**
   - Was this part of a mass-closure event? (multiple issues closed within 24 hours by same user)
   - Were there any comments explaining the closure rationale?
   - Is there a "false positive" or "won't fix" justification in the comments?

   **4h. Generate verification report:**
   - Use the template from `references/verify-fix-template.md`
   - Fill all sections: TLDR, Closure Metadata, Evidence (current code state), Security Classification, Recommended Fix (from fix-patterns), Actual vs. Recommended Comparison, Closure Context, Risk Assessment
   - Include a TLDR section at the top with the verdict

   **4i. Handle `--reopen` flag (if set and verdict is UNFIXED or PARTIALLY FIXED):**
   - Present the verification report to the user.
   - Ask for confirmation: "Should I reopen issue #{number} and post this report as a comment?"
   - If confirmed:
     - Post the report as a comment: `gh issue comment ${NUMBER} --repo "${OWNER}/${REPO}" --body-file /tmp/report-${NUMBER}.md`.
     - Reopen the issue: `gh issue reopen ${NUMBER} --repo "${OWNER}/${REPO}"`.
   - If declined: save the report locally only.

5. **LOOP BACK** to Step 4 for the next issue (in `--batch` mode). Repeat until all target issues are processed.

6. **Compile summary:**
   - Single-issue mode: Save as `{repo-name}-verify-fix-{issue-number}.md`
   - Batch mode: Save individual reports plus a summary as `{repo-name}-verify-fix-audit.md` containing:
     - Issue-by-issue verdicts table
     - Mass-closure pattern analysis (if detected)
     - Statistics: total verified, fixed, partially fixed, unfixed, inconclusive
     - Prioritized list of issues that need reopening

## Verdict Definitions

| Verdict | Criteria | Action |
|---------|----------|--------|
| **FIXED** | Code changes found that address the vulnerability described in the issue | No action needed — confirm closure was justified |
| **PARTIALLY FIXED** | Some code changes found but gaps remain | Flag for additional remediation |
| **UNFIXED** | No relevant code changes found; vulnerable code is unchanged | Recommend reopening with verification report |
| **INCONCLUSIVE** | Cannot determine fix status (reorganized code, missing files, etc.) | Flag for manual review |
