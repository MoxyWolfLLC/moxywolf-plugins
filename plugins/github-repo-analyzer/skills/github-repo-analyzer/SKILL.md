---
name: github-repo-analyzer
description: >
  This skill should be used when the user asks to "analyze a GitHub repo",
  "check repo health", "audit a repository", "review a codebase",
  "measure tech stack conformance", "reverse-engineer a PRD",
  "generate a PRD from code", "review issues", "audit security issues",
  "classify vulnerabilities", "check if closed issues were actually fixed",
  "suggest fixes", "generate code fixes", "fix this issue",
  "suggest a remediation", "what's the fix for this vulnerability",
  or needs a structured health report, issue review, or code fix suggestion
  for any public or accessible GitHub repository.
version: 0.4.0
---

# GitHub Repo Analyzer

Analyze any GitHub repository via the GitHub API to produce structured health reports, measure tech stack conformance against MoxyWolf's approved stack, generate structured issue reviews with CWE/OWASP/NIST security classification, suggest code fixes one issue at a time with human-in-the-loop approval, verify whether closed issues were actually fixed with code changes, and optionally reverse-engineer a Product Requirements Document (PRD).

## Backend

This skill uses native Cowork tooling end-to-end — no third-party broker:

**Repo analysis (`/analyze-repo`, `/reverse-prd`):** prefer a local clone via `gh repo clone "${OWNER}/${REPO}"` and walk the working tree with `Glob` / `Read` / `Grep`. Fall back to the GitHub REST tree API (`gh api "/repos/${OWNER}/${REPO}/git/trees/${BRANCH}?recursive=1"` + `gh api "/repos/${OWNER}/${REPO}/contents/${PATH}"`) when cloning isn't viable or when `--quick` is set.

**Issue work (`/review-issues`, `/suggest-fixes`, `/verify-fix`):** mix the native GitHub MCP (Cowork-managed) with direct REST via `gh api` for endpoints the MCP doesn't expose.

| Need | Tool |
|------|------|
| List issues (open/closed, with labels) | Native GitHub MCP `list_issues` |
| Full issue body and metadata | `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}"` |
| Issue comment thread | Native GitHub MCP `get_issue_comments` |
| Issue timeline (linked PRs, commits, close events) | `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}/timeline" --paginate` |
| Source file content | `gh api "/repos/${OWNER}/${REPO}/contents/${PATH}"` (base64; decode with `jq -r .content \| base64 -d`) or `Read` against a local `gh repo clone` |
| Repo tree | `gh api "/repos/${OWNER}/${REPO}/git/trees/${BRANCH}?recursive=1"` |
| Post a comment | `gh issue comment ${NUMBER} --repo "${OWNER}/${REPO}" --body-file <file>` |
| Reopen an issue | `gh issue reopen ${NUMBER} --repo "${OWNER}/${REPO}"` |
| List PRs | Native GitHub MCP `list_pulls` |
| Branch inventory | Native GitHub MCP `list_branches` |

Authentication: `gh` reuses your already-authenticated GitHub Desktop session, so no token plumbing is required on a normal MoxyWolf workstation. If `gh` isn't installed, fall back to `curl` with `GITHUB_TOKEN` set in the shell.

## Inputs

### Health Report / PRD Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `repo_url` | Yes | Full GitHub URL (e.g., `https://github.com/org/repo`) |
| `include_prd` | No | Set to `true` to reverse-engineer a PRD alongside the health report. Default: `false` |
| `analysis_depth` | No | `deep` for full recursive tree traversal, `quick` for root-level only. Default: `deep` |
| `client_name` | No | Client or project name for report branding |

### Issue Review Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `repo_url` | Yes | Full GitHub URL (e.g., `https://github.com/org/repo`) |
| `--security-only` | No | Only include security-labeled issues. Default: include all issues |
| `--include-closure-audit` | No | Explicitly run closure audit. Default: auto-triggered when closed security issues are found |

### Fix Suggestion Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `repo_url` | Yes | Full GitHub URL (e.g., `https://github.com/org/repo`) |
| `--issue <number>` | No | Start with a specific issue number instead of the first in priority order |
| `--security-only` | No | Only process issues with a `security` label |

### Verify-Fix Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `repo_url` | Yes | Full GitHub URL (e.g., `https://github.com/org/repo`) |
| `--issue <number>` | Yes (unless `--batch`) | Verify a specific closed issue by number |
| `--batch` | No | Verify ALL closed security-labeled issues instead of a single issue. Replaces `--issue` |
| `--reopen` | No | After verification, reopen any issue confirmed unfixed and post the verification report as a GitHub comment |

## Trigger Routing

Match the user's intent to the appropriate analysis mode:

| User Says | Mode | Command |
|-----------|------|---------|
| "Analyze this repo" / "Check repo health" | Health report only | `/analyze-repo` |
| "Reverse-engineer a PRD from this repo" | Health + PRD | `/reverse-prd` |
| "Does this repo match our stack?" | Conformance check | `/analyze-repo` |
| "Full audit of this repo" | Everything | `/reverse-prd` with deep analysis |
| "Review the issues" / "Audit security issues" | Issue review | `/review-issues` |
| "Are closed issues actually fixed?" / "Closure audit" | Issue review + closure audit | `/review-issues --include-closure-audit` |
| "Classify the vulnerabilities" / "CWE analysis" | Security-focused issue review | `/review-issues --security-only` |
| "Suggest fixes" / "Generate code fixes" | HITL fix suggestions | `/suggest-fixes` |
| "Fix issue #138" / "What's the fix for this?" | Single-issue fix | `/suggest-fixes --issue 138` |
| "Suggest security fixes only" | Security-scoped fixes | `/suggest-fixes --security-only` |
| "Remediate these vulnerabilities" | HITL fix suggestions | `/suggest-fixes --security-only` |
| "Was this issue actually fixed?" / "Verify the fix" | Single-issue verification | `/verify-fix --issue 146` |
| "Verify all closed security issues" / "Closure verification audit" | Batch verification | `/verify-fix --batch` |
| "Verify and reopen unfixed issues" | Batch verify + reopen | `/verify-fix --batch --reopen` |
| "Check if closed issues were actually fixed" | Batch verification | `/verify-fix --batch` |

## Analysis Workflow — Health Report

1. **Accept the repo URL** from the user. Extract owner and repo name.
2. **Gather repo data.** Prefer a local clone for `deep` analysis: `gh repo clone "${OWNER}/${REPO}" /tmp/analyze-$$` and walk it with `Glob` / `Read` / `Grep`. For `quick` mode or when cloning isn't possible, use `gh api` against the tree and contents endpoints (see the Backend table above).
3. **Inspect the gathered data** into structured sections — package manifests, configs, code samples, doc files, contributor patterns.
4. **Stack conformance** — Compare detected technologies against the approved tech stack in `references/tech-stack.md`. Flag deviations, missing expected tools, and unexpected additions.
5. **PRD generation** (if requested) — Use the template in `references/prd-template.md` to structure the reverse-engineered PRD. Fill in as many sections as the codebase evidence supports.
6. **Compile the final report** as a Markdown document.

## Analysis Workflow — Issue Review

1. **Accept the repo URL** from the user. Extract owner and repo name.

2. **Fetch all repository issues** using the native GitHub MCP plus REST where needed:
   - Native GitHub MCP `list_issues` for the inventory of open and closed issues with labels and metadata.
   - For each issue's full body text, `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}"`.
   - For security-labeled issues, fetch comment threads via the native MCP `get_issue_comments`.
   - For pagination across large issue trackers, `gh api --paginate` handles it transparently — no manual chunking needed.

3. **Build structured issue inventory:**
   - Parse labels to determine priority (P0–P3) and category (security, billing, infrastructure, etc.)
   - Count open/closed/total by priority level
   - Identify security-labeled issues for deep classification

4. **Cluster security issues by vulnerability domain:**
   - Group issues that share attack surfaces, affected code paths, or vulnerability types
   - Common cluster themes: credential storage, authorization/IDOR, billing integrity, CORS/origin trust, information disclosure, infrastructure hardening
   - Each cluster gets its own section with full analysis

5. **Apply CWE/OWASP/NIST classification** to each security cluster:
   - Map each vulnerability to relevant CWE identifiers (reference: `references/issue-review-template.md`)
   - Map to OWASP Top 10:2025 categories
   - Map to OWASP API Security Top 10:2023 where applicable
   - Map to NIST SP 800-53 controls
   - Build a classification table for each cluster

6. **Analyze code evidence:**
   - Extract affected file paths from issue bodies
   - Document the current implementation approach vs. industry best practice
   - Build comparison tables for each cluster

7. **Assess team pushback:**
   - Scan comment threads for disagreement, "false positive" claims, or dismissal language
   - Quote the specific pushback and provide technical rebuttal
   - Evaluate whether pushback is valid, partially valid, or invalid
   - Flag patterns: RLS misapplication, "not public so not a risk" fallacy, bulk dismissal

8. **Run closure audit** (auto-triggered when closed security issues exist, or when `--include-closure-audit` is set):
   - Use `GITHUB_LIST_REPOSITORY_EVENTS` to fetch repository event history
   - Check for PullRequestEvent entries (any PRs ever created?)
   - Check for PushEvent entries and examine commit messages for issue references
   - For each closed security issue, determine:
     - Who closed it and when
     - Whether any PR or commit is linked
     - Whether the "false positive" claim is technically valid
   - Build a mass-closure timeline if multiple issues were closed in rapid succession
   - Provide issue-by-issue verdicts

9. **Compile the report** using the template in `references/issue-review-template.md`:
   - Executive summary with issue inventory table
   - Security clusters with full classification tables
   - Vulnerability analysis with affected files
   - Team pushback assessment with rebuttals
   - Closure audit addendum (if applicable)
   - Prioritized remediation roadmap

10. **Save** as `{repo-name}-issue-review.md` and provide to user.

## Analysis Workflow — Fix Suggestions (HITL)

This workflow processes issues **one at a time** with human-in-the-loop approval at each step.

1. **Accept the repo URL** from the user. Extract owner and repo name.

2. **Fetch the issue queue:**
   - Retrieve all issues via `GITHUB_LIST_REPOSITORY_ISSUES`
   - If `--security-only`, filter to security-labeled issues
   - Sort by priority: P0 → P1 → P2 → P3 → unlabeled
   - Present the queue to the user and ask which issue to start with
   - If `--issue <number>` is set, start with that issue

3. **HITL Loop — for each issue:**

   **a. Fetch issue details:**
   - Full body, labels, and metadata via `GITHUB_GET_AN_ISSUE`
   - Comment threads via `GITHUB_LIST_ISSUE_COMMENTS`
   - Present a brief summary to the reviewer

   **b. Extract file paths (three-tier fallback):**
   - **Tier 1 — Explicit:** Scan issue body and comments for file paths, code blocks, backtick-quoted paths
   - **Tier 2 — Keyword inference:** Map domain terms from labels/title to likely file locations (billing → `**/billing/**`, auth → `**/auth/**`, CORS → `**/cors*`, etc.)
   - **Tier 3 — Schema/config scan:** Use `GITHUB_GET_REPOSITORY_CONTENT` to scan the repo tree for route definitions, config files, and schema files
   - Present discovered files to the user for confirmation

   **c. Fetch source code:**
   - Retrieve file contents via `GITHUB_GET_REPOSITORY_CONTENT`
   - For large files, scan for the relevant functions/classes

   **d. Scan for existing patterns:**
   - Search the codebase for instances where the same vulnerability class is already handled correctly
   - Document the existing secure pattern and explain how to apply it to the affected file(s)
   - If no existing pattern exists, note this — the fix will establish a new pattern

   **e. Apply security reference catalog:**
   - Match the issue to CWE identifiers using `references/fix-patterns.md`
   - Pull the corresponding fix pattern template
   - Map to OWASP Top 10:2025, OWASP API Security 2023, OWASP ASVS v4.0, OWASP Cheat Sheets, and NIST SP 800-53
   - Adapt the generic pattern to the repo's language, framework, and conventions

   **f. Generate the fix report:**
   - Use the template from `references/fix-report-template.md`
   - Fill all eight sections: Issue Header, Vulnerability Description, Security Classification, Existing Patterns, Recommended Fix, Why This Fix Works, Tests Needed, Reviewer Action
   - Present the complete report to the reviewer

   **g. Wait for reviewer action:**
   - **Approve** → Save the report and advance to the next issue
   - **Request changes** → Reviewer provides feedback; revise the fix and re-present
   - **Skip** → Mark as skipped with reason and advance
   - **Stop** → End the session and compile summary

4. **Compile session summary:**
   - List all issues processed with status (approved / revised / skipped / pending)
   - Save individual reports as `{repo-name}-fix-{issue-number}.md`
   - Save session summary as `{repo-name}-fix-summary.md`

## Analysis Workflow — Verify Fix

Verify whether closed issue(s) were actually fixed with code changes, or merely closed without remediation.

1. **Accept the repo URL** from the user. Extract owner and repo name. Check for flags:
   - `--issue <number>`: Verify a specific closed issue (required unless `--batch`)
   - `--batch`: Verify ALL closed security-labeled issues
   - `--reopen`: After verification, reopen unfixed issues and post the report as a comment

2. **Identify target issues:**
   - If `--issue <number>`: fetch that single issue via `GITHUB_GET_AN_ISSUE`
   - If `--batch`: fetch all closed issues with a `security` label via `GITHUB_LIST_REPOSITORY_ISSUES` (state: closed)
   - Verify each target is in a closed state. Skip open issues with a note.

3. **Verification loop — for each target issue:**

   **a. Fetch issue metadata:**
   - Full body, labels, state, closer, closure timestamp via `GITHUB_GET_AN_ISSUE`
   - All comments via `GITHUB_LIST_ISSUE_COMMENTS`
   - Repository events via `GITHUB_LIST_REPOSITORY_EVENTS` to find PullRequestEvent and PushEvent entries linked to the issue
   - Record: who closed it, when, linked PRs (count), linked commits (count), comments at closure

   **b. Extract affected file paths — three-tier fallback:**
   - **Tier 1 — Explicit:** Scan issue body and comments for file paths, code blocks, backtick-quoted paths
   - **Tier 2 — Keyword inference:** Map domain terms from labels/title to likely file locations
   - **Tier 3 — Schema/config scan:** Use `GITHUB_GET_REPOSITORY_CONTENT` to scan the repo tree
   - Present discovered files for confirmation (skip confirmation in `--batch` mode)

   **c. Fetch current source code:**
   - Retrieve current file contents via `GITHUB_GET_REPOSITORY_CONTENT` for each affected file
   - Decode base64 content and extract the relevant code sections

   **d. Match to fix patterns catalog:**
   - Identify the CWE class from the issue body, labels, and title
   - Look up the corresponding fix pattern from `references/fix-patterns.md`
   - Determine what a proper fix WOULD look like for this vulnerability class

   **e. Compare actual code vs. expected fix:**
   - Scan current source code for evidence that the fix pattern was applied (validation functions, sanitization, authorization guards, allowlists, etc.)
   - Check whether the specific vulnerable code described in the issue has been modified
   - Search the broader codebase for any new utility/helper implementing the fix pattern

   **f. Determine verdict:**
   - **FIXED** — Code changes found that address the vulnerability
   - **PARTIALLY FIXED** — Some aspects addressed but gaps remain
   - **UNFIXED** — No code changes found; vulnerable code is unchanged
   - **INCONCLUSIVE** — Unable to determine (file paths changed, code reorganized, insufficient evidence)

   **g. Assess closure context:**
   - Was this part of a mass-closure event? (3+ security issues closed within 24 hours by same user, zero linked PRs)
   - Were there comments explaining the closure rationale?
   - Is there a "false positive" or "won't fix" justification?

   **h. Generate verification report:**
   - Use the template from `references/verify-fix-template.md`
   - Fill all 8 sections: TLDR, Closure Metadata, Evidence (current code state), Security Classification, Recommended Fix, Actual vs. Recommended Comparison, Closure Context, Risk Assessment

   **i. Handle `--reopen` flag (if set and verdict is UNFIXED or PARTIALLY FIXED):**
   - Present the verification report to the user
   - Ask for confirmation: "Should I reopen issue #{number} and post this report as a comment?"
   - If confirmed: post report as comment via `GITHUB_CREATE_AN_ISSUE_COMMENT`, then reopen via `GITHUB_UPDATE_AN_ISSUE` (state: open)
   - If declined: save the report locally only

4. **Loop back** to step 3 for the next issue (in `--batch` mode).

5. **Compile summary:**
   - Single-issue mode: Save as `{repo-name}-verify-fix-{issue-number}.md`
   - Batch mode: Save individual reports plus a batch summary as `{repo-name}-verify-fix-audit.md` containing verdicts table, mass-closure pattern analysis, statistics, prioritized reopen list, and CWE coverage

## Health Report Structure

The health report covers these sections:

- **Repository Overview** — Name, description, primary language, license, visibility, last updated
- **Architecture & Structure** — Directory layout, monorepo detection, framework identification, design patterns
- **Tech Stack Inventory** — Languages, frameworks, databases, infrastructure, CI/CD, detected from package files, configs, and imports
- **Stack Conformance** — Side-by-side comparison against MoxyWolf's approved stack with match/deviation/missing status for each layer
- **Code Quality Signals** — Linter configs, test frameworks, CI pipelines, code coverage indicators, formatting tools
- **Dependency Health** — Total count, outdated packages, known vulnerabilities (if detectable), license concerns
- **Contributor Health** — Active contributors, commit frequency, bus factor, PR merge patterns
- **Documentation Assessment** — README quality, API docs, inline comments, architecture docs
- **Security Posture** — .env handling, secret detection patterns, auth approach, dependency audit configs
- **Technical Debt Indicators** — TODO/FIXME density, large files, complex modules, stale branches
- **Recommendations** — Prioritized action items grouped by urgency (critical, important, nice-to-have)

## Issue Review Report Structure

The issue review report covers these sections:

- **Executive Summary** — Issue inventory by priority, security issue count, closure status, threat domain overview
- **Security Clusters** — Grouped by vulnerability domain, each containing:
  - Issue listing table
  - Vulnerability analysis with affected files
  - CWE/OWASP/NIST classification table
  - Recommended vs. current approach comparison
  - Team pushback assessment with technical rebuttals
- **Non-Security Categories** (optional) — Billing, infrastructure, code quality, product/feature groupings
- **Closure Audit Addendum** (when applicable) — Linked PRs/commits analysis, mass-closure timeline, issue-by-issue verdicts, pattern analysis
- **Remediation Roadmap** — Prioritized action items by severity

## Fix Report Structure

Each fix report (one per issue) contains eight sections:

1. **Issue Header** — Issue number, title, state, priority, labels, affected files
2. **Vulnerability Description** — Plain-language explanation, attacker scenario, blast radius
3. **Security Classification** — CWE, OWASP Top 10, OWASP API Security, OWASP ASVS, OWASP Cheat Sheets, NIST SP 800-53 mappings
4. **Existing Patterns in Codebase** — Where the same vulnerability class is already handled correctly elsewhere
5. **Recommended Fix** — Actual code with before/after comparison and inline comments
6. **Why This Fix Works** — Table mapping each code change to the CWE/OWASP/NIST requirement it satisfies
7. **Tests Needed** — Unit tests, integration tests, regression tests with specific test cases
8. **Reviewer Action** — Approve, request changes, skip, or stop

## Verify-Fix Report Structure

Each verification report (one per issue) contains eight sections:

1. **TLDR** — Verdict emoji, key evidence bullets, action statement
2. **Closure Metadata** — Who closed, when, linked PRs/commits count, verification confidence (High/Medium/Low)
3. **Evidence: Current State of Affected Files** — Current source code with inline vulnerability/fix annotations, codebase search for fix patterns
4. **Security Classification** — CWE, OWASP Top 10, OWASP API Security, OWASP ASVS, OWASP Cheat Sheets, NIST SP 800-53 mappings
5. **Recommended Fix** — Code from fix-patterns catalog adapted to repo conventions, with test cases
6. **Actual Fix vs. Recommended Fix Comparison** — Dimension-by-dimension gap assessment with percentage
7. **Closure Context** — Mass-closure timeline (if applicable), administrative vs. remedial conclusion
8. **Risk Assessment** — Exploitability, authentication required, impact, blast radius, confidence level

Batch mode additionally produces a **Batch Summary** with verdicts table, statistics, mass-closure pattern analysis, prioritized reopen list, and CWE coverage.

## PRD Output Format

When `include_prd` is true, generate a PRD following the template in `references/prd-template.md`. Fill sections based on what the codebase reveals. Mark sections where evidence is insufficient as "Requires stakeholder input."

After generation, assess PRD completeness using the rubric in `references/prd-assessment-template.md`.

## Scope Guidance

| Scope | What's Included | What's Excluded |
|-------|-----------------|-----------------|
| Repository analysis | File tree, configs, package manifests, README, CI files | Runtime behavior, live API testing |
| Stack conformance | Technology detection vs. approved stack comparison | Version-level compatibility checks |
| PRD generation | Architecture, features, integrations inferred from code | Business metrics, user research, pricing |
| Security posture | Static indicators (configs, patterns, .env handling) | Dynamic vulnerability scanning |
| Issue review | All issues, labels, comments, events, closure history | Private issue content not accessible via API |
| Security classification | CWE, OWASP Top 10, OWASP API Security, NIST 800-53 | CVE assignment, CVSS scoring |
| Closure audit | Repository events, PR history, commit references | CI/CD logs, deployment history |
| Fix suggestions | Source code analysis, pattern detection, code generation | Automated PR creation, code deployment |
| Fix patterns | CWE Top 25 + children, OWASP ASVS v4.0, Cheat Sheets | Full CWE database, OWASP Testing Guide |
| HITL workflow | One issue at a time, reviewer approval at each step | Batch processing, auto-merge, CI integration |
| Closure verification | Closed issue metadata, events, PRs, commits, current source code | Runtime testing, CI/CD logs, deployment verification |
| Verify-fix verdicts | FIXED, PARTIALLY FIXED, UNFIXED, INCONCLUSIVE based on source code review | Dynamic exploit validation, penetration testing |
| Reopen workflow | Post verification report as comment, reopen issue via API | Automated PR creation, branch management |

## Reference Files

- **`references/tech-stack.md`** — MoxyWolf's approved technology stack with architecture layers, integration patterns, and tooling decisions
- **`references/prd-template.md`** — 17-section PRD template used as the output format for reverse-engineered PRDs
- **`references/prd-assessment-template.md`** — Comprehensive PRD evaluation rubric for assessing completeness and quality
- **`references/issue-review-template.md`** — Structured issue review report template with CWE/OWASP/NIST classification framework and closure audit format
- **`references/fix-patterns.md`** — Embedded security fix patterns catalog mapping CWE Top 25 to concrete code templates with OWASP ASVS, Cheat Sheet, and NIST SP 800-53 cross-references
- **`references/fix-report-template.md`** — Eight-section fix report output template with session summary format
- **`references/verify-fix-template.md`** — Eight-section closure verification report template with batch summary and GitHub comment templates for the `--reopen` workflow

## Limitations

- Requires GitHub API access — the native GitHub MCP must be authenticated in Cowork, plus `gh` CLI (or `GITHUB_TOKEN`) for endpoints the MCP doesn't expose
- Cannot execute code or test runtime behavior
- Private repos require appropriate GitHub permissions on whichever account `gh` / the MCP is authenticated as
- PRD sections dependent on business context (user personas, KPIs, pricing) will be marked as needing stakeholder input
- Analysis quality depends on repository documentation and conventional project structure
- Issue review depends on issue quality — poorly written issues with no file references will have limited classification
- Closure audit uses the Events API which returns the most recent 100 events; older history may not be available
- CWE/OWASP classification is based on issue descriptions, not dynamic code scanning
- Fix suggestions are static analysis only — they cannot verify runtime behavior or execute tests
- Fix code is a recommendation, not a guaranteed working implementation — reviewer must validate before applying
- Large files may need to be fetched in sections; the GitHub API has a 1 MB file size limit for content retrieval
- The fix patterns catalog covers the CWE Top 25 and common application security patterns; exotic or domain-specific vulnerabilities may require web search supplementation
- Verify-fix batch mode processes issues sequentially; large batches with many affected files may approach context limits
- The Events API returns the most recent 100 events; closure events older than the event window may lack linked PR/commit data, reducing verification confidence
- The `--reopen` flag requires write permissions on the repository; read-only connections will fail at the reopen/comment step
- Verify-fix verdicts are based on static source code comparison against fix pattern expectations — a fix implemented differently than the catalog pattern may be marked INCONCLUSIVE rather than FIXED
