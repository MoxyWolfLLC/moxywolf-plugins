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
version: 0.2.0
---

# gstack Execution Engine

Software development execution adapted from [gstack](https://github.com/garrytan/gstack) (MIT license) for Cowork. This plugin handles the build-review-ship cycle after Product Orchestrator has made the decisions about what to build and how.

## Core Principle

Product Orchestrator is the board of directors. This plugin is the factory floor. It doesn't debate what to build. It builds, reviews, tests, and ships what the board decided.

## Available Commands

| Command | What It Does | Cowork Compatibility |
|---------|-------------|---------------------|
| `/gstack-review` | Pre-landing code review with structural checklist | Full — git + grep |
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
| "Build this feature" | Manual coding → `/gstack-review` → `/gstack-ship` |
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
- **No code modification during review or security audit.** `/gstack-review` and `/gstack-cso` are read-only analysis. They produce findings and recommendations. Fixes are a separate step.

## Completeness Principle

Borrowed from gstack: AI makes completeness near-free. Always do the complete thing. A full security audit takes gstack 15 minutes. A full code review takes 5. Don't cut corners when the marginal cost is near zero.

| Task | Human Team | AI + gstack | Compression |
|------|-----------|-------------|-------------|
| Code review | 2 hours | 5 min | ~25x |
| Security audit | 2 days | 15 min | ~100x |
| Bug investigation | 4 hours | 15 min | ~16x |
| Design consultation | 1 day | 10 min | ~50x |
