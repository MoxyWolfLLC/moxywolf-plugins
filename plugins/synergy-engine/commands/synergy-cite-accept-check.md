---
description: Citation center — daily check for accepted connection invites; surface them, fire any staged accept-reply, and advance the registry. Human-gated; never auto-sends.
argument-hint: ""
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, mcp__Claude_in_Chrome__tabs_context_mcp, mcp__Claude_in_Chrome__navigate, mcp__Claude_in_Chrome__computer, mcp__Claude_in_Chrome__read_page, mcp__scheduled-tasks__create_scheduled_task]
---

# /synergy-engine:synergy-cite-accept-check — follow through on accepts

Connection requests sit `Connect pending` until the person accepts; messaging only unlocks then. This command finds the new accepts, advances the registry, and (where one is staged) sends the accept-reply. Read `references/outreach-channels.md` first. **Never auto-sends** — every reply is gated.

## STEP 1 — Load the registry + the pending set

Read `synergy-engine-config.md` and the citation registry. Collect every row with `Status = Connect pending`.

## STEP 2 — Detect accepts

In the user's logged-in LinkedIn, check connection status for the pending set (their My Network / connections, or each profile — a 1st-degree badge means accepted). Mark newly accepted rows `Accepted` in the registry.

## STEP 3 — Fire staged accept-replies (gated)

For any newly accepted person who has a **staged accept-reply** (only the early hook-carrying notes do; hook-free notes owe nothing), show the drafted DM and get an OK. The reply corrects any clipped invite note and delivers what was promised (the DOI + where their work fits). Send it through the now-unlocked messaging, then mark `Replied`. Apply the same send care (focus the composer deliberately, verify the text before sending).

## STEP 4 — Surface the rest

List the people who accepted but have no staged reply (a thank-you is optional and the user can do it by hand), and anyone still pending past a long window (candidates to leave alone — do NOT withdraw; that triggers a ~3-week resend lockout).

## STEP 5 — Offer to schedule

If not already scheduled, offer to stand up a daily run via `mcp__scheduled-tasks__create_scheduled_task` (e.g. 9am PT) that runs this check and surfaces accepts for a human-gated reply — it never sends on its own.

## STEP 6 — Report

New accepts, replies sent, who's still pending, and the updated registry counts.
