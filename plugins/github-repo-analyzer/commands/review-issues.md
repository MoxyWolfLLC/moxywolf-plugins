---
description: Generate a structured security issue review with CWE/OWASP/NIST classification
argument-hint: <github-url> [--security-only] [--include-closure-audit]
---

Analyze all GitHub issues for the repository at $1 and produce a structured issue review report with security classification.

## Steps

1. Parse the repo URL from `$ARGUMENTS`. Extract the owner and repo name. Check for flags:
   - `--security-only`: Only include issues with a `security` label (skip non-security issues)
   - `--include-closure-audit`: Run the closure audit phase to verify whether closed issues had actual code remediation

2. Read the skill file at `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/SKILL.md` to load the issue review workflow, classification framework, and report structure.

3. Read the issue review template from `${CLAUDE_PLUGIN_ROOT}/skills/github-repo-analyzer/references/issue-review-template.md`.

4. **Fetch all repository issues** using the native GitHub MCP plus REST where needed:
   - Native GitHub MCP `list_issues` for the inventory of open and closed issues with labels, state, and metadata.
   - Native GitHub MCP `get_issue_comments` for each issue's comment thread.
   - For full issue body text (the MCP's `list_issues` may return summaries only), call `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}"` per issue via `Bash`.
   - If pagination matters, `gh api --paginate` handles it transparently.
   - Store structured issue data for analysis.

5. **Classify and cluster issues:**
   - Identify security-tagged issues and group them into vulnerability clusters based on shared attack surface or code paths
   - For each security cluster, perform CWE/OWASP/NIST classification using the framework defined in the template
   - For non-security issues (unless `--security-only`), group by category (billing, infrastructure, code quality, product/feature)

6. **Analyze team pushback:**
   - Scan issue comments for disagreement, "false positive" claims, or dismissal language
   - For each instance, document the claim and provide a technical assessment of its validity
   - Flag any pattern of dismissing legitimate findings

7. **Closure audit** (if `--include-closure-audit` flag is set OR if closed security issues are detected):
   - `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}/timeline"` (or `/events`) to get linked PRs and commits per issue.
   - `gh api "/repos/${OWNER}/${REPO}/issues/${NUMBER}/events"` for the close-event metadata (who closed it, when, with what commit/PR reference).
   - For each closed security issue, determine whether any code changes were made (linked PR? linked commit? or just "closed as not planned"?).
   - Build a mass-closure timeline if multiple issues were closed in rapid succession (e.g. >5 closures in <1 hour).
   - Provide issue-by-issue verdicts on whether the closure was justified.

8. **Compile the report** following the template structure:
   - Executive Summary with issue inventory table
   - Security clusters with full CWE/OWASP/NIST classification tables
   - Vulnerability analysis with affected files and recommended vs. current approach
   - Team pushback assessment with technical rebuttals
   - Closure audit addendum (if applicable)
   - Prioritized remediation roadmap

9. Save the report as `{repo-name}-issue-review.md` and provide it to the user.
