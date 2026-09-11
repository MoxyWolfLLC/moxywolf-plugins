# gstack Execution Plugin

**Version:** 0.5.0
**Author:** MoxyWolf LLC
**Based on:** [gstack](https://github.com/garrytan/gstack) by Garry Tan (MIT License), with adversarial-review framing from OpenAI's [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (Apache-2.0)
**Requires:** Claude in Chrome extension (for browser commands), Git (for code review/ship). Optional: `codex` CLI for real cross-model review in `/gstack-codex-review` and `/gstack-plan-review`.

## Overview

The factory floor. Product Orchestrator decides what to build. This plugin builds, reviews, tests, and ships it.

Adapted from Garry Tan's gstack — an open-source software factory that turns AI agents into a virtual engineering team. This Cowork adaptation routes browser operations through **Claude in Chrome** (the user's own logged-in browser), giving the QA and verification workflows real-session fidelity that headless tooling can't match.

## Commands

| Command | Description | Tools Used |
|---------|-------------|-----------|
| `/gstack-design-doc` | Create or refresh `DESIGN.md` as an editable artifact; approval writes it to the repo and Taskade, commits, pushes, pulls back | Artifact + Git |
| `/gstack-build` | The coding loop: design doc gate → build one item → push + verify + pull back → cross-tool review until clean → human release handoff → record merge before done | Git + `codex`/`claude` CLI |
| `/gstack-review` | Structural code review with two-pass checklist | Git + Grep |
| `/gstack-plan-review` | Pre-code plan-hardening loop over PLAN.md (real Codex or fresh-context Claude critic) | Git + Grep + `codex` CLI (optional) |
| `/gstack-peer-review` | Bounded cross-tool review loop at an implementation checkpoint (Codex ↔ Claude Code), fixed contract, explicit outcomes | Git + the other tool's CLI (`codex` or `claude`) |
| `/gstack-codex-review` | Compatibility alias for `/gstack-peer-review --builder claude` | Same |
| `/gstack-verify` | Post-build check of the implementation against its plan/spec (claim table + drift report) | Git + Grep + Read |
| `/gstack-investigate` | Root cause debugging with hypothesis testing | Git + Grep + Read |
| `/gstack-cso` | Security audit: OWASP + STRIDE + supply chain + secrets | Grep + Bash |
| `/gstack-ship` | Test → review → PR pipeline, worktree-isolated with a safe-fix/escalate contract; the Ship Report carries required Verified / Unverified lines | Git + Bash |
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
| `endform-e2e.yml` | The Endform E2E workflow every Vercel-deployed repo carries; `scripts/endform_workflow.py` checks for it and writes it with the repo's Vercel project name and package manager |
| `design-doc-editor.html` | The editable artifact page `/gstack-design-doc` publishes: Markdown editor + preview, Save version, Mark approved; the page stores the document as data and republishes itself |
| `design-doc-template.md` | `DESIGN.md` skeleton: goal, constraints and settled decisions (the review exclusions), items with acceptance criteria and status, amendments log |
| `peer-review-contract.md` | The peer review contract: packet, direct-dependency scope, blocking criterion, finding schema, loop, dispositions, outcomes; `scripts/peer_review.py` enforces the mechanical parts |
| `codex-review-methodology.md` | Adversarial lenses (approach, design, assumptions, failure modes); now the reference behind `/gstack-plan-review`, where approach challenges belong |
| `plan-review-protocol.md` | Bounded plan-hardening loop (iteration with memory, deadlock handling, both engines' mechanics) behind `/gstack-plan-review` |
| `cso-phases.md` | Detailed grep patterns, severity classifications, false positive rules |
| `verification-checks.md` | The six verification checks — canonical text, injected verbatim by the SessionStart hook (or, in cloud sessions, by the first-prompt fallback) |

## Attribution

This plugin adapts methodologies from [gstack](https://github.com/garrytan/gstack) by Garry Tan, licensed under MIT. The original gstack is a Claude Code skill library designed for terminal environments. This adaptation restructures the workflows for Cowork's plugin format and routes browser operations through Claude in Chrome instead of local Chromium.

`/gstack-ship` concept-ports two behaviors from [no-mistakes](https://github.com/kunchenguid/no-mistakes) by kunchenguid (MIT): validation runs in a disposable git worktree so the user's checkout is never touched, and every finding is classified under a safe-fix/escalate contract (mechanical fixes auto-apply, judgment calls stop and ask). Behaviors were re-specified for this pipeline; no code was vendored, so no upstream LICENSE file is carried. no-mistakes itself is a Go git-proxy runtime — worth evaluating directly for product repos that want a hard, unbypassable pre-push gate with a PR flow.

`/gstack-codex-review` additionally adapts the adversarial-review framing and scope/sizing logic from OpenAI's [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) (Apache-2.0). Where that plugin always shells out to the local `codex` binary, the gstack version uses a hybrid engine: it delegates to real Codex (`codex exec`) when the CLI is present and logged in, and falls back to a Claude-run pass against the same methodology when it isn't — so the command works in the Cowork sandbox as well as from Claude Code CLI on a Mac.

`/gstack-plan-review` concept-ports the Act 2 plan-hardening loop from Chase AI's [grill-me-codex](https://github.com/chaseai-yt/grill-me-codex) (MIT), which builds on Matt Pocock's [grill-me](https://github.com/mattpocock/skills) (MIT). The bounded-rounds/deadlock discipline is theirs; the hybrid engine and arbitration rules are gstack's. No code copied.

## Version History

- **0.15.1** — Second live repo (oc-website PR #8, `1 passed, 1 skipped` on the Vercel preview) taught `endform_workflow.py` two things: `ensure` now reads the env var the repo's `playwright.config` uses for `baseURL` (oc-website reads `OC_E2E_BASE_URL`) and exports the preview URL under that name; a pnpm repo without `packageManager` in `package.json` is refused with the fix spelled out, because `pnpm/action-setup` fails with "No pnpm version is specified". `/gstack-build` adds: an existing suite whose only spec skips without its backing service does not cover the deploy, so a smoke spec is still required; and when local verification needs an `.env.local` the repo does not carry, the PR's preview run is the verification and the commit says so.
- **0.15.0** — Endform gate hardened from the first live run (cki PR #81, 2 passed on the Vercel preview). `endform_workflow.py scaffold` adds the minimum Playwright suite to a repo that has none (package.json with `@playwright/test` only, `playwright.config.ts` on `BASE_URL`, `e2e/smoke.spec.ts` with a `--title-regex`) and installs under `NODE_ENV=development`, refusing a lockfile that lost the devDependency; `check` warns when the shell exports `NODE_ENV=production`. `/gstack-build` says where results live (the PR's `e2e` check-run and the job log with the suite-run URL; no Endform connector exists or is needed), how to open the PR without `gh` (REST with the vault PAT), and to run Playwright through `./node_modules/.bin/playwright`, never `npx playwright`, which resolves a global package on the team Macs.
- **0.14.0** — **E2E gate via Endform.** Every Vercel-deployed repo carries `.github/workflows/endform-e2e.yml` (Dorian's file, `references/endform-e2e.yml`): on pull requests and pushes to `main`, wait for the Vercel preview, export `BASE_URL`, run the Playwright suite with `npx endform@latest test`. `/gstack-build` Step 3 now runs `scripts/endform_workflow.py check` first and, when the file is missing, `ensure --project <vercel-project>` (project looked up through the Vercel connector, install step matched to the lockfile: pnpm verbatim, `npm ci`, or bun), commits it alone as `ci: add Endform e2e workflow`, pushes, pulls back, then builds. Web acceptance criteria name the spec that proves them; the Endform run URL on the final head is the packet's test evidence and part of the exit condition. Repos with no Vercel project get no workflow and say so in their design doc. Selftest covers missing/present, no-overwrite, and the three install variants.
- **0.13.0** — `/gstack-design-doc`: the design document as an **editable artifact**. Drafts `DESIGN.md` from the repo, the project's PRDs and specs, the team-shared rules, and the user's notes; publishes it in `references/design-doc-editor.html` (Markdown editor, live preview, Save version, Mark approved; the page is the record and republishes itself via the `artifact` capability). On approval the Markdown is written to `<repo>/DESIGN.md` (canonical) and `<taskade>/06 – Engineering/DESIGN-<repo>.md` (mirror), committed as `design: …`, pushed, `ls-remote`-verified, pulled back. Both directories are resolved from the session's mounted folders; a missing one is requested, and the user is asked for the path if the request is declined. `/gstack-build` Step 1 now routes a missing doc here. Proving run 2026-09-11: the moxywolf-plugins draft published as version 1 of its editor page.
- **0.12.0** — `/gstack-build`: **all coding follows one loop** (Dorian, 2026-09-11). A `DESIGN.md` at the repo root is canonical (mirrored to Taskade `06 – Engineering/DESIGN-<repo>.md`) and carries the goal, the constraints and settled decisions, and items with checkable acceptance criteria. A coding request is matched to an item; if it is not covered or conflicts, Claude drafts the amendment, Dorian approves, the doc commit lands first, and only then code. Build on `build/<item-id>-<slug>`; commit; push with the vault PAT; verify `ls-remote` equals local HEAD; pull back into the local clone, every push. Then `/gstack-peer-review` with the packet derived from the doc (criteria verbatim, constraints as exclusions, the actual test commands and results), fixes pushed and pulled back each round, exit only on `fixes_verified` or `no_blocking_findings`. Merge to main, mark the item done with the review ID, mirror, stop; the next item starts only when asked. The rule is also in team-shared memory (`feedback_all_coding_via_gstack_build.md`, indexed) so sessions that never invoke the skill still follow it.
- **0.11.0** — **Model floors.** Anything this plugin runs through Codex uses Astra (`gpt-6-astra`) or higher; anything through Claude Code uses Opus 5 (`claude-opus-5`) or higher (Fable qualifies). Set by Dorian 2026-09-11. `scripts/peer_review.py` passes the model explicitly (`-m` / `--model`), reads back the model each CLI reports it actually ran (Codex's `model:` header, Claude's `modelUsage`), and ends the round as `model_below_floor` on either side; `GSTACK_CODEX_MODEL` / `GSTACK_CLAUDE_MODEL` move the model, never the floor. Codex also runs with `model_reasoning_effort=high` (its default was `none`). The plan-review protocol's `codex exec` lines carry `-m gpt-6-astra`. Verified live on the Mac: Claude→Codex and Codex→Claude round 1 both `blocking_findings` with `model: gpt-6-astra` and `model: claude-opus-5` recorded; `GSTACK_CODEX_MODEL=gpt-5` and `GSTACK_CLAUDE_MODEL=claude-sonnet-5` both refused as `model_below_floor` before any call.
- **0.10.1** — Codex adapter verified against a live `codex` 0.154.0 (installed 2026-09-11). Three fixes from that run: `codex exec` blocks on "Reading additional input from stdin..." unless stdin is closed (now `DEVNULL`); OpenAI structured output rejects a schema without `additionalProperties: false` and a full `required` list on every object (a `strict()` transform now feeds both adapters one schema); `--head <repo>=<sha>` is resolved like the packet path so `/var/…` matches `/private/var/…` on macOS. Verified: Claude→Codex round 1 `blocking_findings` with file:line evidence (Codex executed the test read-only and reported the AssertionError), round 2 `fixes_verified`; Codex→Claude both rounds earlier the same day; selftest on 3.10 and 3.11; no stray snapshot worktrees. Still unverified: hook behavior inside reviewer sessions.
- **0.10.0** — `/gstack-peer-review`: a **bounded cross-tool review loop**, not another audit. At a completed implementation checkpoint the builder (named explicitly, `--builder claude|codex`, never inferred from git authorship) supplies a review packet — outcome and acceptance criteria, one exact base/head pair per repository, changed behavior and entry points, exclusions and settled decisions, tests run with results, prior findings — and the *other* tool reviews the pinned commits in a fresh read-only session against `references/peer-review-contract.md`. Scope is the direct-dependency boundary (callers, immediate helpers, the crossed API/DB boundary, the tests for it), not touched lines and not the directory; a finding blocks only when it demonstrably prevents an acceptance criterion or creates a concrete correctness, security, or data-loss risk, else it is `follow_up` or `separate`. One review plus two fix-verification rounds; stable finding IDs each ending `fixed | disproved | deferred | unresolved`; exhausting the limit yields `rounds_exhausted` with an escalation, never approval. `scripts/peer_review.py` (stdlib) enforces commit identity, snapshot isolation, output validation, round limits, and the recursion guard (`GSTACK_PEER_REVIEW_SESSION`), and names every non-pass as itself: `review_unavailable`, `missing_commits`, `timeout`, `malformed_output`. `/gstack-codex-review` becomes a compatibility alias (its "challenge the approach" moved to `/gstack-plan-review`; its Claude fallback is gone, since a same-tool pass is not independent review). `/gstack-ship` runs the loop at Step 4.5. Verified 2026-09-11: dispatcher selftest (all outcome paths, disposition gate, worktree teardown) and two live Claude-reviewer rounds on a seeded off-by-one (blocked with file:line evidence, then `fixes_verified`). Not verified at 0.10.0: the Codex adapter against a live binary (closed in 0.10.1) and hook behavior inside reviewer sessions.
- **0.9.0** — The checks now reach **cloud (Cowork) sessions**. Observed 2026-09-02 from the session's own debug log: the runtime fired SessionStart at +0.0s while the synced plugins' hooks were registered at +7.8s ("Registered 5 hooks from 46 plugins"), so the 0.8.0 hook could never run there — and project-init 0.27.0's liveness line correctly reported NOT LOADED on the very first test. The fix is a **UserPromptSubmit fallback**: the same script, `prompt` mode, delivers the block on the first user prompt of any session that did not receive it at start, and a marker file keyed on `session_id` (in `$CLAUDE_PLUGIN_DATA`, else a per-user temp dir, swept after a day) makes it once-per-session in both directions — a session that got it at SessionStart never gets it again, and the prompt path never repeats it per turn. Without a `session_id` the prompt path stays silent rather than risk repeating. Also removed the manifest `hooks` key that re-declared `hooks/hooks.json`: the loader auto-loads that file and logged the duplicate as a `hook-load-failed` error on every start (harmless to the hooks, which still registered, but it marked the plugin as errored). Verified by running the script with simulated payloads: start emits and marks; prompt-after-start is silent; prompt-without-start emits exactly once; no payload does not hang.
- **0.8.0** — The verification checks become a **SessionStart + SubagentStart hook**, not just skill text. A SKILL.md section only reaches Claude when that skill is invoked, and every mistake these checks describe was made without invoking gstack-execution; a hook fires regardless. Canonical text moved to `references/verification-checks.md` — one home, read by both the skill and the hook (check 5 applied to itself). Output contract matches ponytail's working reference: raw stdout on native SessionStart, `hookSpecificOutput` JSON on SubagentStart, `systemMessage` + `hookSpecificOutput` on Codex, `additionalContext` on Copilot. Every failure path (file missing, empty, unreadable) exits 0 silently, so a broken hook can never block a session.
- **0.7.0** — Verification discipline. Six checks the skill now applies before any claim that something works, each drawn from a real failure where the artifact was correct and the path the user takes was broken: verify through the user's path under the user's conditions (a DB function tested in the SQL editor runs as a different role than PostgREST, which enables `pg_safeupdate`); never say "press" without a URL and a confirmed-rendering control; read `${PIPESTATUS[0]}` rather than `$?` after a pipe, so a command redacted through `sed` cannot report a crash as success; count before characterizing data, especially when the characterization is the argument for overriding the user; grep for a rule's second home before changing it (`CREATE OR REPLACE FUNCTION` with a changed signature overloads rather than replaces); and state what was verified and what was not, as a format rather than an intention.
- **0.6.0** — Close the DR-004 gate pair. `/gstack-plan-review`: an iterative, bounded (default 5 rounds) adversarial review of an implementation plan before any code — same critic session/log across rounds, deadlock surfaced as a first-class outcome, PLAN-REVIEW-LOG.md as the argument transcript; hybrid engine (real Codex read-only, or a fresh-context Claude critic subagent in Cowork). Loop discipline concept-ported from chaseai-yt/grill-me-codex (MIT; lineage: Matt Pocock's grill-me, MIT) — no code copied. `/gstack-verify`: post-build verification of the implementation against its plan/spec — extracts every verifiable claim, tags each BUILT/DRIFTED/MISSING/EXTRA/UNVERIFIABLE, runs the spec's proof command; read-only, informs but never gates (per DR-004's posture).
- **0.5.0** — `/gstack-ship` hardening, concept-ported from no-mistakes (MIT, ideas only): Step 1.5 runs validation in a disposable git worktree (teardown always, in-place fallback escalates everything), and a Fix Contract classifies every Step 2–4 finding as safe-mechanical (auto-applied, logged) or judgment-call (stop and ask; validation/error-handling/security/accessibility always escalate). Ship Report now itemizes fixes.
- **0.4.x** — ecc merge (`/ecc-build-fix`, `/ecc-learn`, `/ecc-skill-create`) and ponytail restraint wiring (Step 3.5 in `/gstack-ship`, references in both reviews).
- **0.3.0** — Add `/gstack-codex-review`: an adversarial review of just-committed code (post-commit, pre-push). Hybrid engine — real Codex via `codex exec` when the CLI is present, Claude fallback against the shared `codex-review-methodology.md` (four lenses + defect floor) when it isn't. Adapts the adversarial framing from OpenAI's codex-plugin-cc.
- **0.2.0** — Replace remote-Playwright browser testing with Claude in Chrome. Real browser, real session, no remote sandbox dependency. See `MIGRATION-rube-deprecation.md` at the repo root for context.
- **0.1.0** — Initial release. 7 commands (review, investigate, cso, ship, design, qa, browse). Remote Playwright via Rube.

## Composio fallback

For apps with no native MCP connector, this plugin can reach them through Composio's Tool Router when the Composio connector is installed. See the `composio` plugin.

## Governance

This plugin conforms to the [MoxyWolf AI Governance Manifesto](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md). Every skill declares a risk tier, and high-stakes actions route through a named Release Owner who signs before anything irreversible ships. See [`GOVERNANCE.md`](GOVERNANCE.md) for the per-skill tier table.

Routine feature-branch commits and pushes are authorized. No auto-push to a protected branch or agent merge: a named human owns the merge. `peer_review.py release` prepares a revision-bound handoff and stops; `record-release` reads GitHub’s exact-head human merge record. See the [release contract](skills/gstack-execution/references/peer-review-contract.md#release-boundary).

## Merged from ecc

Three commands are merged from [ecc](https://github.com/affaan-m/ECC) (MIT, © Affaan Mustafa): `/ecc-build-fix` (incremental build/type-error fix loop), `/ecc-learn` (extract reusable patterns from a session into candidate skills), and `/ecc-skill-create` (generate SKILL.md from git history; ecc's instinct/continuous-learning coupling removed). ecc's 67 agents and 271 skills were not vendored — only these three genuinely-new, low-coupling commands. See `NOTICE`.

## Task graphs (0.17.0)

CSO and verify now execute static workflow declarations through `scripts/task_graph.py`. The runner schedules independent nodes with a concurrency cap, retains evidence and review IDs on resume, and converges through the other model before one report. Explicitly independent repository reviews can fan out; coupled work keeps integration review. See [task-graph contract](skills/gstack-execution/references/task-graph-contract.md). Data-use declarations gate dispatch and output destinations; human observations and machine outcomes remain separate. No graph handler merges or deploys.
