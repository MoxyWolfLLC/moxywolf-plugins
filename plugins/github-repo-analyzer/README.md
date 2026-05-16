# GitHub Repo Analyzer

Analyze any GitHub repository for health, tech stack conformance, structured issue reviews with security classification, code fix suggestions, and fix verification — built for MoxyWolf LLC internal use.

## What It Does

- **Health Reports** — Produces structured Markdown reports covering architecture, code quality, dependency health, contributor patterns, security posture, and technical debt
- **Stack Conformance** — Compares detected technologies against MoxyWolf's approved tech stack and flags deviations
- **Issue Reviews** — Fetches all repository issues, clusters security findings by vulnerability domain, applies CWE/OWASP/NIST classification, assesses team pushback, and audits whether closed issues had actual code remediation
- **PRD Generation** — Reverse-engineers a 17-section PRD from existing codebases using MoxyWolf's standard PRD template
- **Fix Suggestions** — Generates code fix reports for open issues one at a time with HITL reviewer approval, using three-tier file path extraction and CWE Top 25 fix pattern catalog
- **Fix Verification** — Cross-references closed issue metadata against current source code to determine whether issues were actually fixed, partially fixed, or left unresolved

## Commands

| Command | Description |
|---------|-------------|
| `/analyze-repo <url>` | Generate a health report with stack conformance check |
| `/review-issues <url>` | Generate a structured issue review with security classification |
| `/reverse-prd <url>` | Generate a health report plus a reverse-engineered PRD |
| `/suggest-fixes <url>` | Suggest code fixes for open issues one at a time with reviewer approval |
| `/verify-fix <url>` | Verify whether closed issues were actually fixed in the codebase |

All commands accept an optional `--quick` flag for root-level-only analysis (faster, less detailed).

The `/review-issues` command accepts additional flags:
- `--security-only` — Only include security-labeled issues
- `--include-closure-audit` — Explicitly run the closure audit (auto-triggered when closed security issues are found)

The `/suggest-fixes` command accepts additional flags:
- `--security-only` — Only process security-labeled issues
- `--max <n>` — Limit to n issues per run (default: all open issues)

The `/verify-fix` command accepts additional flags:
- `--security-only` — Only verify security-labeled issues
- `--reopen` — Automatically reopen issues verified as UNFIXED
- `--max <n>` — Limit to n issues per run (default: all closed issues)

## Natural Language Triggers

You can also trigger the analyzer conversationally:

- "Analyze this repo: https://github.com/org/repo"
- "Check if this repo matches our stack"
- "Review the issues on this repo"
- "Audit the security issues for https://github.com/org/repo"
- "Are the closed security issues actually fixed?"
- "Classify the vulnerabilities in the issue tracker"
- "Reverse-engineer a PRD from this codebase"
- "Suggest fixes for the open issues on this repo"
- "Generate a fix report for https://github.com/org/repo"
- "Verify the closed issues are actually fixed"
- "Check if closed issues on this repo were really resolved"
- "Full audit of https://github.com/org/repo"

## Components

| Type | Name | Purpose |
|------|------|---------|
| Skill | `github-repo-analyzer` | Core analysis knowledge, workflow, and report structure |
| Command | `/analyze-repo` | Health report + stack conformance |
| Command | `/review-issues` | Issue review + security classification + closure audit |
| Command | `/reverse-prd` | Health report + PRD generation |
| Command | `/suggest-fixes` | Code fix suggestions with HITL reviewer approval |
| Command | `/verify-fix` | Fix verification against closed issue metadata |

## Reference Files

The plugin bundles six reference documents:

- **tech-stack.md** — MoxyWolf's approved technology stack (Directus, Next.js, Vercel, Supabase, tRPC, shadcn/ui, etc.)
- **prd-template.md** — 17-section PRD template for structuring reverse-engineered PRDs
- **prd-assessment-template.md** — Evaluation rubric for scoring PRD completeness
- **issue-review-template.md** — Structured issue review report template with CWE/OWASP/NIST classification framework and closure audit format
- **suggest-fixes-template.md** — Fix report template with 8-section structure, three-tier file discovery, and CWE Top 25 fix patterns
- **verify-fix-template.md** — Verification report template with 9-step loop, 4 verdicts (FIXED, PARTIALLY FIXED, UNFIXED, INCONCLUSIVE), and mass-closure detection

## Backend

This plugin uses native Cowork tooling — no third-party broker:

- **Native GitHub MCP** (the Cowork-managed GitHub connector) for `list_repos`, `list_branches`, `list_issues`, `list_pulls`, `get_issue_comments`, `get_pull_comments`, `create_issue`, `create_pr`, and `push_file`.
- **`Bash` + `gh` CLI** (or `curl` with a `GITHUB_TOKEN`) for everything the MCP doesn't expose — repo tree traversal, per-file content reads, per-issue events/timeline, per-commit metadata.
- **`Bash` + `git clone`** for `/analyze-repo` and `/reverse-prd` when a full local checkout makes the analysis cleaner than walking the tree via API.

## Setup

- The GitHub MCP must be authenticated in Cowork → Connectors with read access to the repos you want to analyze.
- For deeper REST calls, install GitHub Desktop's CLI (`gh`) or set `GITHUB_TOKEN` in your shell. The `gh` path is preferred — it reuses your already-authenticated session and handles pagination cleanly.
