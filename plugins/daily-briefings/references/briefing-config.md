# The briefings config

Every person-specific value this plugin needs lives in one JSON file. Nothing in the skills hard-codes an address, an email, a calendar id, a filename, or a newsletter to ignore. If you find yourself about to write one into a skill, it belongs here instead.

## Where it lives

`MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/briefings.config.json`

Same shelf as `github-pat.env` and `openrouter.env`, for the same reason: it is shared team knowledge, it is read at run time, and it is not secret enough to need a vault of its own. It holds no credentials. If it ever needs one, the credential goes in its own `.env` next to the others and this file holds only the name of the variable.

Resolve the vault root the way every MoxyWolf skill does: the mounted `MoxyWolf Vault` root. If the vault is not mounted, request it before reading.

## Reading it

1. Read the file. If it parses, use it.
2. If the file is **missing**, do not guess and do not invent an owner. Say the config is missing, name the path, and tell the user to run `/briefings-setup`. In an unattended run, fall back to the defaults below for everything except `owner` and `calendars.primary`, render what you can, and put the missing-config note in the footer as a caveat rather than failing silently.
3. If the file is **present but a key is absent**, use that key's default from the table below. Never treat an absent key as a reason to stop.
4. If the file is present but **malformed**, report the parse error verbatim and stop. A half-read config is worse than none.

## Shape

```json
{
  "owner": {
    "name": "Given Family",
    "email": "person@example.com",
    "timezone": "America/Los_Angeles"
  },
  "calendars": {
    "primary": "person@example.com",
    "holiday": "en.usa#holiday@group.v.calendar.google.com",
    "alsoCheck": [],
    "expectedEmpty": []
  },
  "window": {
    "days": 14,
    "weekStartsOn": "monday"
  },
  "categories": [
    "Client & Partner",
    "Personal & Health",
    "Travel & Reservations",
    "Deadline",
    "Community & Events",
    "Holiday"
  ],
  "inbox": {
    "lookbackDays": 21,
    "noiseSenders": [],
    "noiseSubjects": [],
    "extraQueries": []
  },
  "anchors": {
    "localVenues": [
      { "label": "Gym", "address": "", "city": "" }
    ],
    "homeCity": ""
  },
  "output": {
    "directory": "~/Downloads",
    "calendarFilename": "next-14-days-calendar.html",
    "morningFilename": "morning-brief.html",
    "openAfterWrite": true
  },
  "schedule": {
    "calendarCron": "0 14 * * 1-5",
    "morningCron": "0 15 * * 1-5",
    "notifications": { "push": true, "email": false }
  }
}
```

## Keys

| Key | Default if absent | What it does |
|---|---|---|
| `owner.name` | *no default — required* | Named in the footer as the person the briefing is for. Never fabricate one. If it is absent, write "owner not configured" rather than a guess. |
| `owner.email` | *no default — required* | The account the calendar and inbox are read from. |
| `owner.timezone` | `America/Los_Angeles` | Every time in the render is expressed in this zone. Foreign-timezone source data is converted, and the conversion is shown in the chip note. |
| `calendars.primary` | `owner.email` | The main calendar. |
| `calendars.holiday` | `en.usa#holiday@group.v.calendar.google.com` | Public-holiday feed. Set to `null` to skip it. |
| `calendars.alsoCheck` | `[]` | Extra calendar ids to pull. |
| `calendars.expectedEmpty` | `[]` | Calendars that are normally empty. Check them anyway; if one is empty, that is expected and is not worth a caveat line. If one is *not* empty, that is worth surfacing. |
| `window.days` | `14` | Window length, counting today. The grid still starts on the week-start before the window and ends on the week-end after it. |
| `window.weekStartsOn` | `monday` | `monday` or `sunday`. |
| `categories` | the six in the shape above | The category set the chips colour by. This is a *starting* set, not a closed one — see below. |
| `inbox.lookbackDays` | `21` | How far back the dated-commitment sweep reaches. |
| `inbox.noiseSenders` | `[]` | Senders whose mail is newsletter or blast traffic. Suppressed unless the message carries a real deadline the owner has replied to. |
| `inbox.noiseSubjects` | `[]` | Subject substrings with the same treatment. |
| `inbox.extraQueries` | `[]` | Additional Gmail queries appended to the standard set. |
| `anchors.localVenues` | `[]` | Places physically fixed to one city. Used for location-clash detection: a locally-anchored event inside a travel span in another city is a clash. |
| `anchors.homeCity` | `""` | The city the owner is in when no travel span says otherwise. |
| `output.directory` | `~/Downloads` | Where the rendered file lands on the owner's machine. |
| `output.calendarFilename` | `next-14-days-calendar.html` | Overwritten each run by design — see the write boundary below. |
| `output.morningFilename` | `morning-brief.html` | Same. |
| `output.openAfterWrite` | `true` | Whether to open the file after writing it. |
| `schedule.calendarCron` | `0 14 * * 1-5` | UTC cron for the commitment-calendar scheduled task. |
| `schedule.morningCron` | `0 15 * * 1-5` | UTC cron for the morning-brief scheduled task. |
| `schedule.notifications` | `{ "push": true, "email": false }` | Completion-notification channels for both scheduled tasks. |

## Categories are derived, not dictated

The `categories` list is the set seen so far, and it exists so colours stay stable between runs rather than reshuffling every morning. Derive categories from what the data actually contains. If the window holds something none of the configured categories fit, add a category for it in the render and say so in the footer, then suggest the config gain it. Do not force a commitment into a category that misdescribes it, and do not drop a commitment because no category fits.

## The write boundary

These skills write exactly two paths, both inside `output.directory`, both named by the config: the calendar file and the morning-brief file. Each run overwrites its own prior copy, which is the intended behaviour and the reason an unattended run is safe.

Never write any other path on the owner's machine. Never write outside `output.directory`. If a run would need to, stop and ask instead — that is a change of scope, not a render.

## Cron is UTC

Both cron fields are evaluated in UTC. `0 14 * * 1-5` is 7am in `America/Los_Angeles` while it is on daylight time and 6am while it is not. The plugin does not shift the cron across the DST boundary; if the owner wants a fixed local hour year-round, they change the cron twice a year, and `/briefings-setup` says so when it registers the task.
