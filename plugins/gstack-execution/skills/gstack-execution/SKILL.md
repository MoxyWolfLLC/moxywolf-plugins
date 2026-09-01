---
name: gstack-execution
description: >
  This skill should be used when the user asks to "review my code", "audit this
  for security", "investigate this bug", "ship this feature", "create a PR",
  "security audit", "root cause analysis", "debug this", "code review",
  "design consultation", "run QA", "test this in a browser", "check this page",
  or any request that involves executing software development work on a codebase
  in the workspace. Adapted from Garry Tan's gstack (MIT licensed) for Cowork's
  environment, with browser testing via Claude in Chrome (the user's real
  logged-in browser). Pairs with the Product Orchestrator plugin: Product
  Orchestrator decides what to build, this plugin builds it.
version: 0.4.0
---

# gstack Execution Engine

Software development execution adapted from [gstack](https://github.com/garrytan/gstack) (MIT license) for Cowork. This plugin handles the build-review-ship cycle after Product Orchestrator has made the decisions about what to build and how.

## Core Principle

Product Orchestrator is the board of directors. This plugin is the factory floor. It doesn't debate what to build. It builds, reviews, tests, and ships what the board decided.

## Available Commands

| Command | What It Does | Cowork Compatibility |
|---------|-------------|---------------------|
| `/gstack-review` | Pre-landing code review with structural checklist | Full — git + grep |
| `/gstack-plan-review` | Pre-code plan-hardening loop over PLAN.md — bounded rounds, deadlock surfaced; real Codex when present, fresh-context Claude critic fallback | Full — git + grep (real Codex needs `codex` CLI on host) |
| `/gstack-codex-review` | Adversarial review of just-committed code; real Codex when present, Claude fallback | Full — git + grep (real Codex needs `codex` CLI on host) |
| `/gstack-verify` | Post-build verification of the implementation against its plan/spec — claim table, drift report; read-only, never gates | Full — git + grep + read |
| `/gstack-investigate` | Root cause debugging with hypothesis testing | Full — git + grep + read |
| `/gstack-cso` | Security audit (OWASP + STRIDE + supply chain) | Full — grep + code analysis |
| `/gstack-ship` | Test + review + PR creation pipeline | Partial — needs `gh` CLI for PR |
| `/gstack-design` | Design system consultation and generation | Full — analysis + code gen |
| `/gstack-qa` | Browser QA testing with bug fixing | Full — via Claude in Chrome |
| `/gstack-browse` | Browser-based page verification and dogfooding | Full — via Claude in Chrome |

## How It Connects to Product Orchestrator

When Product Orchestrator's sprint protocol reaches Phase 3 (Execute), it routes tasks to this plugin based on the execution routing table:

| Product Orchestrator Decision | gstack Command |
|------------------------------|----------------|
| "Build this feature" | `/gstack-plan-review` (harden the plan) → coding → `/gstack-review` → `/gstack-ship` |
| "Challenge this plan before we build" | `/gstack-plan-review` (pre-code, iterative, bounded) |
| "Challenge what I just committed" | `/gstack-codex-review` (adversarial, post-commit, pre-push) |
| "Did we build what we planned?" | `/gstack-verify` (implementation vs spec, after build) |
| "Fix this bug" | `/gstack-investigate` → fix → `/gstack-review` |
| "Security audit before launch" | `/gstack-cso` |
| "Design the UI" | `/gstack-design` → build → `/gstack-review` |
| "Ship what we built" | `/gstack-review` → `/gstack-ship` |
| "Test this in a browser" | `/gstack-qa` or `/gstack-browse` |
| "Verify the deploy" | `/gstack-browse` (navigate + snapshot + verify) |

## Environment Requirements

This plugin works within Cowork's sandboxed Bash environment. It needs:

- **Git** — for diff analysis, history, branch operations. Available in Cowork sandbox.
- **Grep/Read/Glob** — for code analysis. Native Cowork tools.
- **A codebase in the workspace** — mount the project folder via Cowork's folder selector.

Required for browser commands (`/gstack-qa`, `/gstack-browse`):
- **Claude in Chrome** — Chrome extension that exposes the user's real, logged-in browser to Claude. Tools used: `mcp__Claude_in_Chrome__navigate`, `get_page_text`, `read_page`, `read_console_messages`, `read_network_requests`, `javascript_tool`, `tabs_create_mcp`, `resize_window`, `shortcuts_execute`. If the extension isn't connected when a browser command runs, halt and ask the user to install and sign in — do not silently fall through to a headless tool.

Optional (enhances functionality):
- **gh CLI** — for PR creation in `/gstack-ship`. If not available, the plugin prepares everything and instructs the user to create the PR manually.
- **npm/bun** — for dependency auditing in `/gstack-cso`.

## Browser Operations via Claude in Chrome

gstack's original `/qa` and `/browse` skills use a compiled Chromium binary. In Cowork, we route all browser operations through the **Claude in Chrome** extension — Claude controls the user's real, signed-in Chrome session.

**Why this is better than headless tooling:**

- The user's authenticated sessions (LinkedIn, Gmail, Supabase dashboards, deployed staging URLs gated by SSO) are already live — no separate auth dance.
- Real cookies, real extensions, real network conditions — the QA verdict is what an actual user would see.
- DOM-aware tools (`javascript_tool`, `get_page_text`, `read_page`) extract structured data more reliably than screen-scraping a headless screenshot.

**Standard session pattern:**

```
1. tabs_create_mcp                       — open a fresh tab
2. navigate(url)                          — go to the target
3. read_console_messages / read_network_requests   — capture errors
4. get_page_text / read_page              — pull rendered content
5. javascript_tool(code)                  — run structural / a11y checks in-page
6. form_input / shortcuts_execute         — drive interactions
7. resize_window(w, h)                    — responsive checks
```

**Capturing visuals:** Claude in Chrome ships `gif_creator` for short interaction recordings. For single still frames, take a native screenshot with `mcp__computer-use__screenshot` while the Chrome window is frontmost.

**Headless fallback (rare):** for fully unattended runs (scheduled regression suites with no human around to host Chrome), install Playwright inside the workspace bash sandbox:

```bash
npm i -g playwright
npx playwright install chromium
node /path/to/regression-suite.js
```

This is the legacy code path. Prefer Claude in Chrome whenever a real session is available.

## Verification Discipline — what "it works" is allowed to mean

Every one of these came from shipping something that was correct in isolation and
broken on the path the user takes. They are checks, not values: each either ran
or it didn't, and the report says which.

**1. Verify through the user's path, under the user's conditions.** Not the
artifact — the path. A database function tested in the SQL editor runs as a
different role than the one the API uses (Supabase enables `pg_safeupdate` for
PostgREST, so a bare `DELETE`/`UPDATE` that passes in the editor is refused
through the button). A page section tested by reading the source is not tested;
load the deployed URL. A rule fixed in a database table is inert if the code
reads a hardcoded constant. Exercise the real path or say plainly which part is
unverified.

**2. Never say "press" without a URL, and not before the control renders.**
Naming a button is not directions. Give the address, and confirm the control
actually appears in that state first — a control built into an unreachable
branch looks finished in the diff and does not exist to the user.

**3. Read the exit code you actually mean.** `$?` after a pipeline is the LAST
stage's status. A command piped through `sed` (for example to redact a token)
reports `sed`'s success, so a crashed process reads as `rc=0`. Use
`${PIPESTATUS[0]}`, or run the command unpiped and post-process separately.

**4. Count before you characterize.** Never describe data as noisy, clean,
duplicated or safe without the query behind it — especially when the
characterization is the argument for overriding the user's judgment. "Mostly
junk" that turns out to be two rows out of sixty-eight is not a summary, it is a
guess wearing a summary's clothes.

**5. Before changing a rule, find its second home.** Config tables that mirror
code constants, glossaries that define the same term twice, `CREATE OR REPLACE
FUNCTION` with a changed signature (which OVERLOADS rather than replaces, leaving
the old one to win the call). Grep for the value, not just the file you're in.

**6. Say what you verified and what you didn't.** As a format, every time — the
sentence is visible when it's missing, which is what makes it work where a
resolution doesn't. "Typechecked but not exercised through the API" is a complete
and useful report. "Done" is not.

An error caught here costs tokens. An error the user catches costs their
attention and their trust in everything next to it. Run the checks before
speaking, not after being corrected.

## Execution Voice

Adapted from gstack's communication philosophy:

- Lead with the point. State what it does, why it matters, what changes.
- Sound like a builder. Someone who shipped code today and verifies it works.
- Concrete always. Name the file, function, line number. Give exact commands.
- Connect to user outcomes. Why does this finding matter to the end user?
- User sovereignty. Present recommendations. Never impose.
- No AI vocabulary. No "delve", "crucial", "robust", "comprehensive", "landscape."
- Short paragraphs. Mix one-liners with 2-3 sentence blocks.

## What This Plugin Does NOT Do

- **No deployment.** `/gstack-ship` prepares PRs but doesn't merge or deploy. Use your CI/CD pipeline.
- **No planning.** gstack's `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, and `/plan-design-review` are replaced by Product Orchestrator's deliberation engine. Don't duplicate planning here.
- **No code modification during review or security audit.** `/gstack-review`, `/gstack-codex-review`, and `/gstack-cso` are read-only analysis. They produce findings and recommendations. Fixes are a separate step.

## Completeness Principle

Borrowed from gstack: AI makes completeness near-free. Always do the complete thing. A full security audit takes gstack 15 minutes. A full code review takes 5. Don't cut corners when the marginal cost is near zero.

| Task | Human Team | AI + gstack | Compression |
|------|-----------|-------------|-------------|
| Code review | 2 hours | 5 min | ~25x |
| Security audit | 2 days | 15 min | ~100x |
| Bug investigation | 4 hours | 15 min | ~16x |
| Design consultation | 1 day | 10 min | ~50x |

## Composio fallback — apps with no native MCP

If a step in this skill needs an app or service that has no native Cowork MCP connector — for example Notion, Linear, Jira, HubSpot, Salesforce, Stripe, Airtable, or Calendly — and the Composio connector is installed, reach the app through Composio's Tool Router rather than giving up or asking the user to do it by hand. Discover the tool with `COMPOSIO_SEARCH_TOOLS`, authenticate with `COMPOSIO_MANAGE_CONNECTIONS` if needed, then execute. See the `composio` plugin's `composio-tools` skill for the full pattern.

Native MCP connectors still come first — this is a fallback for reach, not a replacement for the native paths this skill already uses.
