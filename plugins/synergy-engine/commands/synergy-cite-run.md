---
description: Citation center — send the "we cited you" outreach: email first (Mailtrap), then the LinkedIn connection note, human-gated, with the send discipline. Logs to the registry.
argument-hint: "[N people, default sized to the daily LinkedIn ceiling]"
allowed-tools: [Read, Write, Edit, Bash, AskUserQuestion, mcp__Mailtrap__send-email, mcp__Claude_in_Chrome__tabs_context_mcp, mcp__Claude_in_Chrome__navigate, mcp__Claude_in_Chrome__computer, mcp__Claude_in_Chrome__browser_batch, mcp__Claude_in_Chrome__read_page]
---

# /synergy-engine:synergy-cite-run — send the citation outreach

Send the drafted "we cited you" outreach to send-ready people in the citation registry. **The plugin never auto-sends** — email batches and every LinkedIn action are gated on an explicit OK. Read `references/outreach-channels.md` in full before the first send; the send discipline there is non-negotiable.

## STEP 1 — Load the registry + select

Read `synergy-engine-config.md` and the citation registry. Select the due people (see the due rule in `references/citation-registry-schema.md`). **Cap the batch to the daily LinkedIn ceiling** (~20-25 connects/day, ~100/week; subtract any connects already sent today). Email has no such cap but still gets one batch approval. Prefer load-bearing, then primary authors.

## STEP 2 — Email first (Mailtrap)

Show the drafted emails for the batch and get one approval (or per-person edits). Then send each via `mcp__Mailtrap__send-email` as **dorianc@moxywolf.com** (`from`/`to` as plain strings), **BCC dorianc@moxywolf.com**. Structure is their reference -> how used -> our paper once. Log `Email Sent + date` to the registry per person.

## STEP 3 — LinkedIn connect (Chrome), per person

For each person with a `verified` LinkedIn URL and no Connect Sent, in the user's logged-in LinkedIn:

1. **Navigate** to the profile; screenshot; confirm it's the right person and not already pending/connected.
2. **Open the connect dialog** by button geography: 2nd-degree = direct **Connect**; 3rd-degree = **Connect under More (...)**; high-follower = **Follow** is primary, Connect under More.
3. **Add the note** — click "Add a note", then **click the text field and type in SEPARATE calls** (batching races focus and drops the opening characters). The note is the hook-free draft, <=300 chars.
4. **Zoom-verify** the field: read the FIRST and LAST line. Only proceed if the note starts and ends correctly. (This is the truncation guard; a plain screenshot hides a clipped opening.)
5. **Email-gate:** if the profile asks for the member's email to verify, enter the **enriched work email we already hold** for them, then the note.
6. **Send** and confirm the button flips to **"Pending"** (or the "Invitation sent" toast).

Honor the two hard don'ts: never withdraw a bad invite to re-send (3-week lockout); non-connections can't be free-messaged (Message = paid InMail). Space the actions out.

## STEP 4 — Log every send

After each person, write to the registry: `Email Sent`, `Connect Sent`, `Status` (`Email sent` / `Connect pending`), `Next Action`, and the LinkedIn Conf -> `sent/confirmed`. Mirror the status onto the post-tracker queue row. The registry is the dedupe and the queue — keep it current.

## STEP 5 — Stage the accept-reply (for any hook-carrying notes only)

The hook-free notes owe nothing on accept. Only notes that historically carried the "I'll send the doc" hook need an accept-reply staged; for those, draft the correcting DM (DOI + where their work fits) so `/synergy-cite-accept-check` can fire it on accept.

## STEP 6 — Report

Summarize emails sent, connects pending, anyone email-gated and handled, anyone skipped (unverified / already pending), and how much daily headroom remains. Recommend running `/synergy-cite-accept-check` on a daily schedule.
