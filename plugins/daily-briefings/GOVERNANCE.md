# daily-briefings — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md).

Every skill and command below declares a risk tier and is held to the five tests:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action (sending messages, creating external events, writing to shared systems).
2. **A named human signs** — high-tier output requires one *named* human to approve, and the approval is recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

## Risk surface

daily-briefings reads the owner's own calendar, inbox and chat, and renders what it finds as HTML on the owner's own machine. It sends nothing, replies to nothing, accepts no invitation, creates no calendar event, and writes to no shared or customer system. Its only external side effects are two, and they are different in kind.

**The render write is bounded by construction.** Each skill writes exactly one path — the filename named in `output` inside the directory named in `output` — and overwrites its own prior copy. That is why an unattended run is safe: the write is idempotent, self-scoped, and destroys nothing but yesterday's version of itself. Writing any other path is out of scope and requires a confirmation, which makes it a different task rather than a wider render.

**The setup write is not bounded, so it is gated.** `/briefings-setup` writes a config into the shared vault and registers recurring scheduled tasks. A scheduled task is an automation that outlives the session that made it, so nothing is created until the owner has seen the exact JSON, the exact cron, the resolved local time, and the exact prompt text, and said yes. It reads `list_triggers` first and updates in place rather than creating a duplicate, because two scheduled tasks writing one file is a bug that presents as a mystery.

**Test 3 is where this plugin does its real governance work.** The output is claim-bearing — it asserts where the owner is expected to be and what is owed. Three rules carry it: every chip names its source; a date is only plotted when it is explicit in the message body, with any timezone conversion shown; and a source that could not be read is reported as `not checked`, never as empty. The last one is the load-bearing rule. A briefing that renders a clean grid because Gmail was disconnected is not a quiet week, it is a blind spot wearing the costume of good news — and it fails silently, at the moment the owner most needs it not to. The footer carries a three-state source map on every run, whether or not anything went wrong, so its silence means something.

## Skill / command risk tiers

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `commitment-calendar` — read calendars + inbox, render, write one configured file | generate | Read-only against every source. Writes exactly `{output.directory}/{output.calendarFilename}`, overwriting only its own prior output; any other path is out of scope. Provenance per Test 3: source on every chip, explicit dates only, three-state source map in the footer. |
| `morning-brief` — read calendars + inbox + chat, render, write one configured file | generate | Same posture and same bounded write, against `{output.morningFilename}`. Asserts nothing it has not read the underlying message for. An absent Slack connector renders as *chat not checked*, never as silence. |
| `briefings-setup` — write vault config + register recurring scheduled tasks | side-effectful-gated | Tests 1 and 5. Exact JSON, exact cron with the resolved local time and the DST caveat, and exact prompt text shown before anything is written or registered. Reads `list_triggers` first and updates in place. Uses `create_trigger`, never `CronCreate`. Proposes task deletion; never deletes. |
| `/commitment-calendar` (command) | generate | Dispatches the skill; inherits its write boundary. |
| `/morning-brief` (command) | generate | Dispatches the skill; inherits its write boundary. |
| `/briefings-setup` (command) | side-effectful-gated | Dispatches the skill; inherits its confirm gates. |

## Unattended operation

Both render skills are built to run from a scheduled task with nobody watching, and both are told not to ask clarifying questions in that mode. That is a deliberate trade and it is only defensible because of the tier: neither skill can take an action that matters to anyone but the owner, and the one thing it does write is its own prior output. What would otherwise have been a question becomes a footer caveat, which is the right place for it — the owner reads the footer when they read the file, which is after the run rather than during it.

The setup skill is the opposite: it is never unattended. It is the only place in this plugin where something is created that outlives the session, and it stops for a human every time.
