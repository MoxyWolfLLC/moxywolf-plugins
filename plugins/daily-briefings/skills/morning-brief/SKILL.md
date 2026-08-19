---
name: morning-brief
risk_tier: generate
description: >
  Render today's briefing as one self-contained HTML page — the day's calendar, what arrived overnight in email and chat that needs an answer, the deadlines close enough to matter, and the flags on today specifically. Use when the user asks for their morning brief, their day, what is on today, what came in overnight, what needs answering, or invokes /morning-brief. Also the skill a scheduled weekday-morning run invokes. Sibling of commitment-calendar: same sources, same honesty rules, same visual family, one day instead of a window.
---

# Morning brief

The commitment calendar answers *what is coming*. This one answers *what is today, and what landed while I was asleep*.

Same sources, same rules, same look. Read these first and follow them rather than the summaries here:

- `${CLAUDE_PLUGIN_ROOT}/references/briefing-config.md` — every person-specific value
- `${CLAUDE_PLUGIN_ROOT}/references/source-discipline.md` — the three source states, and the bar for asserting anything
- `${CLAUDE_PLUGIN_ROOT}/references/flag-detection.md` — the flag rules, applied here to today only
- `${CLAUDE_PLUGIN_ROOT}/references/briefing-design.md` — the shared visual language

## Unattended by default

Scheduled weekday runs mean nobody is watching. **Do not ask clarifying questions and do not offer connector suggestions.** Resolve from the config, make the honest call where it is silent, and put what is unresolved in the footer.

---

## Step 1 — Anchor the date

Run `date` in bash. Today is today's real date, not an inferred one.

Load the config. Everything below reads from it.

## Step 2 — Today's calendar

`mcp__Google_Calendar__list_calendars`, then `mcp__Google_Calendar__list_events` across the same calendar set the commitment calendar uses, bounded to today in `owner.timezone`, `orderBy: startTime`.

Pull **tomorrow** as well. A brief that ends at midnight is useless for the one thing people actually need in the morning, which is whether tonight's preparation is for something happening tomorrow. Render tomorrow as a short secondary strip, clearly labelled, not mixed into today.

Record each calendar's state in the source map.

## Step 3 — What arrived, and what is still waiting

**Email.** `mcp__Gmail__search_threads`:

- `newer_than:1d in:inbox -category:promotions -category:social` — the overnight arrivals
- `newer_than:{inbox.lookbackDays}d in:inbox is:unread -category:promotions -category:social` — the ones that never got dealt with
- one pass for dated commitments, per `source-discipline.md`, scoped to anything falling today or tomorrow

Suppress `inbox.noiseSenders` / `inbox.noiseSubjects` per the noise rule, and count the suppressions.

**Chat.** If a Slack connector is available, read the channels and DMs that carry direct asks — mentions, threads the owner is in, unanswered DMs — bounded to the last day. If it is not available, that is `unavailable`, and it goes in the footer as *chat not checked*. It does not go in as silence.

Confirm anything you intend to assert by reading the message, not the preview. A brief that says "Michael needs an answer on the deck" and is wrong about which thread costs more than it saves.

## Step 4 — Today's flags

Apply `flag-detection.md` scoped to today and tomorrow:

- overlapping timed events today, split into real clashes and duplicate invites
- a locally-anchored event inside a travel span in another city
- any deadline today or tomorrow with no prep block behind it
- zero-duration entries, rendered without a duration

A day with no flags renders an explicit "no clashes today" line. Absence of a flag section would read as absence of checking.

## Step 5 — Build the file

One self-contained HTML page per `briefing-design.md`, in the same visual family as the commitment calendar — same type scale, same category colours, same flag marks — but laid out as a day rather than a grid:

- **Today**, hour-ordered, every commitment as a chip with its source
- **Tomorrow**, a short strip, clearly secondary
- **Needs an answer** — overnight arrivals and still-unread asks, each with sender, thread subject, and what is actually being asked
- **Close deadlines** — anything due today, tomorrow, or with prep that should have started already
- **Footer** — the source map with all three states, the fetch timestamp in `owner.timezone`, the suppressed-message count, and any caveat

Write it to the sandbox first. Do not compose the page into a message.

## Step 6 — Deliver, save, open

Same delivery contract as the commitment calendar, with `output.morningFilename`:

1. `SendUserFile`, keep the `file_uuid`.
2. `mcp__remote-devices__get_device_info`; request `output.directory` once if it is not connected, reason `"Saving your morning brief."` If declined or timed out, stop and say so — do not retry more than once.
3. `mcp__remote-devices__device_commit_files` to `{output.directory}/{output.morningFilename}`, `force: true`. That path and no other.
4. If `output.openAfterWrite`, open it — Chrome control first, `osascript` fallback, and if neither is available say so rather than treating the run as failed.

## Step 7 — Report

Two or three sentences: the shape of the day, the one thing most likely to be missed, and any source that was `unavailable`. Nothing more — the page is the brief.

---

## Boundaries

- Writes exactly one path: `{output.directory}/{output.morningFilename}`.
- Reads only. It never replies, never marks read, never accepts an invitation, never posts to chat.
- Never asserts an ask without having read the message it came from.
- Never renders an unread source as a quiet one.
