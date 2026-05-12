# CSO Audit Phases — Detailed Protocol

Extended reference for `/gstack-cso`. The command file contains the execution flow. This file contains the detailed patterns, grep searches, and severity classifications for each phase.

## Confidence Gates

**Daily Mode (default):** 8/10 minimum. Zero noise. Only report what you could write a proof-of-concept for.

**Comprehensive Mode:** 2/10 minimum. Surface anything that might be real. Mark sub-8 findings as TENTATIVE.

## Phase 0: Stack Detection Patterns

Detect via file presence:
- `package.json` + `tsconfig.json` → Node/TypeScript
- `Gemfile` → Ruby
- `requirements.txt` or `pyproject.toml` → Python
- `go.mod` → Go
- `Cargo.toml` → Rust
- `pom.xml` or `build.gradle` → JVM

Framework detection (check dependency files):
- Next.js, Express, Fastify, Hono (Node)
- Django, FastAPI, Flask (Python)
- Rails (Ruby)
- Gin (Go)
- Spring Boot (JVM)

Stack detection determines scan PRIORITY, not scope. Always run a catch-all pass after targeted scanning.

## Phase 2: Secret Patterns

### Known Prefixes (high confidence)
| Pattern | Service | Severity |
|---------|---------|----------|
| `AKIA[A-Z0-9]{16}` | AWS Access Key | CRITICAL |
| `sk-[a-zA-Z0-9]{48}` | OpenAI API Key | CRITICAL |
| `sk_live_[a-zA-Z0-9]+` | Stripe Live Key | CRITICAL |
| `ghp_[a-zA-Z0-9]{36}` | GitHub Personal Token | CRITICAL |
| `gho_[a-zA-Z0-9]+` | GitHub OAuth Token | CRITICAL |
| `github_pat_[a-zA-Z0-9]+` | GitHub Fine-Grained Token | CRITICAL |
| `xoxb-[0-9]+-[a-zA-Z0-9]+` | Slack Bot Token | CRITICAL |
| `xoxp-[0-9]+-[a-zA-Z0-9]+` | Slack User Token | CRITICAL |
| `SG\.[a-zA-Z0-9]+` | SendGrid API Key | HIGH |
| `sq0atp-[a-zA-Z0-9]+` | Square Access Token | CRITICAL |

### False Positive Exclusions
- Placeholders: "your_key_here", "changeme", "TODO", "xxx", "REPLACE_ME"
- Test fixtures in `test/`, `__tests__/`, `spec/` directories
- `.env.example` or `.env.sample` files (unless values look real)
- Rotated secrets STILL flagged (they were exposed in git history)

## Phase 4: CI/CD Severity Classifications

| Finding | Severity | Condition |
|---------|----------|-----------|
| Unpinned third-party actions | HIGH | Any `uses:` without `@{sha}` |
| First-party `actions/*` unpinned | MEDIUM | Lower risk but still flag |
| `pull_request_target` + PR checkout | CRITICAL | Fork PRs get write access |
| `pull_request_target` without checkout | SAFE | Not exploitable |
| Script injection via `${{ github.event }}` | CRITICAL | In `run:` steps |
| Secrets as `env:` vars | HIGH | Should use `with:` blocks |
| Missing CODEOWNERS on workflows | MEDIUM | No review required for changes |

## Phase 7: LLM Security Grep Patterns

Search for these patterns using the Grep tool:

**Prompt injection vectors:**
- String interpolation near "system" or "prompt": `system.*\$\{|system.*\+.*user|prompt.*\$\{`
- Template literals with user content in system messages

**Unsanitized LLM output:**
- `dangerouslySetInnerHTML` with AI response data
- `v-html` with AI response data
- `innerHTML` assignment from AI response
- `.html()` jQuery calls with AI data

**Unvalidated tool calls:**
- `tool_choice`, `function_call`, `tools=` without subsequent validation
- Direct execution of AI-selected tool names without allowlist check

**API key exposure:**
- `sk-` followed by 20+ alphanumeric characters outside `.env` files
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in code (not env vars)

## Phase 8: OWASP Grep Patterns by Category

### A01 — Broken Access Control
- `skip_before_action`, `skip_authorization` (Rails)
- Routes missing `@login_required` (Django)
- `params[:id]`, `req.params.id` without ownership check
- Missing `.where(user_id:)` scope on queries

### A02 — Crypto Failures
- `MD5`, `SHA1` (weak hashing for security contexts)
- `DES`, `ECB` mode (weak encryption)
- Hardcoded keys in source

### A03 — Injection
- Raw SQL: `.execute()`, `.raw()`, `query()` with string interpolation
- Command injection: `system()`, `exec()`, `spawn()`, `popen()` with user input
- Template injection: `render()` with user-controlled template strings

### A05 — Security Misconfiguration
- CORS: `Access-Control-Allow-Origin: *` in production
- Debug mode: `DEBUG=true`, `NODE_ENV=development` in prod configs
- Verbose error messages exposing stack traces

### A07 — Auth Failures
- JWT without expiration check
- Session tokens without rotation
- Missing MFA enforcement for admin accounts

### A10 — SSRF
- URL construction from user input: `fetch(userUrl)`, `requests.get(url)` where url is user-controlled
- Internal service URLs constructable from external input

## Hard Exclusions (Never Report)

1. Denial of Service / rate limiting (exception: LLM cost amplification)
2. Secrets stored encrypted on disk with proper permissions
3. Memory/CPU/file descriptor exhaustion
4. Input validation on non-security fields without proven impact
5. Missing hardening without concrete vulnerability
6. Race conditions without concrete exploit path
7. Regex complexity on non-user input
8. Security concerns in documentation files (exception: SKILL.md files — those are executable)
9. Git history secrets committed AND removed in same initial PR
10. Dependency CVEs with CVSS < 4.0 and no known exploit
11. Docker issues in `Dockerfile.dev` or `Dockerfile.local`

## Finding Template

```markdown
## Finding {N}: {Title} — {File}:{Line}

**Severity:** CRITICAL | HIGH | MEDIUM
**Confidence:** {N}/10
**Status:** VERIFIED | UNVERIFIED | TENTATIVE
**Phase:** {N} — {Phase Name}
**Category:** {Secrets | Supply Chain | CI/CD | Infrastructure | Integrations | LLM Security | OWASP A01-A10}

**Description:** {What's wrong — one paragraph}

**Exploit Scenario:**
1. Attacker does {step 1}
2. This causes {step 2}
3. Result: {what the attacker gains}

**Impact:** {What's at risk — data, access, money, reputation}

**Remediation:**
{Specific fix with code example. Name the file, show the change.}
```
