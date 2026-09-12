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
version: 0.18.0
---

# gstack Execution Engine

Software development execution adapted from [gstack](https://github.com/garrytan/gstack) (MIT license) for Cowork. This plugin handles the build-review-ship cycle after Product Orchestrator has made the decisions about what to build and how.

## Core Principle

**All coding goes through `/gstack-build`** (Dorian, 2026-09-11; canonical rule in `Taskade/_Shared Files/_shared-memory/feedback_all_coding_via_gstack_build.md`). A request to write or change code starts by reading the repo's `DESIGN.md`; if the ask is not covered, the doc is amended with approval before any code; every push is verified on the remote and pulled back into the local clone; nothing is done until the other tool has reviewed it clean.

Product Orchestrator is the board of directors. This plugin is the factory floor. It doesn't debate what to build. It builds, reviews, tests, and ships what the board decided.

## Available Commands

| Command | What It Does | Cowork Compatibility |
|---------|-------------|---------------------|
| `/gstack-design-doc` | Create or refresh a repo's `DESIGN.md` as an editable artifact; on approval, written to the repo (canonical) and Taskade `06 – Engineering` (mirror), committed, pushed, verified, pulled back; asks for either directory if it is not mounted | Full — Artifact tool + git |
| `/gstack-build` | **The coding loop.** Design doc first (`DESIGN.md`, canonical in the repo, mirrored to Taskade), build one item against its acceptance criteria or amend the doc with approval first, feature branch → push → verify → pull back, `/gstack-peer-review` until clean, human release handoff, record merge before marking done | Full — git + the other tool's CLI for the review |
| `/gstack-review` | Pre-landing code review with structural checklist | Full — git + grep |
| `/gstack-plan-review` | Pre-code plan-hardening loop over PLAN.md — bounded rounds, deadlock surfaced; real Codex when present, fresh-context Claude critic fallback | Full — git + grep (real Codex needs `codex` CLI on host) |
| `/gstack-peer-review` | Bounded cross-tool review at an implementation checkpoint: the other tool (Codex ↔ Claude Code) reviews pinned commits against a fixed contract; one review + two fix-verification passes; explicit outcomes, never a same-tool substitute | Needs the *other* tool's CLI on PATH (`codex` or `claude`), else `review_unavailable` |
| `/gstack-codex-review` | Compatibility alias for `/gstack-peer-review --builder claude` | Same |
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
| "Build this feature" / any coding request | `/gstack-build` (design doc gate → build → push + pull back → `/gstack-peer-review` loop → human release handoff). `/gstack-plan-review` hardens a larger design first; `/gstack-ship` remains the PR pipeline for repos that land through PRs |
| "Challenge this plan before we build" | `/gstack-plan-review` (pre-code, iterative, bounded) |
| "Have the other tool review this checkpoint" | `/gstack-peer-review --builder <tool>` (bounded, cross-tool, fixes blockers in scope) |
| "Did we build what we planned?" | `/gstack-verify` (implementation vs spec, after build) |
| "Fix this bug" | `/gstack-investigate` → fix → `/gstack-review` |
| "Security audit before launch" | `/gstack-cso` |
| "Design the UI" | `/gstack-design` → build → `/gstack-review` |
| "Ship what we built" | `/gstack-review` → `/gstack-ship` |
| "Test this in a browser" | `/gstack-qa` or `/gstack-browse` |
| "Verify the deploy" | `/gstack-browse` (navigate + snapshot + verify) |

## E2E gate (Endform)

Every Vercel-deployed repo carries `.github/workflows/endform-e2e.yml` (template in `references/endform-e2e.yml`): on each pull request and push to `main` it waits for the Vercel preview, exports its URL as `BASE_URL`, and runs the Playwright suite with `npx endform@latest test` on Endform's cloud runners. `/gstack-build` checks for the file before building and writes it (with the repo's Vercel project name and package manager) when missing; `scripts/endform_workflow.py check|ensure|scaffold` (scaffold adds the minimum Playwright suite and installs under `NODE_ENV=development`). Results are read from the PR's `e2e` check-run and job log; there is no Endform connector. The Endform run on the final head is part of the loop's exit condition for web items. Set by Dorian 2026-09-11.

## Model floors

When a command in this plugin shells out to a CLI: Codex runs **Astra (`gpt-6-astra`) or higher** (`-m gpt-6-astra`), Claude Code runs **Opus 5 or higher** (`--model opus`, which resolves to `claude-opus-5`; Fable qualifies). `scripts/peer_review.py` enforces this and reports `model_below_floor`; the plan-review protocol carries the flags in its commands. Set by Dorian 2026-09-11.

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

**Canonical text: `references/verification-checks.md`.** That file is the single
home for these checks; the plugin's SessionStart hook injects it verbatim, so
they arrive whether or not this skill was invoked — which matters, because every
mistake they describe was made without invoking it.

The six, in short:

1. **Verify through the user's path, under the user's conditions** — not the artifact. A different role, a different environment, or reading source instead of loading the page all mean untested.
2. **Never say "press" without a URL**, and not before the control renders.
3. **Read the exit code you mean** — `${PIPESTATUS[0]}`, not `$?` after a pipe.
4. **Count before you characterize** — especially when the characterization is the argument for overriding the user.
5. **Before changing a rule, find its second home.**
6. **Say what you verified and what you didn't**, as a format.

Read the reference for the worked reasoning behind each. Do not restate them
elsewhere — a rule with two homes is exactly what check 5 is about.

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

## Executable task graphs

CSO, verify and independent multi-repository review use `scripts/task_graph.py` and the static declarations in `workflows/`. Follow [the task-graph contract](references/task-graph-contract.md) for permission packets, frozen inputs, bounded concurrency, resume and oversight. The commands execute the graph; prose-only parallel review is not a substitute.
