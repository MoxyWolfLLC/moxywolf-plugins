# Fix Report Template

Output format for the `/suggest-fixes` command. One report per issue. All eight sections are required.

---

## Section 1: Issue Header

```markdown
# Fix Report: Issue #{number} — {title}

| Field | Value |
|-------|-------|
| **Issue** | [#{number}](https://github.com/{owner}/{repo}/issues/{number}) |
| **Title** | {title} |
| **State** | {Open / Closed} |
| **Priority** | {P0 / P1 / P2 / P3 / Unlabeled} |
| **Labels** | {comma-separated labels} |
| **Opened by** | @{user} on {date} |
| **Closed by** | @{user} on {date} *(if closed)* |
| **Affected files** | {comma-separated file paths} |
```

---

## Section 2: Vulnerability Description

```markdown
## Vulnerability Description

**What's wrong:** {1–2 sentence plain-language description of the vulnerability. No jargon — a non-security engineer should understand this.}

**Why it matters:** {What an attacker could do if this is exploited. Be specific: "An authenticated user in Organization A could access billing records belonging to Organization B by changing the invoice ID in the API request."}

**Blast radius:** {What data or functionality is exposed. Quantify if possible: "All {N} organizations' billing data," or "Any user's PII."}
```

---

## Section 3: Security Classification

```markdown
## Security Classification

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

## Section 4: Existing Patterns in Codebase

```markdown
## Existing Patterns in Codebase

{Describe instances where the codebase already handles this vulnerability class correctly. If none exist, state "No existing pattern found — this will be a new pattern for the codebase."}

**Pattern found in:** `{file path}`

```{language}
// Existing code that correctly implements the fix pattern
// Include enough context to show the pattern (typically 5–15 lines)
{code}
```

**What this pattern does:** {Explain why this code is secure and how it prevents the vulnerability.}

**How to reuse it:** {Describe how to apply the same pattern to the affected file(s). Be specific: "Add the same `requireOrgMembership` middleware to the `/api/billing/:orgId` route in `src/routes/billing.ts`."}
```

---

## Section 5: Recommended Fix

```markdown
## Recommended Fix

### {file path}

```{language}
// === BEFORE ===
{existing vulnerable code — enough context to locate the exact insertion point}

// === AFTER ===
{fixed code with inline comments explaining each security-relevant change}
```

*Repeat for each affected file.*

### Implementation Notes

- {Any caveats, edge cases, or migration concerns}
- {Whether this requires a database migration, config change, or environment variable}
- {Whether any existing tests need to be updated}
```

---

## Section 6: Why This Fix Works

```markdown
## Why This Fix Works

| Change | Addresses | Reference |
|--------|-----------|-----------|
| {Specific code change — e.g., "Added orgId ownership check before query"} | {CWE-639: IDOR} | {OWASP ASVS V4.1.1, NIST AC-3} |
| {Next change} | {CWE/OWASP} | {citation} |

{1–2 paragraph narrative explaining the defense-in-depth approach. Connect the code changes to the security requirements they satisfy.}
```

---

## Section 7: Tests Needed

```markdown
## Tests Needed

### Unit Tests

| Test Case | Input | Expected Result |
|-----------|-------|-----------------|
| {Happy path — authorized access} | {valid user, own resource} | {200 OK with data} |
| {Cross-tenant access attempt} | {valid user, other org's resource} | {403 Forbidden} |
| {Unauthenticated access} | {no session/token} | {401 Unauthorized} |
| {Edge case} | {describe} | {expected behavior} |

### Integration Tests

- {Test the full request lifecycle end-to-end}
- {Test with realistic multi-tenant data}

### Regression Tests

- {Verify existing functionality is not broken by the fix}
- {Test that previously working authorized access still works}
```

---

## Section 8: Reviewer Action

```markdown
## Reviewer Action

**Recommended action:** {Approve / Request changes / Needs discussion}

**Confidence level:** {High — straightforward pattern application / Medium — some design decisions required / Low — needs architectural discussion}

**Open questions for reviewer:**
- {Any decisions that need human input — e.g., "Should we also add rate limiting to this endpoint?"}
- {Any uncertainty about existing code behavior}

---

**⏳ Awaiting reviewer action:**
- **Approve** → Save this report and advance to the next issue
- **Request changes** → Provide feedback and I'll revise
- **Skip** → Mark as skipped and advance
- **Stop** → End session and compile summary
```

---

## Session Summary Template

Used at the end of a `/suggest-fixes` session to compile all processed issues.

```markdown
# Fix Suggestion Session Summary — {repo name}

**Repository:** [{owner}/{repo}](https://github.com/{owner}/{repo})
**Date:** {date}
**Reviewer:** {user}
**Issues processed:** {count}

## Results

| # | Title | Priority | Action | Report |
|---|-------|----------|--------|--------|
| #{id} | {title} | {P0–P3} | {Approved / Revised / Skipped / Pending} | [{repo}-fix-{id}.md](link) |

## Summary Statistics

| Metric | Count |
|--------|-------|
| Issues processed | {n} |
| Fixes approved | {n} |
| Fixes revised | {n} |
| Issues skipped | {n} |
| Issues remaining | {n} |

## CWE Coverage

| CWE | Name | Issues Addressed |
|-----|------|-----------------|
| CWE-{id} | {name} | #{id}, #{id} |

## Next Steps

- {Any remaining issues to process in a follow-up session}
- {Any architectural changes that span multiple issues}
- {Recommended PR strategy — one PR per fix, or grouped by vulnerability domain}
```
