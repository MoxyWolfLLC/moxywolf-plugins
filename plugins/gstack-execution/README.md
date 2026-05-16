# gstack Execution Plugin

**Version:** 0.2.0
**Author:** MoxyWolf LLC
**Based on:** [gstack](https://github.com/garrytan/gstack) by Garry Tan (MIT License)
**Requires:** Claude in Chrome extension (for browser commands), Git (for code review/ship)

## Overview

The factory floor. Product Orchestrator decides what to build. This plugin builds, reviews, tests, and ships it.

Adapted from Garry Tan's gstack — an open-source software factory that turns AI agents into a virtual engineering team. This Cowork adaptation routes browser operations through **Claude in Chrome** (the user's own logged-in browser), giving the QA and verification workflows real-session fidelity that headless tooling can't match.

## Commands

| Command | Description | Tools Used |
|---------|-------------|-----------|
| `/gstack-review` | Structural code review with two-pass checklist | Git + Grep |
| `/gstack-investigate` | Root cause debugging with hypothesis testing | Git + Grep + Read |
| `/gstack-cso` | Security audit: OWASP + STRIDE + supply chain + secrets | Grep + Bash |
| `/gstack-ship` | Test → review → PR creation pipeline | Git + Bash |
| `/gstack-design` | Design system audit and component generation | Read + Write |
| `/gstack-qa` | Browser QA testing with bug fixing | Claude in Chrome |
| `/gstack-browse` | Quick page verification and health check | Claude in Chrome |

## Dependencies

**Required:**
- **Git** — available in Cowork sandbox
- **A mounted codebase** — select your project folder in Cowork

**Required for browser commands (`/gstack-qa`, `/gstack-browse`):**
- **Claude in Chrome** — install the Chrome extension and sign in. Browser ops run in your actual browser, so any auth state, cookies, and extensions are present. Tools used: `mcp__Claude_in_Chrome__navigate`, `get_page_text`, `read_page`, `javascript_tool`, `tabs_create_mcp`.

**Optional:**
- **gh CLI** — for automated PR creation in `/gstack-ship`
- **npm/bun** — for dependency auditing in `/gstack-cso`
- **Headless Playwright in workspace bash** — for fully unattended regression suites where a real browser is overkill. `npm i -g playwright && npx playwright install chromium` inside the sandbox.

## How It Pairs with Product Orchestrator

Product Orchestrator handles decisions (scope, architecture, GTM). This plugin handles execution. The connection point is Product Orchestrator's sprint protocol (Phase 3: Execute), which routes tasks here:

| Decision | Execution Path |
|----------|---------------|
| Feature scoped and approved | Code → `/gstack-review` → `/gstack-ship` |
| Bug reported | `/gstack-investigate` → fix → `/gstack-review` |
| Pre-launch security | `/gstack-cso` |
| UI design needed | `/gstack-design` → build → `/gstack-review` |
| Verify deploy | `/gstack-browse` |
| Full QA pass | `/gstack-qa` |

## Reference Files

| File | Purpose |
|------|---------|
| `review-checklist.md` | Two-pass checklist: critical (blocking) + informational |
| `cso-phases.md` | Detailed grep patterns, severity classifications, false positive rules |

## Attribution

This plugin adapts methodologies from [gstack](https://github.com/garrytan/gstack) by Garry Tan, licensed under MIT. The original gstack is a Claude Code skill library designed for terminal environments. This adaptation restructures the workflows for Cowork's plugin format and routes browser operations through Claude in Chrome instead of local Chromium.

## Version History

- **0.2.0** — Replace remote-Playwright browser testing with Claude in Chrome. Real browser, real session, no remote sandbox dependency. See `MIGRATION-rube-deprecation.md` at the repo root for context.
- **0.1.0** — Initial release. 7 commands (review, investigate, cso, ship, design, qa, browse). Remote Playwright via Rube.
