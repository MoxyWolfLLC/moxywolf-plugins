---
description: Citation center — daily check for accepted connection invites; surface them, DM every new accept, and advance the registry. Human-gated; never auto-sends.
argument-hint: ""
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, mcp__Claude_in_Chrome__tabs_context_mcp, mcp__Claude_in_Chrome__navigate, mcp__Claude_in_Chrome__computer, mcp__Claude_in_Chrome__read_page, mcp__scheduled-tasks__create_scheduled_task]
---

# /synergy-engine:synergy-cite-accept-check — follow through on accepts

Connection requests sit `Connect pending` until the person accepts; messaging only unlocks then. This command finds the new accepts, advances the registry, and DMs each one. Read `references/outreach-channels.md` first. **Never auto-sends** — every reply is gated.

## STEP 1 — Load the registry + the pending set

Read `synergy-engine-config.md` and the citation registry. Collect every row with `Status = Connect pending`.

## STEP 2 — Detect accepts

In the user's logged-in LinkedIn, check connection status for the pending set (their My Network / connections, or each profile — a 1st-degree badge means accepted). Mark newly accepted rows `Accepted` in the registry.

## STEP 3 — DM every new accept (gated)

Every newly accepted connection gets a personal DM, not just the hook-carrying ones. Draft per person in the user's voice: reference their actual work and exactly where the anchor paper cites it (registry `Cited Works` / `Sections` / `How Used`), deliver the DOI where useful, no generic "glad to connect" filler. Other authors get the most care. Show every draft and get an explicit OK before each send — **never auto-sends**. Send through the now-unlocked messaging with the usual send care (click the field and type in separate calls, zoom-verify start and end before sending), then mark `Replied`. If the user already DMed them by hand, mark `Replied` and skip.

## STEP 4 — Surface the rest

List anyone still pending past a long window (candidates to leave alone — do NOT withdraw; that triggers a ~3-week resend lockout).

## STEP 5 — Offer to schedule

If not already scheduled, offer to stand up a daily run via `mcp__scheduled-tasks__create_scheduled_task` (e.g. 9am PT) that runs this check and surfaces accepts for a human-gated reply — it never sends on its own.

## STEP 6 — Report

New accepts, replies sent, who's still pending, and the updated registry counts.
