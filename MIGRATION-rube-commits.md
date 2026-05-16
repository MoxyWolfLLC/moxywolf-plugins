# Rube migration — commit-message bundle

Paste each block as a single GitHub Desktop commit. Stage the listed files for that commit, paste subject + body, commit, move to the next.

The `.claude-plugin/marketplace.json` bumps for each plugin are one-line-per-commit edits — GitHub Desktop's per-file staging handles this cleanly.

---

## Commit 1 — saas-pricing-engine

**Staged:**
- `plugins/saas-pricing-engine/.claude-plugin/plugin.json`
- `plugins/saas-pricing-engine/commands/competitor-scan.md`
- `plugins/saas-pricing-engine/skills/pricing-research/SKILL.md`
- `.claude-plugin/marketplace.json` (just the saas-pricing-engine version line)

```
chore(saas-pricing-engine): drop Rube; use Apify or Claude in Chrome

Two text edits — competitor-scan and pricing-research SKILL no longer
mention Rube. Apify actors and Claude in Chrome handle JS-rendered
pricing pages; WebFetch is the static fallback.

Version: 0.1.0 → 0.1.1
```

---

## Commit 2 — repo root README

**Staged:**
- `README.md`

```
docs(readme): drop Rube; require OpenRouter env + Chrome extension

Connector auth list no longer mentions Rube. New per-Mac setup items:
- OPENROUTER_API_KEY env var in ~/.zshrc (Council, research-pipeline,
  product-orchestrator)
- Claude in Chrome extension (gstack-execution, LinkedIn skills,
  saas-pricing-engine competitor scans)
```

---

## Commit 3 — product-orchestrator

**Staged:**
- `plugins/product-orchestrator/.claude-plugin/plugin.json`
- `plugins/product-orchestrator/README.md`
- `plugins/product-orchestrator/skills/product-orchestrator/SKILL.md`
- `plugins/product-orchestrator/skills/product-orchestrator/references/sprint-protocol.md`
- `.claude-plugin/marketplace.json` (product-orchestrator version line)

```
chore(product-orchestrator): drop Rube prereqs; require Council 0.7.0+

Cosmetic — this plugin delegates all model dispatch to Council, so once
Council migrates to direct OpenRouter (v0.7.0), product-orchestrator
inherits it for free. Just updates the "Requires" docs and removes a
caveat referencing RUBE_MULTI_EXECUTE_TOOL.

Version: 0.2.0 → 0.3.0
```

---

## Commit 4 — board-deck

**Staged:**
- `plugins/board-deck/.claude-plugin/plugin.json`
- `plugins/board-deck/commands/board-deck.md`
- `plugins/board-deck/skills/board-deck-builder/SKILL.md`
- `plugins/board-deck/skills/board-deck-builder/references/data-collection.md`
- `.claude-plugin/marketplace.json` (board-deck version line)

```
feat(board-deck): migrate to native GitHub + Gmail MCPs

GitHub commit velocity: native GitHub MCP for list_branches, then
direct REST (gh or curl) for per-branch commits since the MCP doesn't
expose list_commits. SHA-dedupe in Python as before.

RegGenome activity intel: native Gmail MCP (search_threads + get_thread).
Drop-in replacement for GMAIL_FETCH_EMAILS.

Version: 0.2.0 → 0.3.0
```

---

## Commit 5 — council (BREAKING)

**Staged:**
- `plugins/council/.claude-plugin/plugin.json`
- `plugins/council/README.md`
- `plugins/council/commands/deliberate.md`
- `plugins/council/commands/council-optimize.md`
- `plugins/council/scripts/openrouter_dispatch.py` (NEW)
- `plugins/council/skills/deliberation-engine/SKILL.md`
- `plugins/council/skills/pattern-memory/SKILL.md`
- `.claude-plugin/marketplace.json` (council version line)

```
feat(council)!: dispatch via direct OpenRouter API; drop Rube

BREAKING: requires OPENROUTER_API_KEY env var in the Cowork bash
sandbox. Add `export OPENROUTER_API_KEY="sk-or-v1-..."` to ~/.zshrc,
source it, and restart Cowork.

What's in:
- New scripts/openrouter_dispatch.py: parallel HTTPS to
  https://openrouter.ai/api/v1/chat/completions. Pure stdlib (urllib +
  concurrent.futures). Writes one JSON per job to an output dir so the
  skill can read them back.
- deliberation-engine SKILL: Stages 1-3 rewritten to build jobs.json,
  invoke the helper via mcp__workspace__bash, read results.
- pattern-memory hash: bash one-liner via shasum/python instead of a
  remote workbench call.
- Default timeout bumped from 60s (Rube ceiling) to 180s — DeepSeek R1
  is usable again.

Version: 0.6.0 → 0.7.0
```

---

## Commit 6 — research-pipeline (BREAKING)

**Staged:**
- `plugins/research-pipeline/.claude-plugin/plugin.json`
- `plugins/research-pipeline/README.md`
- `plugins/research-pipeline/skills/citation-verifier/SKILL.md`
- `plugins/research-pipeline/skills/literature-discovery/SKILL.md`
- `plugins/research-pipeline/skills/literature-discovery/references/openrouter-swarm.md`
- `plugins/research-pipeline/skills/import-bibtex/SKILL.md`
- `.claude-plugin/marketplace.json` (research-pipeline version line)

```
feat(research-pipeline)!: drop Rube; use direct APIs + Council helper

BREAKING: requires OPENROUTER_API_KEY env var (same as Council) and
Council v0.7.0+ for the dispatch helper (referenced via
${COUNCIL_PLUGIN}/scripts/openrouter_dispatch.py).

What changed per skill:
- citation-verifier: direct CrossRef / DataCite / arXiv / S2 REST calls
  via WebFetch or curl. All four APIs are public, no auth.
- literature-discovery: built-in WebSearch for general web; OpenRouter
  swarm dispatched via Council's helper with a swarm-jobs.json file.
  DeepSeek R1 timeout caveats removed (180s timeout absorbs it).
- import-bibtex: abstract enrichment dispatched the same way, one job
  per batch.

Version: 0.1.0 → 0.2.0
```

---

## Commit 7 — moxywolf-skills bundle (BREAKING)

**Staged:**
- `skill-bundles/moxywolf-skills/.claude-plugin/plugin.json`
- `skill-bundles/moxywolf-skills/skills/linkedin-analytics/SKILL.md`
- `skill-bundles/moxywolf-skills/skills/linkedin-thought-leadership/SKILL.md`
- `skill-bundles/moxywolf-skills/skills/market-awareness-analyzer/SKILL.md`
- `skill-bundles/moxywolf-skills/skills/market-awareness-analyzer/references/tool-execution.md`
- `skill-bundles/moxywolf-skills/skills/market-awareness-analyzer/references/report-template.md`
- `skill-bundles/moxywolf-skills/skills/market-awareness-analyzer/references/sparktoro-integration.md`
- `skill-bundles/moxywolf-skills/skills/daily-ops/SKILL.md` (now a redirect stub)
- `.claude-plugin/marketplace.json` (moxywolf-skills entry)

```
feat(moxywolf-skills)!: drop Rube; Chrome + Apify + remove daily-ops dup

BREAKING:
- LinkedIn skills now require the Claude in Chrome extension. The
  Chrome MCP runs in Dorian's already-logged-in browser, so LinkedIn's
  anti-bot gates don't trigger.
- daily-ops skill removed from the bundle. It ships as its own plugin
  in this same marketplace; install that instead. The bundle's
  daily-ops directory currently contains a redirect stub — safe to
  delete the whole `skills/daily-ops/` directory in a follow-up commit.

What changed per skill:
- linkedin-analytics: navigate + get_page_text + javascript_tool
  instead of COMPOSIO_SEARCH_FETCH_URL_CONTENT.
- linkedin-thought-leadership: same swap. Updated skill description
  to reflect Chrome-MCP as the scraping path.
- market-awareness-analyzer:
  * Web/News → built-in WebSearch
  * Trends → Apify google-trends-scraper actor
  * Reddit → Apify reddit-scraper actor
  * YouTube → Apify youtube-scraper actor
  * Updated report-template's "Tools Used" footer accordingly.

Version: 1.0.0 → 1.1.0
```

---

## Commit 8 — obsidian-update (BREAKING)

**Staged:**
- `plugins/obsidian-update/.claude-plugin/plugin.json`
- `plugins/obsidian-update/commands/personal-os.md`
- `plugins/obsidian-update/commands/memory-extract.md`
- `plugins/obsidian-update/commands/obsidian-update.md`
- `plugins/obsidian-update/scripts/drive_rest.py` (NEW)
- `plugins/obsidian-update/skills/personal-os/SKILL.md`
- `plugins/obsidian-update/skills/personal-os/references/scheduled-task-vm-setup.md` (NEW)
- `plugins/obsidian-update/skills/memory-system/SKILL.md`
- `plugins/obsidian-update/skills/obsidian-update/SKILL.md`
- `.claude-plugin/marketplace.json` (obsidian-update version line)

```
feat(obsidian-update)!: drop Rube; direct Drive REST for Team Drive writes

BREAKING (scheduled-task VMs only):
- Interactive Cowork sessions still use the mounted MoxyWolf Vault
  filesystem — no setup change for daily use.
- Scheduled-task VMs need a one-time Google service account at
  ~/.config/moxywolf/drive-service-account.json. Setup walkthrough in
  plugins/obsidian-update/skills/personal-os/references/
  scheduled-task-vm-setup.md.

What's in:
- New scripts/drive_rest.py: Drive v3 REST helper, pure stdlib + PyJWT.
  Subcommands: download / upload / search / ls. Always passes
  supportsAllDrives=true so Team Drive 404s don't happen.
- All references to RUBE_REMOTE_WORKBENCH, proxy_execute,
  run_composio_tool, and Composio Google Drive tools replaced with
  either the mounted-filesystem path (interactive) or the new helper
  (scheduled VM).
- allowed-tools lists in all three command frontmatters trimmed —
  Rube tool IDs removed.

Version: 2.4.0 → 2.5.0
```

---

## Commit 9 — daily-ops (BREAKING)

**Staged:**
- `plugins/daily-ops/.claude-plugin/plugin.json`
- `plugins/daily-ops/README.md`
- `plugins/daily-ops/commands/daily-ops.md`
- `plugins/daily-ops/skills/daily-ops/SKILL.md`
- `.claude-plugin/marketplace.json` (daily-ops version line)

```
feat(daily-ops)!: drop Rube; Health Auto Export + shared Drive REST

BREAKING:
- HealthKit data is now read from the Health Auto Export iOS app's
  nightly JSON drop in Drive (Personal OS/health-export/). Install
  the app from the App Store (developer: Lybrook Solutions) and set
  up the daily Drive export — see the in-skill setup iMessage for
  details. No more live HealthKit MCP.
- Team Drive writes share obsidian-update v2.5.0's drive_rest.py
  helper (so service-account setup is shared too, for scheduled VMs).
  Interactive sessions write to the mounted vault directly.

What changed:
- All proxy_execute / RUBE_REMOTE_WORKBENCH code blocks in
  skills/daily-ops/SKILL.md replaced with mount-or-helper patterns.
- Fitness coach reads from health-export JSON; iMessage fallback
  updated to point at Health Auto Export setup instead of Claude iOS
  Health permissions.
- allowed-tools in commands/daily-ops.md trimmed — Rube tool IDs
  removed; native Gmail/GCal/Drive MCPs not pre-declared (Cowork
  picks them up by default).

Version: 1.3.0 → 1.4.0
```

---

## Commit 10 — gstack-execution (BREAKING)

**Staged:**
- `plugins/gstack-execution/.claude-plugin/plugin.json`
- `plugins/gstack-execution/README.md`
- `plugins/gstack-execution/commands/gstack-qa.md`
- `plugins/gstack-execution/commands/gstack-browse.md`
- `plugins/gstack-execution/skills/gstack-execution/SKILL.md`
- `.claude-plugin/marketplace.json` (gstack-execution version line)

```
feat(gstack-execution)!: Claude in Chrome for /qa and /browse

BREAKING: /gstack-qa and /gstack-browse require the Claude in Chrome
extension. Chrome MCP runs in the user's real signed-in browser, so
authenticated sessions, cookies, and extensions are present —
strictly better fidelity than the previous remote-Playwright setup.

What changed:
- /gstack-browse: navigate + get_page_text + javascript_tool +
  read_console_messages + read_network_requests. Responsive checks
  via resize_window.
- /gstack-qa: same primitives plus form_input, gif_creator for
  interaction captures, shortcuts_execute for keyboard shortcuts.
- SKILL.md "Browser Operations" section rewritten end-to-end.
- Headless Playwright in workspace bash documented as the alternate
  path for unattended regression suites (no real browser needed).

Version: 0.1.0 → 0.2.0
```

---

## Commit 11 (optional) — migration docs

If you want the migration plan + this commit bundle in their own
commit (rather than folded into commit 1):

**Staged:**
- `MIGRATION-rube-deprecation.md`
- `MIGRATION-rube-commits.md`

```
docs(migration): plan, execution log, and commit bundle for Rube → native

Records every Rube reference in the 15 MoxyWolf plugins, the
replacement strategy per use case, per-plugin migration steps, the
actual-execution log with final versions, and the paste-ready commit
messages used to land the migration.
```

---

## Post-merge cleanup (one follow-up commit, easy)

The bundle's `skill-bundles/moxywolf-skills/skills/daily-ops/`
directory currently contains a redirect stub. After confirming
nothing references it, you can delete the whole directory:

```bash
rm -rf skill-bundles/moxywolf-skills/skills/daily-ops/
```

Then commit:

```
chore(moxywolf-skills): remove daily-ops redirect stub

The redirect from v1.1.0 has served its purpose. The skill ships as
the standalone daily-ops plugin in the same marketplace.
```
