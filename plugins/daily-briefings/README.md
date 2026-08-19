# daily-briefings

Two scheduled briefings that arrive as self-contained HTML on your own machine, plus the setup command that makes them yours.

Every calendar app can show you a grid. What none of them tell you is which of your overlaps are real clashes rather than the same invite twice, which of your deadlines have nothing blocked in front of them, and — the big one — how much of what you actually owe never reaches a calendar at all.

A ticket due Thursday, a pull request open eleven days, a post that will publish itself on Friday whether or not you remember, an invoice going overdue, a contract renewing, an envelope waiting on your signature, a decision record parked at *proposed* since the sixth. None of those are on anybody's calendar. All of them are commitments. Putting them on one grid is what this plugin is for.

## Commands

| Command | What it does |
|---|---|
| `/commitment-calendar [days]` | Builds the rolling window — 14 days by default — as a week grid. Every calendar event, plus every dated commitment found in the inbox, with the five flags. Optional argument overrides the window for that run only. |
| `/morning-brief` | Today and tomorrow, what arrived overnight, what still needs an answer, close deadlines, today's flags. Same sources, same rules, one day. |
| `/crm-sync-health` | Read-only check on a CRM sync pipeline in Supabase — stuck runs, budget-exceeded errors, stale sources. One line on a healthy day. Fixes nothing, ever. |
| `/briefings-setup` | Writes your config into the vault and registers the recurring scheduled tasks. Idempotent — run it again to change a time, add a venue, enable a surface, or mute a noisy sender. |

## The flags

| Flag | What it catches |
|---|---|
| Double-booking | Two timed events whose intervals actually overlap. Touching edges are a tight day, not a clash. |
| Duplicate calendar entries | The same invite accepted twice. Surfaced as clutter, counted separately, so the clash number stays a number you act on. |
| Location clash | A standing local commitment sitting inside a trip to another city. It has not noticed you are away. |
| Unprepped deadline | A hard deadline with nothing that looks like preparation in the three days before it. Every one is flagged; none are ranked or quietly excused. |
| Zero-duration entries | Rendered without a duration and named in the footer, rather than given an invented fifteen-minute box. |

## What it sweeps

The calendar and the inbox, plus every work surface you switch on. Full definitions — what each one pulls, what earns a place on the grid, and what becomes an open loop — are in [`references/work-surfaces.md`](references/work-surfaces.md).

| Domain | Surfaces | The dates it finds that nothing else will |
|---|---|---|
| Development & delivery | team board, repositories, deployments, database advisories | due-dated tickets, milestone dates, **domain renewals**, release dates |
| Marketing & content | scheduled social posts, content in flight, outreach queues, events | publish times, campaign sends, outreach follow-ups, and the *deliverable* behind an event rather than just the event |
| Competition & search | rank and site-audit tracking, competitor watch, product analytics | **experiment end dates**, staged rollouts, scheduled crawls |
| Revenue, finance & legal | invoices and bills, payroll and tax, contracts, pipeline, business plan | invoice and bill due dates, **payroll approval cutoffs**, **contract renewals**, envelope expiry, committed close dates, plan milestones |
| Operations & governance | the scheduled-task registry, decision records, project hygiene | what will fire on its own, decide-by dates |

Two of those deserve calling out because they are the ones people are most surprised to see. **Domain and contract renewals** exist nowhere on a calendar and cost real money to miss. **The scheduled-task registry** tells you both what is about to run without you and — more usefully — which of your automations has quietly stopped firing, which nothing else in your day will ever mention.

### Open loops are the other half

Most of these surfaces yield more undated obligations than dated ones, and the *Open loops* section is where they land, grouped by surface. On a typical day it will be longer than the grid. That is not a defect, it is the accurate shape of the work: an eleven-day-old pull request, a draft stalled at a sign-off gate, a deal past its close date, a decision nobody has signed.

### Cost is managed by tier, not by silence

Surfaces run at `always`, `daily`, `weekly`, or `off`. An ad-hoc run does the cheap core; the scheduled run does more; `--full` does everything, for the day the question is *what am I forgetting*. **Whatever gets skipped is named in the footer with its reason.** A surface with no parameters configured reports as `not checked: not configured` — never as a clean result, which is how a misconfigured surface would otherwise look like good news for a month.

## What makes it trustworthy

**A source that could not be read is reported as *not checked*, never as empty.** This is the rule the whole plugin is built around. The failure it prevents is the one that actually happens: the calendar reads fine, Gmail is not connected, and the grid renders a clean two weeks that looks like good news. Every run carries a three-state source map in the footer — `ok`, `unavailable`, `not checked` — whether or not anything went wrong, so its silence means something.

**Only explicit dates get plotted.** An email commitment reaches the grid only when the date is confirmed in the message body, with any timezone conversion shown in the chip note so you can catch it when it is wrong. Real-but-undated asks go to *Open loops*, which is a different kind of object and gets its own section rather than a made-up slot.

**Every chip names its source.** Calendar events name their calendar; email-sourced chips are prefixed `✉` and name the sender and thread, so you can see at a glance what your calendar does not know about.

## Configuration

Everything person-specific lives in one file:

```
MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/briefings.config.json
```

Same shelf as `github-pat.env` and `openrouter.env`, and it holds no credentials. Nothing in the skills hard-codes an address, an email, a calendar id, a filename, or a sender to ignore — owner and timezone, which calendars to pull, window length, category set, locally-anchored venues for clash detection, newsletter noise to suppress, where the files land, and the two cron schedules all live there.

`/briefings-setup` writes it for you. The full key reference, with defaults, is in [`references/briefing-config.md`](references/briefing-config.md).

Missing config is not fatal: the render falls back to documented defaults for everything except the owner and the primary calendar, says so in the footer, and points at `/briefings-setup`.

## Scheduling

`/briefings-setup` registers both tasks through the remote scheduled-task API, so they survive the session that created them. Cron is evaluated in UTC — `0 14 * * 1-5` is 7am Pacific on daylight time and 6am on standard time, and it does not shift itself. Setup shows you that conversion before it registers anything.

Run setup again any time to change a schedule; it updates the existing task in place rather than creating a second one.

## What it will not do

It reads, across all of it. It never replies, never marks anything read, never accepts an invitation, never creates a calendar event, never posts to chat, never transitions a ticket, never merges or comments on a pull request, never publishes or reschedules a post, never sends outreach, never issues or pays an invoice, never signs or sends an envelope, never edits a CRM record, never touches a deployment, and never fixes a sync.

That inertness is deliberate and it is what lets the sweep be this wide. A briefing that could also act would need a gate on every surface it touches, and would stop being something you can safely run before breakfast. Each render writes exactly one file — the one named in your config, in the directory named in your config — overwriting only its own previous copy.

The one place it stops for a human is `/briefings-setup`, which is the only thing here that creates something outliving the session. See [`GOVERNANCE.md`](GOVERNANCE.md) for the risk tiers.

## Files

```
plugins/daily-briefings/
├── commands/
│   ├── commitment-calendar.md
│   ├── morning-brief.md
│   ├── crm-sync-health.md
│   └── briefings-setup.md
├── references/
│   ├── briefing-config.md      # the config contract, every key, every default
│   ├── work-surfaces.md        # every surface swept, with its pull and its rules
│   ├── source-discipline.md    # three source states; the bar for plotting anything
│   ├── flag-detection.md       # the five flags, defined mechanically
│   └── briefing-design.md      # the shared visual language
├── skills/
│   ├── commitment-calendar/SKILL.md
│   ├── morning-brief/SKILL.md
│   ├── crm-sync-health/SKILL.md
│   └── briefings-setup/SKILL.md
├── GOVERNANCE.md
└── README.md
```
