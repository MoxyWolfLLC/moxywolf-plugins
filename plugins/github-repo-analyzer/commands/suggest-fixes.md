---
description: Suggest code fixes for GitHub issues one at a time with HITL approval
argument-hint: <github-url> [--issue <number>] [--security-only]
---

Analyze GitHub issues for the repository at $1 and generate code fix suggestions one issue at a time, with human-in-the-loop approval before advancing.

## Steps

1. **Parse the repo URL** from `$ARGUMENTS`. Extract the owner and repo name. Check for flags:
   - `--issue <number>`: Start with (or jump to) a specific issue number instead of the first in the queue
   - `--security-only`: Only process issues with a `security` label

2. **Load the skill and references:**
   - Read the skill file at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/SKILL.md` to load the fix suggestion workflow
   - Read the fix patterns catalog at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/fix-patterns.md`
   - Read the fix report template at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/fix-report-template.md`

3. **Fetch the issue queue** using the native GitHub MCP plus REST where needed:
   - Native GitHub MCP `list_issues` for the inventory of open and closed issues.
   - If `--security-only` is set, filter to security-labeled issues only.
   - Sort by priority: P0 first, then P1, P2, P3, then unlabeled.
   - Present the full queue to the user as a numbered list with issue #, title, state, and priority.
   - Ask the user: **"Which issue should we start with?"** (or begin at `--issue <number>` if specified).

4. **BEGIN HITL LOOP — one issue at a time:**

   For the selected issue:

   **4a. Fetch issue details:**
   - `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}"` for the full issue body, labels, and metadata.
   - Native GitHub MCP `get_issue_comments` for the comment thread (for context and pushback history).
   - Present a brief summary to the user: issue title, state, priority, core finding.

   **4b. Extract file paths — three-tier fallback:**
   - **Tier 1 — Explicit paths:** Scan the issue body and comments for file paths (e.g., `src/routes/billing.ts`, `lib/auth/guards.ts`). Look for code blocks, backtick-quoted paths, and path-like strings.
   - **Tier 2 — Keyword inference:** If no explicit paths are found, infer likely files from the issue title, labels, and body keywords. Map domain terms to common file locations:
     - "billing" → `**/billing/**`, `**/stripe/**`, `**/payment*`
     - "auth" / "authorization" → `**/auth/**`, `**/guard*`, `**/middleware/auth*`
     - "CORS" → `**/cors*`, `**/middleware*`, `**/config*`
     - "credential" / "password" / "secret" → `**/.env*`, `**/config*`, `**/auth*`
   - **Tier 3 — Schema/config scan:** If Tiers 1–2 yield nothing, use `gh api "/repos/${OWNER}/${REPO}/git/trees/${BRANCH}?recursive=1"` to list the repo's full file tree, then scan for configuration files, route definitions, and schema files that might contain the vulnerable code paths.
   - Present the discovered files to the user for confirmation before proceeding.

   **4c. Fetch source code:**
   - `gh api "/repos/${OWNER}/${REPO}/contents/${PATH}"` returns the file with its content base64-encoded — decode via `jq -r .content | base64 -d`.
   - For larger explorations, `gh repo clone "${OWNER}/${REPO}" /tmp/grep-$$` once and use `Read`/`Grep` against the local checkout.
   - If a file is too large to read whole, scan for function/class names mentioned in the issue and read those line ranges with `Read --offset/--limit`.

   **4d. Scan for existing patterns:**
   - Search the fetched code for instances where the same vulnerability class is already handled correctly elsewhere in the codebase
   - Example: if the issue is about missing authorization on a route, find other routes that DO have authorization guards and document the pattern
   - This becomes the "Existing Patterns in Codebase" section of the fix report

   **4e. Apply security reference catalog:**
   - Match the issue to CWE identifiers using `references/fix-patterns.md`
   - Pull the corresponding fix pattern template (guard pattern, validation pattern, encryption pattern, etc.)
   - Map to OWASP Top 10:2025, OWASP API Security 2023, OWASP Cheat Sheets, and NIST SP 800-53 controls
   - Adapt the generic fix pattern to the specific codebase's language, framework, and conventions

   **4f. Generate the fix report:**
   - Use the template from `references/fix-report-template.md`
   - Fill in all eight sections:
     1. Issue Header (number, title, state, priority, labels)
     2. Vulnerability Description (what's wrong, why it matters, blast radius)
     3. Security Classification (CWE, OWASP, NIST table)
     4. Existing Patterns in Codebase (where the fix pattern already works)
     5. Recommended Fix (actual code with inline comments)
     6. Why This Fix Works (mapping code changes back to CWE/OWASP requirements)
     7. Tests Needed (unit tests, integration tests, edge cases)
     8. Reviewer Action (approve / request changes / skip)
   - Present the complete fix report to the user

   **4g. Wait for reviewer action:**
   - **Approve** → Save the fix report and move to the next issue
   - **Request changes** → The user provides feedback; revise the fix and re-present
   - **Skip** → Mark as skipped with reason and move to the next issue
   - **Stop** → End the session; compile all completed fix reports into a summary

5. **LOOP BACK** to Step 4 for the next issue in the queue. Repeat until:
   - All issues have been processed, OR
   - The user says "stop" or "that's enough for now"

6. **Compile session summary:**
   - List all issues processed with their status (fix suggested / changes requested / skipped / pending)
   - Save individual fix reports as `{repo-name}-fix-{issue-number}.md`
   - Save the session summary as `{repo-name}-fix-summary.md`
   - Provide all files to the user

## Reviewer Actions Reference

| Action | What Happens | User Says |
|--------|-------------|-----------|
| **Approve** | Fix report saved as-is; advance to next issue | "approve", "looks good", "next" |
| **Request changes** | User provides feedback; Claude revises and re-presents | "change X to Y", "use a different approach", "also check file Z" |
| **Skip** | Issue marked as skipped with reason; advance to next | "skip", "skip — not relevant", "come back to this later" |
| **Stop** | Session ends; all completed reports compiled | "stop", "that's enough", "done for now" |
