# gstack Execution Plugin

**Version:** 0.5.0
**Author:** MoxyWolf LLC
**Based on:** [gstack](https://github.com/garrytan/gstack) by Garry Tan (MIT License), with adversarial-review framing from OpenAI's [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (Apache-2.0)
**Requires:** Claude in Chrome extension (for browser commands), Git (for code review/ship). Optional: `codex` CLI for real cross-model review in `/gstack-codex-review`.

## Overview

The factory floor. Product Orchestrator decides what to build. This plugin builds, reviews, tests, and ships it.

Adapted from Garry Tan's gstack — an open-source software factory that turns AI agents into a virtual engineering team. This Cowork adaptation routes browser operations through **Claude in Chrome** (the user's own logged-in browser), giving the QA and verification workflows real-session fidelity that headless tooling can't match.

## Commands

| Command | Description | Tools Used |
|---------|-------------|-----------|
| `/gstack-review` | Structural code review with two-pass checklist | Git + Grep |
| `/gstack-codex-review` | Adversarial review of just-committed code (real Codex or Claude fallback) | Git + Grep + `codex` CLI (optional) |
| `/gstack-investigate` | Root cause debugging with hypothesis testing | Git + Grep + Read |
| `/gstack-cso` | Security audit: OWASP + STRIDE + supply chain + secrets | Grep + Bash |
| `/gstack-ship` | Test → review → PR pipeline, worktree-isolated with a safe-fix/escalate contract | Git + Bash |
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
| Pressure-test a fresh commit | `/gstack-codex-review` (post-commit, pre-push) |
| Bug reported | `/gstack-investigate` → fix → `/gstack-review` |
| Pre-launch security | `/gstack-cso` |
| UI design needed | `/gstack-design` → build → `/gstack-review` |
| Verify deploy | `/gstack-browse` |
| Full QA pass | `/gstack-qa` |

## Reference Files

| File | Purpose |
|------|---------|
| `review-checklist.md` | Two-pass checklist: critical (blocking) + informational |
| `codex-review-methodology.md` | Adversarial review protocol (four lenses + defect floor) shared by both `/gstack-codex-review` engines |
| `cso-phases.md` | Detailed grep patterns, severity classifications, false positive rules |

## Attribution

This plugin adapts methodologies from [gstack](https://github.com/garrytan/gstack) by Garry Tan, licensed under MIT. The original gstack is a Claude Code skill library designed for terminal environments. This adaptation restructures the workflows for Cowork's plugin format and routes browser operations through Claude in Chrome instead of local Chromium.

`/gstack-ship` concept-ports two behaviors from [no-mistakes](https://github.com/kunchenguid/no-mistakes) by kunchenguid (MIT): validation runs in a disposable git worktree so the user's checkout is never touched, and every finding is classified under a safe-fix/escalate contract (mechanical fixes auto-apply, judgment calls stop and ask). Behaviors were re-specified for this pipeline; no code was vendored, so no upstream LICENSE file is carried. no-mistakes itself is a Go git-proxy runtime — worth evaluating directly for product repos that want a hard, unbypassable pre-push gate with a PR flow.

`/gstack-codex-review` additionally adapts the adversarial-review framing and scope/sizing logic from OpenAI's [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (Apache-2.0). Where that plugin always shells out to the local `codex` binary, the gstack version uses a hybrid engine: it delegates to real Codex (`codex exec`) when the CLI is present and logged in, and falls back to a Claude-run pass against the same methodology when it isn't — so the command works in the Cowork sandbox as well as from Claude Code CLI on a Mac.

## Version History

- **0.5.0** — `/gstack-ship` hardening, concept-ported from no-mistakes (MIT, ideas only): Step 1.5 runs validation in a disposable git worktree (teardown always, in-place fallback escalates everything), and a Fix Contract classifies every Step 2–4 finding as safe-mechanical (auto-applied, logged) or judgment-call (stop and ask; validation/error-handling/security/accessibility always escalate). Ship Report now itemizes fixes.
- **0.4.x** — ecc merge (`/ecc-build-fix`, `/ecc-learn`, `/ecc-skill-create`) and ponytail restraint wiring (Step 3.5 in `/gstack-ship`, references in both reviews).
- **0.3.0** — Add `/gstack-codex-review`: an adversarial review of just-committed code (post-commit, pre-push). Hybrid engine — real Codex via `codex exec` when the CLI is present, Claude fallback against the shared `codex-review-methodology.md` (four lenses + defect floor) when it isn't. Adapts the adversarial framing from OpenAI's codex-plugin-cc.
- **0.2.0** — Replace remote-Playwright browser testing with Claude in Chrome. Real browser, real session, no remote sandbox dependency. See `MIGRATION-rube-deprecation.md` at the repo root for context.
- **0.1.0** — Initial release. 7 commands (review, investigate, cso, ship, design, qa, browse). Remote Playwright via Rube.

## Composio fallback

For apps with no native MCP connector, this plugin can reach them through Composio's Tool Router when the Composio connector is installed. See the `composio` plugin.

## Governance

This plugin conforms to the [MoxyWolf AI Governance Manifesto](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md). Every skill declares a risk tier, and high-stakes actions route through a named Release Owner who signs before anything irreversible ships. See [`GOVERNANCE.md`](GOVERNANCE.md) for the per-skill tier table.

No auto-push to a protected branch — a named human owns the merge.

## Merged from ecc

Three commands are merged from [ecc](https://github.com/affaan-m/ECC) (MIT, © Affaan Mustafa): `/ecc-build-fix` (incremental build/type-error fix loop), `/ecc-learn` (extract reusable patterns from a session into candidate skills), and `/ecc-skill-create` (generate SKILL.md from git history; ecc's instinct/continuous-learning coupling removed). ecc's 67 agents and 271 skills were not vendored — only these three genuinely-new, low-coupling commands. See `NOTICE`.
