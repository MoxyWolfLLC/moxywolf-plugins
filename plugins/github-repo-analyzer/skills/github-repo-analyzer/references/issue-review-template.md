# Structured Issue Review — Report Template

## Report Metadata

```
# {Repo Name} Repository — Structured Issue Review

**Repository:** [{owner}/{repo}](https://github.com/{owner}/{repo})
**Date:** {date}
**Reviewer:** Claude (Cowork Mode) — commissioned by {user}
**Scope:** All {total} issues ({open} open, {closed} closed), with deep-dive security classification
```

---

## 1. Executive Summary

Provide a concise narrative (2–3 paragraphs) covering:

- Total issue count, open/closed breakdown
- How many carry the `security` label, with priority distribution (P0–P3)
- How many security issues are closed — and whether closures had code remediation
- The major security threat domains identified (credential storage, authorization, billing, etc.)
- Any patterns of team pushback or dismissal

### Issue Inventory Table

| Priority | Total | Open | Closed | Security-tagged |
|----------|-------|------|--------|-----------------|
| P0       |       |      |        |                 |
| P1       |       |      |        |                 |
| P2       |       |      |        |                 |
| P3       |       |      |        |                 |
| Unlabeled|       |      |        |                 |
| **Total**|       |      |        |                 |

### Closure Audit Warning (if applicable)

> **⚠ CLOSURE AUDIT:** {n} closed security issues were dismissed as "false positives" without code remediation. {n} pull requests exist in the repository history. See the **Closure Audit Addendum** at the end of this report.

---

## 2. Security Clusters

Group security issues by shared vulnerability domain / attack surface. For each cluster:

### Cluster Template

```markdown
## Security Cluster {N}: {Cluster Name}

### Issues in this cluster

| # | Title | State | Priority |
|---|-------|-------|----------|
| [#{id}](url) | {title} | {open/closed} | {P0-P3} |

### Vulnerability Analysis

**Core Finding:** {1–2 sentence summary of the vulnerability pattern}

**Affected Files:**
- {file path} — {what role this file plays}

### Security Classification

| Framework | Classification | Description |
|-----------|---------------|-------------|
| **CWE-{id}** | {name} | {how it applies} |
| **OWASP Top 10:2025 {code}** | {name} | {how it applies} |
| **OWASP API Security 2023 {code}** | {name} | {how it applies} |
| **NIST SP 800-53 {control}** | {name} | {how it applies} |

### Recommended Approach vs. Current Approach

| Aspect | Industry Best Practice | Current Implementation |
|--------|----------------------|------------------------|
| {aspect} | {what should be done} | {what the repo does} |

### Team Pushback Assessment

**@{user} on #{id}:** *"{quote}"*

**Assessment:** {technical analysis of the claim — why it is or isn't valid}

**Verdict:** {Not a false positive / Partially valid / Valid false positive}
```

---

## 3. Non-Security Issue Categories (optional)

When `--security-only` is NOT set, include a summary table of non-security issues grouped by category:

| Category | Count | Open | Closed | Key Themes |
|----------|-------|------|--------|------------|
| Billing/Payments | | | | |
| Infrastructure | | | | |
| Code Quality | | | | |
| Product/Feature | | | | |
| Documentation | | | | |

Brief narrative for each category noting the most impactful issues.

---

## 4. Closure Audit Addendum

Include this section when `--include-closure-audit` is set or when closed security issues are detected.

### Methodology

Describe the audit approach:
- GitHub Events API analysis for linked PRs and commits
- Timeline reconstruction of closure events
- Cross-reference of commit messages against issue numbers

### Findings Summary

| Metric | Count |
|--------|-------|
| Closed security issues audited | |
| Linked pull requests found | |
| Linked commits found | |
| PullRequestEvents in repo history | |
| Justified closures | |
| Unjustified closures | |

### Mass-Closure Timeline (if applicable)

| Time (UTC) | Actor | Action | Issue | Title |
|------------|-------|--------|-------|-------|
| {timestamp} | {user} | {closed/reopened} | #{id} | {title} |

### Issue-by-Issue Audit

For each closed security issue:

```markdown
#### Issue #{id}: {title}

- **Closed by:** @{user} on {date}
- **Linked PRs:** {count — typically 0}
- **Linked commits:** {count — typically 0}
- **Dismissal rationale:** "{quote from comment}"
- **Technical rebuttal:** {why the dismissal is invalid, citing specific CWE/architectural facts}
- **Verdict:** ❌ Not a false positive — recommend reopening
```

### Pattern Analysis

Identify systemic patterns across the closures:
- Absence of code review culture (no PRs ever)
- Reflexive dismissal of automated findings
- Misapplication of specific technologies as catch-all mitigations (e.g., "RLS handles it")
- Time-compressed closure suggesting bulk dismissal rather than individual analysis

### Recommendation

State clearly whether the closed issues should be reopened, with justification.

---

## 5. Remediation Roadmap

Prioritized action items:

### Critical (address immediately)
1. {action} — resolves #{id}, #{id}

### High (address within sprint)
1. {action} — resolves #{id}

### Medium (plan for upcoming sprint)
1. {action} — resolves #{id}

### Low (backlog)
1. {action} — resolves #{id}

---

## Classification Reference

### CWE (Common Weakness Enumeration)
Source: https://cwe.mitre.org/

Common CWEs for application security:
- CWE-200: Exposure of Sensitive Information
- CWE-256: Plaintext Storage of a Password
- CWE-294: Authentication Bypass by Capture-replay
- CWE-306: Missing Authentication for Critical Function
- CWE-312: Cleartext Storage of Sensitive Information
- CWE-352: Cross-Site Request Forgery
- CWE-522: Insufficiently Protected Credentials
- CWE-532: Insertion of Sensitive Information into Log File
- CWE-601: URL Redirection to Untrusted Site
- CWE-639: Authorization Bypass Through User-Controlled Key (IDOR)
- CWE-862: Missing Authorization
- CWE-942: Permissive Cross-domain Policy (CORS)

### OWASP Top 10:2025
Source: https://owasp.org/Top10/

- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable and Outdated Components
- A07: Identification and Authentication Failures
- A08: Software and Data Integrity Failures
- A09: Security Logging and Monitoring Failures
- A10: Server-Side Request Forgery

### OWASP API Security Top 10:2023
Source: https://owasp.org/API-Security/

- API1: Broken Object Level Authorization (BOLA)
- API2: Broken Authentication
- API3: Broken Object Property Level Authorization
- API4: Unrestricted Resource Consumption
- API5: Broken Function Level Authorization
- API6: Unrestricted Access to Sensitive Business Flows
- API7: Server Side Request Forgery
- API8: Security Misconfiguration
- API9: Improper Inventory Management
- API10: Unsafe Consumption of APIs

### NIST SP 800-53 (Rev. 5) — Selected Controls
Source: https://csf.tools/reference/nist-sp-800-53/

- AC-3: Access Enforcement
- AC-4: Information Flow Enforcement
- AC-6: Least Privilege
- AU-3: Content of Audit Records
- IA-5: Authenticator Management
- SC-8: Transmission Confidentiality and Integrity
- SC-12: Cryptographic Key Establishment and Management
- SC-13: Cryptographic Protection
- SC-28: Protection of Information at Rest
- SI-10: Information Input Validation
