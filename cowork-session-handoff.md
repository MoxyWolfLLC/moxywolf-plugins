---
title: "Session Handoff — moxywolf-plugins"
date: 2026-05-21
session_ended: 2026-05-21T09:05:50-07:00
project: moxywolf-plugins
type: session-handoff
status: active
author: dorian
---

# Session Handoff — moxywolf-plugins

**Session ended:** 2026-05-21 09:05 PT
**Author:** Dorian — solo session, no baton-pass

## What landed this session

Composio came back into the MoxyWolf stack, deliberately. The session opened by changing the `/session-start` skill so it never shows a project picker — it auto-resolves the project (explicit argument, then launch directory, then the most recently active project) and only asks what to focus on. Then the main work: Rube is being retired, and Composio re-enters as an additive reach layer. A new `composio` plugin was built — a `composio-tools` skill, a `/composio-setup` command, and a README — and registered in the marketplace. A uniform "Composio fallback" block was wired into the eight Rube-era plugins' primary skills plus the moxywolf-skills bundle README, with native MCPs still first and Composio only for apps with no native connector. `marketplace.json` was updated (composio added, nine plugin versions bumped, marketplace to 1.1.0), the root `README.md` refreshed (count 17 to 18, composio added, the drift-prone per-plugin version column dropped), and `project-init`'s version drift reconciled to 0.13.0. Separately, a standalone `composio-agent` TypeScript project was scaffolded at `GitHub/composio-agent/` (Claude Agent SDK plus Composio Tool Router, typecheck passing), and a short outreach email to bern@anthropic.com was drafted in Dorian's memo voice. Nothing is committed — the whole moxywolf-plugins working tree is uncommitted as of session end.

## Open work, in priority order

### 1. Commit and push the moxywolf-plugins changes

The entire session's plugin work sits uncommitted in `~/Documents/GitHub/moxywolf-plugins/`. Roughly 36 files: the new `plugins/composio/` (4 files), the Composio fallback block plus version bumps across 9 plugins, `marketplace.json`, the root `README.md`, `project-init`'s `plugin.json`, `MIGRATION-composio-integration.md`, and this handoff. Commit it as one aggregated commit through GitHub Desktop. Commit text is in the Commit & push state section below. Quit GitHub Desktop before any further bulk writes, and confirm no `.git/index.lock` is stranded.

### 2. Disconnect Rube, add the Composio connector

Two manual Cowork-settings actions Claude can't perform. First, Cowork → Settings → Connectors, remove the Rube server (`b51b4119…`). Second, add the Composio connector — run `/composio-setup` for the guided walkthrough, or follow `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/composio-connector-setup.md`. On a Team or Enterprise plan an Owner adds it org-wide so the whole team gets it, then each teammate connects their own app accounts.

### 3. Finish the standalone composio-agent and rotate the key

`GitHub/composio-agent/` is scaffolded and typechecks but isn't a git repo yet. To run it: `npm install`, then add a real `ANTHROPIC_API_KEY` to `.env` (the Claude Agent SDK needs it to call Claude). Then `git init` and add it to GitHub Desktop. Also rotate the Composio API key `ak_b1gi2U9tb4P6rNBbGflF` — it was pasted in plaintext during setup. Generate a fresh one in the Composio dashboard and update the project `.env` and the connector config.

### 4. Decide on the Bern email

A short outreach email to bern@anthropic.com is drafted (in the session chat, Dorian memo voice, soft ask, written to spark interest in the plugin work). Send it, or have it dropped into Gmail drafts.

## Commit & push state

**moxywolf-plugins** — working tree is fully uncommitted as of session end. Claude supplied commit text for GitHub Desktop rather than committing directly, consistent with this session's flow and the project's commit convention. One aggregated commit:

Summary:

```
Add composio plugin; wire Composio fallback into 9 plugins
```

Description:

```
New composio plugin (v0.1.0) — composio-tools skill, /composio-setup command, README. Teaches Claude to use Composio's Tool Router for apps with no native MCP connector. Does not bundle an MCP server; the connector is added at the Cowork level.

Composio fallback wiring — added a uniform Composio fallback block to the primary skill of the 8 Rube-era plugins (board-deck, council, daily-ops, gstack-execution, obsidian-update, product-orchestrator, research-pipeline, saas-pricing-engine) and a short note to each README plus the moxywolf-skills bundle README. Native MCP paths unchanged — Composio is an additive reach layer, not a replacement.

Version bumps — board-deck 0.3.1, council 0.7.2, daily-ops 1.4.1, gstack-execution 0.2.1, obsidian-update 2.5.1, product-orchestrator 0.3.1, research-pipeline 0.2.1, saas-pricing-engine 0.1.2, moxywolf-skills 1.1.1. marketplace.json updated with the composio entry and bumped to 1.1.0.

Repo root README refreshed — plugin count 17 to 18, composio added to the file tree and CLI install loop. Dropped the per-plugin version column from the README tree; marketplace.json is now the single source of truth for versions.

project-init reconciliation — bumped project-init to 0.13.0 in plugin.json and marketplace.json (the two had drifted to 0.12.0 / 0.11.0), versioning the earlier /session-start picker change, and unified the drifted descriptions.

Plan recorded in MIGRATION-composio-integration.md.
```

Paste Summary and Description as the two GitHub Desktop fields — plain text, no markdown.

## Procedural reminders for next-Claude

- **The installed project-init plugin is stale.** The `/session-start` picker change and the rest of project-init's edits live in the source repo (`GitHub/moxywolf-plugins/plugins/project-init/`). The copy running in this Cowork is the older cached build. The changes go live only after the plugin is reinstalled or updated from the marketplace.
- **moxywolf-plugins is a git repo — quit GitHub Desktop before bulk writes.** Its file-watcher races multi-file writes and can strand a `.git/index.lock`.
- **The composio plugin does not bundle an MCP server.** Composio's MCP endpoint is org-specific (URL plus API key); the connector is added at the Cowork level via `/composio-setup`, not shipped in the plugin.
- **Google Drive mounts — use the Read tool, not bash.** bash `sed` / `cat` on vault files (Google Drive) hit "Resource deadlock avoided" this session. The Read tool works fine. bash is fine on the local `GitHub/` repos.
- **Composio API key was pasted in plaintext** (`ak_b1gi2U9tb4P6rNBbGflF`) — rotate it. See Open work #3.

## Suggested opening line

> *"Picking up the moxywolf-plugins Composio work. Everything's written but uncommitted — first move is the one aggregated GitHub Desktop commit (text is in the handoff), then the two manual connector steps: disconnect Rube, add Composio via /composio-setup. The full handoff is at `GitHub/moxywolf-plugins/cowork-session-handoff.md`."*
