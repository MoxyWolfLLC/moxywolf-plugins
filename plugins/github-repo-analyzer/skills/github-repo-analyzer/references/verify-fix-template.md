# Verify-Fix Report Template

Output format for the `/verify-fix` command. One report per issue. All eight sections are required.

---

## Section 1: TLDR

```markdown
## TLDR

**{verdict_emoji} {verdict_text}**

- **{linked_prs_summary}** {linked_commits_summary}. {comments_summary}.
- {1–3 bullet points summarizing the key evidence — what specific code is still vulnerable or what fix was applied}
- {If UNFIXED: note the mass-closure pattern if applicable}

**{action_statement}**
```

Verdict emoji and text mapping:

| Verdict | Emoji + Text |
|---------|-------------|
| FIXED | ✅ This issue was fixed with code changes that address the vulnerability. |
| PARTIALLY FIXED | ⚠️ This issue was partially fixed — some aspects addressed but gaps remain. |
| UNFIXED | ❌ This issue was closed without any code fix. The vulnerability is still fully exploitable. |
| INCONCLUSIVE | ❓ Unable to determine fix status — manual review required. |

Action statement mapping:

| Verdict | Action Statement |
|---------|-----------------|
| FIXED | Closure confirmed — no action needed. |
| PARTIALLY FIXED | Reopening for additional remediation. / Flagged for additional remediation. |
| UNFIXED | Reopening for actual remediation. / Recommended for reopening. |
| INCONCLUSIVE | Flagged for manual review. |

---

## Section 2: Closure Metadata

```markdown
## 1. Closure Metadata

| Field | Value |
|-------|-------|
| **Closed by** | @{user} on {ISO timestamp} |
| **Linked PRs** | {count — link if found, "None" if zero} |
| **Linked Commits** | {count — SHA if found, "None" if zero} |
| **Comments at closure** | {count} |
| **Verification method** | Direct source code review via GitHub API |
| **Verification confidence** | **{High / Medium / Low}** |
```

Confidence levels:

| Level | Criteria |
|-------|----------|
| **High** | Source code confirmed — affected files retrieved and analyzed, fix pattern presence/absence verified |
| **Medium** | Commit found referencing the issue, but diff not fully analyzed or file paths ambiguous |
| **Low** | Insufficient evidence — files reorganized, paths changed, or unable to retrieve source code |

---

## Section 3: Evidence — Current State of Affected Files

```markdown
## 2. Evidence: Current State of Affected Files

### File {n}: `{file path}`

**{description of vulnerable endpoint/function/section}**

```{language}
{Current source code showing the relevant section — include enough context
to demonstrate whether the vulnerability is still present or has been fixed.
Add inline comments with ← arrows pointing to vulnerable/fixed lines.}
```

**Status:** {1–2 sentence assessment of this specific file — is the vulnerability still present? What validation is missing or was added?}

*Repeat for each affected file.*

### Codebase Search for {fix_type} Validation

| Directory Searched | Files Found | {Fix Pattern} Found? |
|---|---|---|
| `{path}` | {count or "404 — path doesn't exist"} | **{None / Yes — describe}** |

**{Summary statement about whether the fix pattern exists anywhere in the codebase.}**
```

---

## Section 4: Security Classification

```markdown
## 3. Security Classification

| Framework | ID | Name | How It Applies |
|-----------|----|------|----------------|
| **CWE** | CWE-{id} | {name} | {1 sentence — how this CWE maps to the specific issue} |
| **OWASP Top 10:2025** | {A0X} | {name} | {1 sentence} |
| **OWASP API Security 2023** | {APIX} | {name} | {1 sentence} |
| **OWASP Cheat Sheet** | {title} | — | {which specific guidance applies} |
| **OWASP ASVS v4.0** | {V.X.X} | {requirement text} | {how the fix satisfies this requirement} |
| **NIST SP 800-53** | {control} | {name} | {1 sentence} |

*Add additional rows as needed. Some issues map to multiple CWEs.*
```

---

## Section 5: Recommended Fix

```markdown
## 4. Recommended Fix

{Pull the recommended fix from `references/fix-patterns.md` based on the CWE classification. Adapt the generic pattern to the repo's language, framework, and conventions.}

**Create `{new utility file path}`:**

```{language}
{Complete implementation of the fix utility — include JSDoc/docstring comments,
type annotations, and defensive coding. This should be copy-paste ready.}
```

Then {describe how to integrate the utility into the affected files — which functions to wrap, which parameters to validate}.

**Tests needed:**

| Test Case | Input | Expected |
|-----------|-------|----------|
| {Happy path} | {valid input} | Accepted |
| {Attack vector 1} | {malicious input} | Rejected → default |
| {Attack vector 2} | {bypass attempt} | Rejected → default |
| {Edge case} | {boundary input} | {expected behavior} |
```

---

## Section 6: Actual Fix vs. Recommended Fix Comparison

```markdown
## 5. Actual Fix vs. Recommended Fix Comparison

| Dimension | What Was Recommended | What Actually Happened |
|-----------|---------------------|----------------------|
| **{fix component 1}** | {what should have been created/changed} | **{what actually exists — "Nothing" if unfixed}** |
| **{fix component 2}** | {what should have been created/changed} | **{what actually exists}** |
| **Tests added** | {count} test cases covering bypass vectors | **{what actually exists}** |
| **PR created** | Expected: PR with code review | **{None / PR #{number}}** |
| **Commits referencing #{issue}** | Expected: at least one commit | **{None / SHA}** |

**Gap assessment: {percentage}% gap.** {Summary — e.g., "No aspect of the recommended fix was implemented." or "Core fix applied but edge cases not covered."}
```

---

## Section 7: Closure Context

```markdown
## 6. Closure Context

{Describe whether this was an isolated closure or part of a pattern.}

| Timestamp (UTC) | Issues Closed |
|---|---|
| {date/time} | {issue numbers} |

{Analysis: Was this a mass-closure event? How many issues closed in what timeframe? Were any linked to PRs?}

**Conclusion:** {Administrative closure / Remedial closure / Mixed — with justification}
```

For mass-closure detection, flag when:
- 3+ security issues closed within 24 hours by the same user
- Zero linked PRs across the batch
- No comments explaining closure rationale

---

## Section 8: Risk Assessment

```markdown
## 7. Risk Assessment

| Factor | Assessment |
|--------|-----------|
| **Exploitability** | {barrier to exploitation — what an attacker needs to do} |
| **Authentication required** | {Yes — describe / No} |
| **Impact** | {what happens when exploited — be specific about data/functionality exposed} |
| **Blast radius** | {who is affected and how many} |
| **Confidence** | **{High / Medium / Low}** — {method used to verify} |
```

---

## Batch Summary Template

Used at the end of a `/verify-fix --batch` session to compile all verified issues.

```markdown
# Closure Verification Audit — {repo name}

**Repository:** [{owner}/{repo}](https://github.com/{owner}/{repo})
**Date:** {date}
**Issues verified:** {count}
**Verification method:** Source code review via GitHub API

## Verdicts Summary

| # | Title | Priority | Verdict | Linked PRs | Linked Commits |
|---|-------|----------|---------|------------|----------------|
| #{id} | {title} | {P0–P3} | {FIXED / PARTIALLY FIXED / UNFIXED / INCONCLUSIVE} | {count} | {count} |

## Statistics

| Metric | Count |
|--------|-------|
| Total verified | {n} |
| ✅ Fixed | {n} |
| ⚠️ Partially fixed | {n} |
| ❌ Unfixed | {n} |
| ❓ Inconclusive | {n} |

## Mass-Closure Pattern Analysis

{If detected: timeline table, user who closed, PR/commit counts across the batch.}
{If not detected: "No mass-closure pattern identified. Issues were closed individually with associated code changes."}

## Prioritized Reopen List

{Ordered by priority, then by exploitability. Only includes UNFIXED and PARTIALLY FIXED issues.}

| Priority | # | Title | Verdict | Recommended Action |
|----------|---|-------|---------|--------------------|
| {P0–P3} | #{id} | {title} | {verdict} | {Reopen / Reopen with partial credit / Manual review} |

## CWE Coverage

| CWE | Name | Issues |
|-----|------|--------|
| CWE-{id} | {name} | #{id}, #{id} |

## Next Steps

- {Issues to reopen with verification reports}
- {Issues needing manual review}
- {Recommended PR strategy for batch remediation}
```

---

## GitHub Comment Template

Used when `--reopen` flag is set and the verdict is UNFIXED or PARTIALLY FIXED. This is posted as a comment before reopening the issue.

```markdown
# Closure Verification Report — Reopening

## TLDR

**{verdict_emoji} {verdict_text}**

- {key evidence bullets from TLDR section}

**Reopening for actual remediation.**

---

## Full Verification Report

{Include sections 2–8 from the main template above, renumbered as subsections:
1. Closure Metadata
2. Evidence: Current State of Affected Files
3. Security Classification
4. Recommended Fix
5. Actual vs. Recommended Comparison
6. Closure Context
7. Risk Assessment}

---

*Verification performed via source code review using GitHub API. Full report archived in project docs.*
```
