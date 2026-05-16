---
title: Rube deprecation — MoxyWolf plugins migration plan
date: 2026-05-16
author: Dorian (with Claude)
status: executed
type: migration-plan
executed_on: 2026-05-16
---

> **Status:** All 10 migrations executed on 2026-05-16. See bottom of file for actual-execution notes vs. the original plan. The body of this document is the plan as drafted; consult the version-history lines in each plugin's `README.md` for what actually shipped.



# Rube deprecation — migration plan

**Rube was discontinued on 2026-05-16** (the day the marketplace shipped, ha). Composio — the platform Rube was built on — is still alive, but Rube's single-endpoint gateway model is gone. This document inventories every Rube reference in the 15 MoxyWolf-authored plugins (+ the `moxywolf-skills` bundle) and prescribes a per-reference replacement. Source-of-truth scan was run against the canonical repo at `~/Documents/GitHub/moxywolf-plugins/` on 2026-05-16.

## TL;DR

8 plugins and the `moxywolf-skills` bundle reference Rube. 7 plugins are clean. The bulk of references fall into three buckets that have already-connected native replacements, so most of the work is search-and-replace plus a few patterns that need genuine rewrites. **Total estimated effort: 1.5 to 2 working days** if done sequentially; less in parallel.

The painful ones are (1) OpenRouter multi-model dispatch in Council/research-pipeline, (2) Google Drive Team Drive writes in obsidian-update/daily-ops (in the scheduled-task VM path specifically), and (3) Apple HealthKit data pulls in daily-ops fitness mode. Everything else is mostly mechanical.

## Reference inventory (canonical repo)

| Plugin | Files w/ refs | Lines | Burden |
|---|---:|---:|---|
| board-deck | 3 | 9 | low |
| council | 5 | 18 | **high** (core dispatch model) |
| daily-ops | 3 | 12 | medium |
| gstack-execution | 5 | 29 | **high** (Playwright host) |
| obsidian-update | 6 | 19 | **high** (Team Drive writes, scheduled-VM path) |
| product-orchestrator | 3 | 5 | low (delegates to Council) |
| research-pipeline | 5 | 22 | medium |
| saas-pricing-engine | 2 | 2 | trivial |
| **moxywolf-skills** bundle | 7 | 50 | medium (LinkedIn + market-awareness) |
| **Clean (no work)** | bibtex-builder, dev-infrastructure-skills, editorial-forge, project-init, saas-frontend-designer, team-kanban, vtt-to-text | — | — |

## Replacement matrix

Each Rube use case across all plugins maps to one of these replacements. Plugin-specific sections below reference these by ID.

| ID | Rube usage pattern | Replacement | Notes |
|---|---|---|---|
| **R1** | OpenRouter multi-model fan-out (`RUBE_MULTI_EXECUTE_TOOL` → `OPENROUTER_CREATE_CHAT_COMPLETION`) | Direct HTTPS to `https://openrouter.ai/api/v1/chat/completions` from workspace bash, using `OPENROUTER_API_KEY` env var. Parallelize with `xargs -P` or Python `asyncio`. | Removes Rube's 60-sec timeout — DeepSeek R1 becomes usable. Cleaner error handling. |
| **R2** | Google Drive Team Drive writes via `proxy_execute` (because Composio's standard GDrive doesn't pass `supportsAllDrives=true`) | **Interactive sessions:** write to mounted Vault filesystem (already documented as primary path). **Scheduled-task VMs:** direct Drive REST API via curl with stored service-account token, explicit `supportsAllDrives=true&supportsTeamDrives=true`. | Native GDrive MCP (`mcp__2c888036-*`) — needs Team Drive verification before relying on it. Default to direct REST. |
| **R3** | GitHub branch + per-branch commit listing (`GITHUB_LIST_BRANCHES`, `GITHUB_LIST_COMMITS`) | Native GitHub MCP `list_branches` + direct REST `GET /repos/{owner}/{repo}/commits?sha={branch}` via curl. | GitHub MCP doesn't expose `list_commits`; REST fills the gap. |
| **R4** | Gmail search/fetch (`GMAIL_FETCH_EMAILS`) | Native Gmail MCP (`mcp__50d37d97-*`) — `search_threads`, `get_thread`. | Drop-in replacement. |
| **R5** | LinkedIn page scraping (`COMPOSIO_SEARCH_FETCH_URL_CONTENT` via Rube → Browserless) | Claude in Chrome MCP (`mcp__Claude_in_Chrome__navigate` + `get_page_text` / `read_page`). | Better than Rube — runs in Dorian's logged-in browser, no auth gate. Already documented as fallback in linkedin-analytics. |
| **R6** | Web/Trends/News/Reddit search (`COMPOSIO_SEARCH_WEB`, `_TRENDS`, `_NEWS`, `REDDIT_SEARCH_ACROSS_SUBREDDITS`) | Built-in `WebSearch` for general web. Apify actors (`mcp__Apify__search-actors` → `call-actor`) for Google Trends, Reddit cross-subreddit, news scraping. | Apify already connected and independently maintained. |
| **R7** | Apple HealthKit pulls (Rube HealthKit toolkit) | **Primary:** Health Auto Export iOS app writes JSON to `Drive/Personal OS/health-export/`; read mounted file. **Fallback:** existing iMessage-prompt pattern (`send_imessage` to ask Dorian for manual numbers). | Composio HealthKit toolkit no longer reachable post-Rube. Health Auto Export is the durable path. |
| **R8** | Playwright remote sandbox (`RUBE_REMOTE_BASH_TOOL` + `RUBE_REMOTE_WORKBENCH` running Playwright) | **Verification + QA against live apps:** Claude in Chrome MCP — it IS a real browser, exactly what gstack `/qa` and `/browse` want. **Headless one-offs:** install Playwright in workspace bash sandbox (`npm i -g playwright && npx playwright install chromium`). | Claude in Chrome gives you real DOM, console, network — better fidelity than headless. |
| **R9** | Generic compute / hash / Python via `RUBE_REMOTE_WORKBENCH` | Workspace `mcp__workspace__bash` — runs Python, Node, curl, anything. | Trivial swap. |
| **R10** | Tool discovery / connection management (`RUBE_SEARCH_TOOLS`, `RUBE_MANAGE_CONNECTIONS`, `RUBE_GET_TOOL_SCHEMAS`) | Delete. Cowork's native connector model handles discovery; the user manages connections in the app. | These tools become dead weight. |

## Per-plugin migration

### 1. `council` v0.6.0 → 0.7.0 (HIGH effort, ~3 hours)

**Files to edit:**
- `commands/deliberate.md` — strip Rube tools from `allowed-tools`, rewrite Stage 1 dispatch
- `commands/council-optimize.md` — same allowed-tools cleanup
- `skills/deliberation-engine/SKILL.md` — full rewrite of the dispatch section (lines 15–25, 184–251, 407)
- `skills/pattern-memory/SKILL.md` line 82 — swap `RUBE_REMOTE_WORKBENCH` hash → Python in bash
- `README.md` lines 9, 14 — remove Rube prerequisites; document OpenRouter API key requirement

**The work:**
The deliberation engine is the most invasive change. The Stage 1 "fire 4 parallel models" pattern currently uses `RUBE_MULTI_EXECUTE_TOOL` with `sync_response_to_workbench`. Rewrite as a Python script invoked via `mcp__workspace__bash`:

```python
# Pseudocode for the dispatch script
import asyncio, httpx, os, json
async def call_model(model, messages):
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
            json={"model": model, "messages": messages})
        return model, r.json()
results = asyncio.run(asyncio.gather(*[call_model(m, msgs) for m in models]))
```

Persist results to `/sessions/.../mnt/outputs/council-{session_id}-round-{n}.json` and read back from the skill. Same pattern for Round 2 (peer review) and Stage 3 (synthesis). No more 60-sec timeout — DeepSeek R1 is usable; update `references/` to reflect.

**Verification:** Run a fresh `/deliberate` on a non-trivial question; confirm 4 models respond, peer-review round runs, synthesis lands.

**Version bump rationale:** Breaking change to the dispatch contract → minor bump.

### 2. `research-pipeline` v0.1.0 → 0.2.0 (MEDIUM effort, ~2 hours)

**Files to edit:**
- `README.md` line 59 — drop "Rube MCP" requirement; document OpenRouter API key
- `skills/citation-verifier/SKILL.md` lines 23–24 — swap Rube → direct CrossRef/DataCite/arXiv API via curl
- `skills/literature-discovery/SKILL.md` lines 67, 150–280 — rewrite OpenRouter swarm to use the same pattern as Council (R1); swap `COMPOSIO_SEARCH_WEB` → `WebSearch`
- `skills/literature-discovery/references/openrouter-swarm.md` — remove the "Rube 60-sec timeout" caveats throughout; re-enable DeepSeek R1
- `skills/import-bibtex/SKILL.md` lines 25–104 — swap OpenRouter calls to direct API

**The work:**
Citation verification is straightforward — CrossRef/DataCite/arXiv all have free public REST APIs. Replace each `RUBE_MULTI_EXECUTE_TOOL` block with a curl-or-Python equivalent in workspace bash. The literature-discovery web search becomes built-in `WebSearch`. The OpenRouter swarm dispatch uses the same async-Python pattern as Council (R1) — consider extracting to a shared helper script in `moxywolf-skills/_shared/openrouter_dispatch.py`.

### 3. `obsidian-update` v2.4.0 → 2.5.0 (HIGH effort, ~3 hours)

**Files to edit:**
- `commands/personal-os.md`, `memory-extract.md`, `obsidian-update.md` — strip Rube tools from `allowed-tools`
- `skills/personal-os/SKILL.md` — lines 18, 43, 50, 187, 209, 255, 304, 313, 493, 544, 801 — biggest rewrite
- `skills/memory-system/SKILL.md` line 45 — rewrite dual-access pattern
- `skills/obsidian-update/SKILL.md` line 20 — same

**The work:**
Two access paths must remain functional:

1. **Interactive Cowork sessions (vault is mounted):** Use standard `Read`/`Write`/`Edit` against the mounted filesystem. This already works and is the primary documented path. No code change — just remove the "Rube fallback" language and make the mounted-vault path the only path.

2. **Scheduled-task VMs (vault is NOT mounted):** This is the hard one. Three options:
   - **A. Native Google Drive MCP** — test whether `mcp__2c888036-*__create_file` accepts a Team Drive ID and `supportsAllDrives=true`. If it does, swap directly.
   - **B. Direct Drive REST API via bash** — `curl -X PATCH "https://www.googleapis.com/upload/drive/v3/files/{id}?uploadType=media&supportsAllDrives=true"` with a stored OAuth token. Most reliable, most plumbing.
   - **C. Reshape scheduled tasks to mount the vault** — if scheduled-task VMs can request a Drive mount the same way interactive sessions do, option A/B becomes unnecessary.

**Recommendation:** Test C first (1 day). If it works, the scheduled-task VM uses the same mounted-filesystem path as interactive. If not, fall back to B with a long-lived service account.

### 4. `daily-ops` v1.3.0 → 1.4.0 (MEDIUM effort, ~2 hours)

**Files to edit:**
- `README.md` lines 45, 52 — rewrite "Direct Google Drive Writes" paragraph (no more `proxy_execute`); update prereqs ("Rube/Composio connection" → "Health Auto Export + OpenRouter API key")
- `commands/daily-ops.md` line 3 — strip Rube tools from `allowed-tools`
- `skills/daily-ops/SKILL.md` lines 38–957 — multiple sites:
  - Team Drive writes (lines 38, 43, 73, 383, 540, 550) → R2 (use mounted vault for interactive; defer scheduled-VM concern to obsidian-update's resolution)
  - HealthKit pulls (lines 665, 697, 957) → R7

**The work:**
The Team Drive write story shares its fate with obsidian-update — do them together. HealthKit needs a real decision: if Health Auto Export is already exporting to Drive, point the skill at that file. If not, the fitness mode degrades to the existing iMessage-prompt pattern (already documented at line 957). Update the SKILL.md preamble to say "fitness mode requires Health Auto Export OR manual numbers via iMessage" instead of "requires Rube HealthKit."

### 5. `gstack-execution` v0.1.0 → 0.2.0 (HIGH effort, ~4 hours)

**Files to edit:**
- `.claude-plugin/plugin.json` line 4 — update description
- `README.md` — full rewrite of "Requires" + "Architecture" sections
- `commands/gstack-qa.md`, `commands/gstack-browse.md` — replace `RUBE_REMOTE_WORKBENCH` flow with Claude in Chrome flow
- `skills/gstack-execution/SKILL.md` lines 10, 33–34, 59, 65, 67, 71, 76–82 — full rewrite of "Browser Operations via Rube" section → "Browser Operations via Claude in Chrome"

**The work:**
This is the biggest conceptual change. The Rube remote-Playwright pattern was: "install playwright in a sandbox VM, launch a headless Chromium, run scripts." The Claude in Chrome pattern is: "navigate the user's real browser, read DOM/page text, run JS in-context." This is *better* for QA/dogfooding (real session, real cookies, real network) but means rewriting the example workflows.

For `/gstack-qa`:
- `RUBE_REMOTE_WORKBENCH: install playwright` → no-op (Claude in Chrome is always available)
- `RUBE_REMOTE_BASH_TOOL: launch playwright script for navigation` → `mcp__Claude_in_Chrome__navigate`
- `RUBE_REMOTE_BASH_TOOL: take screenshot` → `mcp__Claude_in_Chrome__get_page_text` or `read_page` (Chrome MCP doesn't have a screenshot primitive — use `gif_creator` if visual evidence is needed, or fall back to native computer-use `screenshot`)
- Assertions → `javascript_tool` to evaluate in-page JS

For `/gstack-browse`:
- Replace "URL → Rube Playwright" with "URL → `navigate` + `get_page_text`" — much simpler.

For headless-only use cases (scripted regression suites, CI), document a secondary path: install Playwright in workspace bash sandbox via `npm i -g playwright && npx playwright install chromium`. This works inside the Cowork sandbox.

### 6. `board-deck` v0.2.0 → 0.3.0 (LOW effort, ~1 hour)

**Files to edit:**
- `commands/board-deck.md` lines 20, 25, 30 — drop "via Rube"
- `skills/board-deck-builder/SKILL.md` lines 8, 46, 47 — same
- `skills/board-deck-builder/references/data-collection.md` lines 134, 198, 204 — swap tool names

**The work:**
- GitHub commit velocity → R3: use native `list_branches` MCP, then per-branch `GET /repos/{owner}/{repo}/commits?sha={branch}` via curl in workspace bash. Dedupe SHAs in Python.
- Gmail RegGenome search → R4: swap `GMAIL_FETCH_EMAILS` → `mcp__50d37d97-*__search_threads` + `get_thread`. Argument shapes differ; verify against the schema.

### 7. `product-orchestrator` v0.2.0 → 0.3.0 (LOW effort, ~30 min)

**Files to edit:**
- `README.md` lines 5, 47, 48 — drop Rube from requirements; reference OpenRouter API key instead
- `skills/product-orchestrator/SKILL.md` line 122 — already delegates to deliberation-engine; just remove the "Do NOT call RUBE_MULTI_EXECUTE_TOOL directly" caveat (it's now meaningless)
- `skills/product-orchestrator/references/sprint-protocol.md` line 196 — drop "via Rube Playwright" parenthetical (gstack-execution's fix handles the underlying)

**The work:** Cosmetic. This plugin delegates the actual model dispatch to Council, so once Council is migrated, this just needs documentation cleanup.

### 8. `saas-pricing-engine` v0.1.0 → 0.1.1 (TRIVIAL, ~5 min)

**Files to edit:**
- `commands/competitor-scan.md` line 12 — change "Use Rube/Apify tools if available" → "Use Apify or Claude in Chrome"
- `skills/pricing-research/SKILL.md` line 58 — same swap

**The work:** Two-line text edit. Patch-level bump.

### 9. `moxywolf-skills` bundle v1.0.0 → 1.1.0 (MEDIUM effort, ~3 hours)

**Files to edit:**
- `skills/linkedin-analytics/SKILL.md` — lines 22, 35–48, 77, 84, 227, 252 — full Rube → Claude in Chrome swap (R5). The "Claude in Chrome fallback" mentioned at line 252 becomes the primary path.
- `skills/linkedin-thought-leadership/SKILL.md` — lines 3, 8, 24–32, 163, 175 — same R5 swap. Update the skill description (the `description` field in frontmatter).
- `skills/market-awareness-analyzer/SKILL.md` lines 3, 64, 68–70 — R6 swaps. The 4 search modes (web/trends/news/reddit) each get a different replacement. Update the skill `description` frontmatter to drop the "Requires Rube MCP" sentence.
- `skills/market-awareness-analyzer/references/tool-execution.md` lines 6–60 — full rewrite of the tool-orchestration recipe. Replace the `RUBE_MULTI_EXECUTE_TOOL` batch patterns with: (a) `WebSearch` calls in parallel, (b) Apify `call-actor` for Trends and News, (c) Apify or direct Reddit API for subreddit search.
- `skills/market-awareness-analyzer/references/report-template.md` lines 282–285 — cosmetic: replace the "Tools used" footnote (`COMPOSIO_SEARCH_TRENDS via Rube MCP` etc.) with the new tool names so generated reports cite the right source.
- `skills/market-awareness-analyzer/references/sparktoro-integration.md` line 3 — one-line edit: SparkToro was already external; just drop the "not available through Rube MCP tools" framing.
- `skills/daily-ops/SKILL.md` — **duplicate of `plugins/daily-ops/skills/daily-ops/SKILL.md`** — see "duplication concern" below.

**Duplication concern:** `moxywolf-skills/skills/daily-ops/SKILL.md` is a copy of the plugin's daily-ops skill. Either (a) keep both in sync manually during this migration, (b) symlink one to the other, or (c) decide the bundle should not re-vendor skills that ship as their own plugin. **Recommendation (c)** — drop daily-ops from the bundle since `daily-ops` ships as its own plugin in the marketplace. Same review needed for any other bundle/plugin overlap.

### 10. Repo root `README.md` (TRIVIAL, ~2 min)

**Files to edit:**
- `README.md` line 166 — connector auth list mentions "Rube" alongside Slack/Gmail/etc. Drop Rube from the list. Optionally add "OpenRouter API key" and "Claude in Chrome extension" as new required configurations.

## Sequencing

Recommended order (each plugin can be a separate PR):

1. **Day 1 morning** — `saas-pricing-engine` (warm-up, 5 min) + repo root `README.md` (2 min) + `product-orchestrator` cosmetic (30 min) + `board-deck` (1 hr). Four PRs, all low-risk.
2. **Day 1 afternoon** — `council` rewrite (3 hr). This unblocks `product-orchestrator`'s real dispatch and `research-pipeline`'s swarm.
3. **Day 2 morning** — `research-pipeline` (2 hr) using Council's new dispatch helper. `moxywolf-skills` LinkedIn + market-awareness (2 hr).
4. **Day 2 afternoon** — `obsidian-update` Team Drive resolution (3 hr) — start by testing whether scheduled-task VMs can mount Drive (the cheapest fix). `daily-ops` HealthKit decision (1 hr).
5. **Day 3** — `gstack-execution` Playwright → Claude in Chrome rewrite (4 hr). This is the biggest conceptual change; do it last so it doesn't block other work.

After each plugin migrates: bump version in `plugin.json`, update `.claude-plugin/marketplace.json` at the repo root, commit individually for clean history.

## Verification checklist

For each migrated plugin, before merging:

- [ ] `grep -ri "rube\|RUBE_" plugins/{name}/` returns zero matches
- [ ] `grep -ri "composio" plugins/{name}/` returns only intentional references (e.g., explaining migration history)
- [ ] `plugin.json` version bumped
- [ ] `marketplace.json` version updated
- [ ] At least one happy-path invocation of the plugin's primary skill runs end-to-end without Rube
- [ ] README's "Requires" section reflects new dependencies (OpenRouter API key, Claude in Chrome extension, etc.)

After all 9 migrations land:

- [ ] `grep -ri "rube" .` at repo root returns zero matches outside this `MIGRATION-rube-deprecation.md` file
- [ ] README.md top-level marketplace docs no longer reference Rube as a prerequisite
- [ ] Smoke test: install the marketplace fresh on a clean Cowork session, verify each migrated plugin loads without errors

## Open questions for Dorian

1. **OpenRouter API key storage.** Where should plugins read it from? Options: `OPENROUTER_API_KEY` env var injected by Cowork, file in vault (`_Shared Knowledge/Agents and Plugins/openrouter.env`), 1Password CLI. **Recommendation:** env var, with a one-time setup note in each affected plugin's README.
2. **Scheduled-task VM vault access.** Is it possible to mount Drive in those VMs? This decision drives whether obsidian-update/daily-ops need the direct Drive REST path or can lean on the filesystem.
3. **Health Auto Export.** Is the iOS app already configured to export to a known Drive folder? If yes, point me at the path. If no, this needs a one-time setup.
4. **moxywolf-skills bundle overlap.** Should the bundle stop re-vendoring skills that ship as their own plugin (daily-ops at minimum)?

## Footnote: the seven clean plugins

These have zero Rube references and need no changes for this migration: `bibtex-builder`, `dev-infrastructure-skills`, `editorial-forge`, `project-init`, `saas-frontend-designer`, `team-kanban`, `vtt-to-text`.

---

## Execution log (2026-05-16)

All 10 migrations landed in one Cowork session. Final version table:

| Plugin | Before | After | Notes |
|---|---|---|---|
| board-deck | 0.2.0 | **0.3.0** | Native GitHub MCP + REST for commits; native Gmail MCP for RegGenome. |
| council | 0.6.0 | **0.7.0** | Direct OpenRouter via new `scripts/openrouter_dispatch.py`. Breaking — needs `OPENROUTER_API_KEY` env var. |
| daily-ops | 1.3.0 | **1.4.0** | Health Auto Export Drive folder for HealthKit; shared `drive_rest.py` for scheduled-VM writes. Breaking — Health Auto Export iOS app required. |
| gstack-execution | 0.1.0 | **0.2.0** | `/gstack-qa` and `/gstack-browse` use Claude in Chrome; workspace-bash Playwright as headless fallback. Breaking — Chrome extension required. |
| moxywolf-skills | 1.0.0 | **1.1.0** | LinkedIn skills → Claude in Chrome. market-awareness → WebSearch + Apify actors. Removed duplicate daily-ops skill (replaced with redirect stub — directory can be deleted in a follow-up). Breaking — Chrome extension required for LinkedIn skills. |
| obsidian-update | 2.4.0 | **2.5.0** | New `scripts/drive_rest.py` for Team Drive REST writes in scheduled-task VMs. Interactive sessions still use mounted vault. Breaking — service-account JSON required for scheduled-task VMs (see `personal-os/references/scheduled-task-vm-setup.md`). |
| product-orchestrator | 0.2.0 | **0.3.0** | Cosmetic — delegates to Council, just dropped Rube references from prereqs. |
| research-pipeline | 0.1.0 | **0.2.0** | Citation verifier uses direct CrossRef/DataCite/arXiv REST. Literature swarm reuses Council's dispatch helper. Web search → built-in `WebSearch`. Breaking — needs `OPENROUTER_API_KEY` and Council v0.7.0+. |
| saas-pricing-engine | 0.1.0 | **0.1.1** | Text-only edits. No behavior change. |
| repo root README | n/a | n/a | Dropped Rube from the connector list; added OpenRouter env-var setup and Claude in Chrome extension as new requirements. |

### Two new helper scripts shipped

- `plugins/council/scripts/openrouter_dispatch.py` — pure-stdlib parallel OpenRouter dispatcher. POSTs to `https://openrouter.ai/api/v1/chat/completions` with `OPENROUTER_API_KEY`. Used by Council (all three deliberation stages), research-pipeline (literature swarm, abstract enrichment).
- `plugins/obsidian-update/scripts/drive_rest.py` — Drive v3 REST helper, service-account auth, `supportsAllDrives=true` always. Subcommands: `download`, `upload`, `search`, `ls`. Used by obsidian-update and daily-ops in scheduled-task VMs.

### One-time setup per Mac (post-merge)

1. **`OPENROUTER_API_KEY`** in `~/.zshrc`:
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   ```
   Source it and restart Cowork.

2. **Claude in Chrome extension** — Chrome Web Store, sign in. Needed by gstack-execution browser commands, moxywolf-skills LinkedIn skills, and saas-pricing-engine's competitor scan.

3. **Drive service account** — only needed if you run obsidian-update or daily-ops on a scheduled-task VM. See `plugins/obsidian-update/skills/personal-os/references/scheduled-task-vm-setup.md`.

4. **Health Auto Export iOS app** — only needed for daily-ops fitness mode. App Store, configure JSON export to `MoxyWolf Vault/../Personal OS/health-export/` on a daily schedule.

### Verification

- `grep -ri "RUBE_\|rube\.sh\|rube\.app\|proxy_execute\|run_composio_tool" .` → zero hits in code paths
- Remaining "Rube" mentions in the repo are: this migration doc, gstack-execution's v0.1.0 version-history line, daily-ops README v1.4.0 What's New (since lightly reworded). All intentional historical/contextual references.
- Both helper scripts pass `python3 -m py_compile`.
- Marketplace manifest reflects all version bumps.
