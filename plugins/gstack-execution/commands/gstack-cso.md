---
description: Security audit — OWASP, STRIDE, supply chain, secrets
allowed-tools: Read, Grep, Glob, Bash, Write, Agent
argument-hint: [--comprehensive | --diff | --scope domain]
---

Chief Security Officer audit. Adapted from gstack's `/cso` v2.0 methodology. Think like an attacker, report like a defender.

Read the gstack-execution skill for context. Then read `references/cso-phases.md` for the detailed audit protocol.

## Mode Resolution

Parse $ARGUMENTS:
- No args → Daily mode (8/10 confidence gate, zero noise)
- `--comprehensive` → Monthly deep scan (2/10 gate, surfaces more)
- `--diff` → Branch changes only (combinable with other flags)
- `--scope {domain}` → Focused audit on specific domain (e.g., "auth", "payments")

## Audit Sequence

Run these phases in order. Each phase uses Grep and Read tools for code analysis. Never modify code.

### Phase 0: Architecture Mental Model
Detect tech stack (package.json, Gemfile, requirements.txt, go.mod, Cargo.toml). Map application architecture: components, connections, trust boundaries, data flow. Express as brief architecture summary.

### Phase 1: Attack Surface Census
Map what an attacker sees. Count: public endpoints, authenticated routes, admin routes, API endpoints, file uploads, external integrations, background jobs, webhook handlers.

### Phase 2: Secrets Archaeology
Scan git history for leaked credentials. Check tracked `.env` files. Find CI configs with inline secrets. Patterns: AWS keys (AKIA), OpenAI (sk-), GitHub tokens (ghp_, gho_), Slack tokens (xoxb-, xoxp-).

### Phase 3: Dependency Supply Chain
Run available audit tools (npm audit, pip-audit, etc.). Check for install scripts in production deps. Verify lockfile existence and tracking.

### Phase 4: CI/CD Pipeline Security
Check GitHub Actions/GitLab CI for: unpinned third-party actions, pull_request_target with checkout, script injection via github.event, secrets as env vars.

### Phase 5: Infrastructure Shadow Surface
Check Dockerfiles (running as root, secrets as ARG), config files with prod credentials, IaC files for overpermissive IAM.

### Phase 6: Webhook & Integration Audit
Find webhook routes without signature verification. Check for disabled TLS verification. Audit OAuth scopes.

### Phase 7: LLM & AI Security
Check for: prompt injection vectors, unsanitized LLM output (dangerouslySetInnerHTML, v-html), unvalidated tool calls, AI API keys in code, eval of LLM output.

### Phase 8: OWASP Top 10
Targeted analysis for each OWASP category: broken access control, crypto failures, injection, insecure design, security misconfiguration, vulnerable components, auth failures, integrity failures, logging failures, SSRF.

### Phase 9: STRIDE Threat Model
For each major component: evaluate Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege.

### Phase 10: False Positive Filtering
Apply confidence gate (8/10 for daily, 2/10 for comprehensive). Filter test fixtures, documentation, placeholders. Mark findings as VERIFIED, UNVERIFIED, or TENTATIVE.

### Phase 11: Report

```
SECURITY POSTURE REPORT
═══════════════════════
Mode: {daily | comprehensive}
Scope: {full | diff | domain}
Stack: {detected technologies}

FINDINGS
────────
#  Sev    Conf  Status     Category        Finding                    File:Line
1  CRIT   9/10  VERIFIED   Secrets         AWS key in git history     .env:3
2  HIGH   8/10  VERIFIED   Supply Chain    postinstall in prod dep    package.json
...

TOTALS: {N} critical, {N} high, {N} medium
```

For each finding, include: description, exploit scenario, impact, and specific remediation.

Save report to workspace as `security-audit-{date}.md`.

## Rules
- Read-only. Never modify code.
- Zero noise > zero misses. Only report what survives the confidence gate.
- Every finding needs a concrete exploit scenario. "This pattern is insecure" is not a finding.
- Concrete always. Name the file, function, line number.
