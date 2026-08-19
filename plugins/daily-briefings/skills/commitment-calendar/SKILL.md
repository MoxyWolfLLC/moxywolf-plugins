---
name: commitment-calendar
risk_tier: generate
description: >
  Build a rolling N-day commitment calendar as one self-contained HTML file — every calendar event plus every dated commitment found in the inbox, laid out on a week grid, with double-booking, duplicate-invite, location-clash and unprepped-deadline flags. Use when the user asks for their commitment calendar, their next two weeks, what is coming up, a look-ahead, where the clashes are, which deadlines have no prep time, or invokes /commitment-calendar. Also the skill a scheduled daily run of that briefing invokes. Writes to the configured output directory and opens the result.
---

# Commitment calendar

One file, one window: today through today plus `window.days - 1`, rendered as a week grid with everything the owner has committed to, from wherever it lives.

The value is not the grid. Every calendar app has a grid. The value is the three things a calendar app will not tell you: which of these overlaps are real clashes rather than the same invite twice, which deadlines have nothing blocked in front of them, and which commitments are sitting in email where the calendar cannot see them.

Read these before you start, and follow them rather than the summaries here:

- `${CLAUDE_PLUGIN_ROOT}/references/briefing-config.md` — every person-specific value, and what to do when the config is missing
- `${CLAUDE_PLUGIN_ROOT}/references/source-discipline.md` — the three source states, and the bar for plotting an email
- `${CLAUDE_PLUGIN_ROOT}/references/flag-detection.md` — the five flags, defined mechanically
- `${CLAUDE_PLUGIN_ROOT}/references/briefing-design.md` — what the file looks like

## Unattended by default

This skill is built to run with nobody watching. When it is invoked by a scheduled task, **do not ask clarifying questions** — resolve what you can from the config, make the honest choice where the config is silent, and put anything unresolved in the footer caveats where the owner will read it later. Asking a question into an empty room fails the run.

When a person invokes it interactively, the same discipline still applies. There is nothing here worth interrupting for.

---

## Step 1 — Anchor the date

Run `date` in bash. Do not infer today from context, a filename, or a previous message; a briefing built on the wrong day is wrong in every cell.

The window is today through today + `window.days - 1`, inclusive. The **grid** runs wider than the window: from the `weekStartsOn` day on or before the window's first day, through the week-end on or after its last.

Load the config now (`briefing-config.md`). Everything below reads from it.

## Step 2 — Pull the calendars

`mcp__Google_Calendar__list_calendars` first, so you know what exists rather than assuming. Then `mcp__Google_Calendar__list_events` on each of:

- `calendars.primary`
- `calendars.holiday`, unless it is `null`
- everything in `calendars.alsoCheck`
- everything in `calendars.expectedEmpty` — check them, expect nothing, and only surface them if they are not empty

Pass `startTime` / `endTime` covering the whole window, `timeZone` from `owner.timezone`, `orderBy: startTime`, `pageSize: 250`. Page until exhausted; a truncated pull silently drops the back half of the window.

If a `list_events` response is too large for context it gets written to a file. Do not read that file whole — `jq` it into TSV of `[start, end, summary, location, attendee count, description]` and work from that.

Record each calendar's state in the source map: `ok`, `unavailable`, or `not checked`.

## Step 3 — Sweep the inbox for dated commitments

The calendar knows about the meetings someone else scheduled. It does not know about the thing the owner agreed to in a reply. That is what this step is for.

Run `mcp__Gmail__search_threads` with the standard set, substituting `inbox.lookbackDays`:

- `newer_than:{lookback}d (deadline OR "due date" OR "due by" OR "submit by" OR "no later than" OR RSVP OR expires OR "last day" OR "action required")`
- `in:inbox newer_than:{window.days}d -category:promotions -category:social`
- everything in `inbox.extraQueries`

Suppress `inbox.noiseSenders` and `inbox.noiseSubjects` per the noise rule in `source-discipline.md` — with the two exceptions it names, and **count what you suppressed** for the footer.

For every surviving candidate, `mcp__Gmail__get_thread` with `messageFormat: PLAIN_TEXT` and confirm the date **in the body** before plotting anything. Explicit dates only; convert foreign timezones to `owner.timezone` and show the conversion in the chip note. Undated but real goes to *Open loops*.

Record Gmail's state in the source map.

## Step 4 — Categorise

Assign each commitment a category from `config.categories`, in that order, so colours stay stable run to run. Derive a new category if the data genuinely calls for one, use it, and name it in the footer. Never force a commitment into a category that misdescribes it, and never drop one because nothing fits.

## Step 5 — Detect the flags

Apply all five rules in `flag-detection.md` exactly as written: double-booking, duplicate calendar entries, location clash, unprepped deadline, zero-duration entries. Keep real clashes and duplicates in separate counts.

## Step 6 — Build the file

One self-contained HTML file per `briefing-design.md`: grid, legend, stats strip, flags, the two card sections below the grid, and the footer carrying the source map, the fetch timestamp, and every caveat.

Write it into the sandbox first. Do not compose HTML into a message.

## Step 7 — Deliver, save, open

1. `SendUserFile` on the file. Keep the `file_uuid` — it is the handle for the next step, and it is also the delivery that survives if the rest fails.
2. Check `mcp__remote-devices__get_device_info`. If `output.directory` is not in `connectedFolders`, request it once with `mcp__remote-devices__device_request_folder_access`, reason `"Saving your commitment calendar."` **If that is declined or times out, stop here and say so plainly.** Do not retry more than once — a second dialog into an empty room is noise, and the file already reached the conversation.
3. `mcp__remote-devices__device_commit_files` with that `file_uuid` to `{output.directory}/{output.calendarFilename}`, `force: true`. The force is deliberate and scoped: this path is the skill's own prior output and nothing else. Never write any other path.
4. If `output.openAfterWrite`, open it — `mcp__remote-devices__Control_Chrome__open_url` with the `file://` URL and `new_tab: true`. If Chrome control is unavailable, fall back to `mcp__remote-devices__Control_your_Mac__osascript` running `do shell script "open '<path>'"`. If both are unavailable, say so; do not treat it as a failed run.

## Step 8 — Report

Three or four sentences. What changed versus a normal day, any new clash, and any deadline now inside the window with nothing blocked in front of it. Name any source that was `unavailable` or `not checked`, because that is the part the file's reader most needs told twice.

Do not recap the calendar. The file is the recap.

---

## Boundaries

- Writes exactly one path: `{output.directory}/{output.calendarFilename}`. Nothing else on the owner's machine, ever.
- Reads only. It never accepts an invitation, replies to a thread, creates an event, or moves anything.
- Never invents a commitment, a date, a duration, or a person's name. An item with no confirmed date is an open loop, not a chip.
- Never renders an unread source as an empty one.
