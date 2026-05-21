---
title: Composio integration — moxywolf-plugins plan
date: 2026-05-21
status: proposed
type: migration-plan
author: Dorian (with Claude)
---

# Composio integration — plan

Rube is dead (`MIGRATION-rube-deprecation.md`). Composio — the platform underneath Rube — is alive and has a current MCP model: session-based, each session exposing a remote MCP endpoint. This plan brings Composio back into the MoxyWolf plugin ecosystem deliberately, as a capability, without re-coupling the plugins to a gateway.

**Status: proposed — awaiting sign-off before any plugin files change.**

## Decision recap

On 2026-05-21 the call was made to (a) retire the idle Rube connector, (b) add Composio as a current-model connector, and (c) bring the capability into `moxywolf-plugins` as both a new standalone plugin AND wiring into the eight plugins that previously used Rube. This plan honors all three — with one engineering caveat called out in Part 2.

Companion artifacts already produced: the Cowork connector setup doc (`MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/composio-connector-setup.md`) and a standalone agent project (`GitHub/composio-agent/` — a runnable program, deliberately not a plugin).

## Part 1 — New `composio` plugin

A standalone plugin at `plugins/composio/`:

- `.claude-plugin/plugin.json` — name `composio`, version `0.1.0`.
- `skills/composio-tools/SKILL.md` — teaches Claude how to use Composio when the Composio MCP connector is present: the meta-tool model (`COMPOSIO_SEARCH_TOOLS` to discover, `COMPOSIO_MANAGE_CONNECTIONS` to authenticate, then execute), the session model, the 1000+ toolkits, and the workbench for bulk operations. Critically, it encodes *when to reach for Composio vs. a native MCP* — native MCP first, Composio for apps with no native connector.
- `commands/composio-setup.md` — `/composio-setup`, an operational walkthrough: retire the Rube connector, create a Composio MCP server URL, add it as a Cowork custom connector org-wide. Mirrors the vault connector-setup doc.
- `README.md`.
- Registered in `.claude-plugin/marketplace.json`, category `integration`.

Design note: the plugin does **not** bundle an MCP server in `plugin.json`. Composio's MCP endpoint is org-specific (URL + API key) and cannot be hardcoded in a marketplace plugin. The connector is added once at the Cowork level; the plugin teaches and operationalizes that.

This part is low-risk, self-contained, and is the real "Composio is a first-class part of the ecosystem" deliverable.

## Part 2 — Wiring into the eight Rube-era plugins

**Engineering caveat, stated plainly.** The Rube migration didn't just remove Rube — it replaced each use with a *specific* native path (R1–R10 in `MIGRATION-rube-deprecation.md`): direct OpenRouter, native Gmail MCP, native GitHub MCP, Claude in Chrome, Apify, built-in WebSearch. For every one of those specific use cases the native path is equal to or better than routing back through Composio. Re-wiring the eight plugins to *call Composio instead of* their natives would discard working, faster integrations and re-introduce the exact gateway coupling the migration removed. **That is not recommended.**

What Composio genuinely adds is **reach** — 1000+ apps the team has no native MCP for (Notion, Linear, Jira, HubSpot, Stripe, Airtable, Calendly, and so on). So the wiring is *additive*, not *replacing*.

Each of the eight plugins gets a short, uniform **"Composio fallback"** block in its primary `SKILL.md`, plus a one-line `README.md` note: *if a task needs an app with no native MCP and the Composio connector is installed, discover and execute it through Composio's meta-tools — see the `composio` plugin.* No native path is removed. No skill logic is rewritten. Patch-level version bump each.

| Plugin | Current | After | Change |
|---|---|---|---|
| board-deck | 0.3.0 | 0.3.1 | + Composio fallback block |
| council | 0.7.1 | 0.7.2 | + Composio fallback block |
| daily-ops | 1.4.0 | 1.4.1 | + Composio fallback block |
| gstack-execution | 0.2.0 | 0.2.1 | + Composio fallback block |
| obsidian-update | 2.5.0 | 2.5.1 | + Composio fallback block |
| product-orchestrator | 0.3.0 | 0.3.1 | + Composio fallback block |
| research-pipeline | 0.2.0 | 0.2.1 | + Composio fallback block |
| saas-pricing-engine | 0.1.1 | 0.1.2 | + Composio fallback block |

The `moxywolf-skills` bundle was also Rube-era; it can take the same note (1.1.0 → 1.1.1). Optional — flag if you want it in scope.

If you want the heavy version anywhere — Composio actually *replacing* a native path in a specific plugin — name the plugin and the use case and I'll scope that as a separate, deliberate change. By default this plan does the additive version only.

## marketplace.json

- Add the `composio` plugin entry.
- Bump the eight (or nine) plugin versions to match.
- Bump the marketplace `version` 1.0.0 → 1.1.0 (new plugin added).

## Sequencing

1. Build the `composio` plugin (Part 1) — self-contained, no dependencies on the rest.
2. Add the fallback block to the eight plugins (Part 2) — mechanical, one uniform block.
3. Update `marketplace.json` — new entry plus version bumps.
4. Verify — the new plugin loads; every touched `plugin.json` version matches `marketplace.json`.
5. Commit via GitHub Desktop — one aggregated commit, plain-text message. Quit GitHub Desktop first (bulk write across many files).

## Side note — unrelated drift to reconcile

`project-init`'s `plugin.json` is at `0.12.0` but `marketplace.json` lists `0.11.0`, and the `/session-start` project-picker change made earlier on 2026-05-21 is itself unversioned. Reconcile that drift separately — it is not part of this Composio work, but it should not be lost.
