# The ultradian curve and the day ledger

Two things live here: the one home for the owner's measured curve, and the schema of the file that carries a day's state between cold runs. Nothing else in this plugin restates either. If you are about to write a start time, a band, or a window into a skill or a trigger prompt, it belongs here instead.

## Why the curve is config

The frog window was previously stated inside the 07:00 trigger prompt, with a comment telling a future human to edit that paragraph if the survey changed. It also exists in the owner's Body Clock Audit. Two homes for one rule is how a rule goes stale without anyone noticing, and the failure is silent: the briefing keeps flagging a window the owner no longer works. One home, and every reader reads it.

## The `ultradian` block in `briefings.config.json`

**The block below is an illustration, not a curve.** Its bands peak in the morning. The owner
this was built for peaks at 19:00, so copying it would produce a plan that looked measured and
was backwards. `check_curve()` in the block planner refuses to run against it, and refuses any
curve whose `curveSource` is empty. Both refusals are hard stops. The owner's real fragment,
derived from the Daily Architecture survey, is in `06 – Engineering/ultradian.config-fragment.json`.

```json
"ultradian": {
  "blockMinutes": 75,
  "recoveryMinutes": 15,
  "dayStart": "08:00",
  "dayEnd": "21:00",
  "maxBlocksPerDay": 6,
  "bands": [
    { "band": "peak", "start": "08:00", "end": "11:00" },
    { "band": "high", "start": "11:00", "end": "13:00" },
    { "band": "low",  "start": "13:00", "end": "16:00" },
    { "band": "high", "start": "16:00", "end": "19:00" },
    { "band": "peak", "start": "19:00", "end": "21:00" }
  ],
  "frogWindow": { "start": "19:00", "end": "21:00", "workdaysOnly": true },
  "curveSource": "Body Clock Audit, Daily Architecture survey, 2026-09",
  "ledgerDirectory": "_Shared Knowledge/Agents and Plugins/sprint-ledger",
  "evidenceSources": {
    "github": { "repos": [], "author": "" },
    "vault":  { "paths": [] },
    "gmail":  { "enabled": true },
    "web":    { "urls": [] }
  }
}
```

| Key | Default if absent | What it does |
|---|---|---|
| `blockMinutes` | `75` | Focus length. The sprint is this plus `recoveryMinutes`. |
| `recoveryMinutes` | `15` | Recovery inside the sprint, not tacked on after it. |
| `dayStart` / `dayEnd` | `08:00` / `21:00` | The outer bounds. No block starts before or ends after. |
| `maxBlocksPerDay` | `6` | Cost and sanity ceiling. Each block with a commitment costs one scheduled check-in. |
| `bands` | *no default, required* | The measured curve, and only the hours that were actually measured. Ranges labelled `peak`, `high` or `low`. An hour inside no range is `unmeasured`, which ranks above `low` and below `high`. Leave gaps rather than filling them: a guessed band is a claim the survey never made. |
| `frogWindow` | *no default, required* | The owner's highest-value deep-work window. Reserved before the rest of the day is filled. |
| `curveSource` | *no default, required* | Where the curve came from and when. Empty is a hard stop. Printed in the close email so a stale curve is visible rather than assumed. |
| `ledgerDirectory` | `_Shared Knowledge/Agents and Plugins/sprint-ledger` | Relative to the vault root. The only directory this skill writes. |
| `evidenceSources` | all empty | Which surfaces may be queried for proof. An empty source is `not checked: not configured`, never a clean miss. |

## `unavailable`: availability, which is not capacity

`bands` says when the owner's brain is sharp. `unavailable` says when the owner is not free. They
are different facts and neither substitutes for the other. A curve alone will hand someone a deep
work block at the hour they are at the table.

```json
"unavailable": [
  { "start": "17:00", "end": "19:00", "label": "last meal",
    "source": "Body Clock Audit Part C, 2026-09-23; clearance 3h before sleep onset 23:30" }
]
```

Every entry needs a `source`, and `check_curve()` refuses one without it. The rule is the same as
the curve's: a window that blocks the owner's day has to be derived from something a reader can
re-check, not typed in because it seemed right. Part C of the Body Clock Audit is what derives the
meal window, from the owner's own meal times and the gap they say they keep before sleep. The
audit supplies no number of its own.

`dayEnd` is availability too, and it clamps the frog window rather than shortening it. A frog
window measured at 19:00 to 21:00 with a day that ends at 20:30 yields exactly one evening block.
The measured window stays 19:00 to 21:00 in the config, because that is what the instrument said.

## Conflicts are stated, never resolved

`curve_conflicts()` returns plain sentences and the plan carries them. Three cases:

- an `unavailable` window overlapping the frog window, which is the one that matters most: the
  owner's best hours and a body constraint are competing for the same seat
- an `unavailable` window overlapping any `peak` or `high` band
- a frog window running past `dayEnd`

None of these is resolved automatically. A silent reshuffle hides the trade the owner should be
making, and silently planning anyway schedules work into an hour that does not exist.

There is no key that relaxes the evidence rule. That is deliberate.

## The ledger

One file per day, `YYYY-MM-DD.json`, in `ledgerDirectory`. It is the agent's entire memory. Every run is cold, so anything not in this file does not exist.

```json
{
  "date": "2026-09-23",
  "timezone": "America/Los_Angeles",
  "generatedAt": "2026-09-23T07:04:11-07:00",
  "curveSource": "Body Clock Audit, Daily Architecture survey, 2026-09",
  "blocks": [
    {
      "id": "B1",
      "start": "08:00",
      "end": "09:15",
      "band": "peak",
      "focusMinutes": 75,
      "recoveryMinutes": 15,
      "inFrogWindow": false,
      "commitment": "Draft the AI Governance spoke",
      "commitmentId": "c1",
      "commitmentSource": "commitment-calendar",
      "evidence": {
        "expect": [
          { "type": "github_commit", "repo": "MoxyWolfLLC/FrontierFounder", "pathPrefix": "content/blog/" }
        ]
      },
      "status": "planned",
      "verifiedBy": [],
      "checkedAt": null,
      "note": "",
      "triggerId": null
    }
  ],
  "sources": { "github": "ok", "vault": "ok", "gmail": "unavailable: not connected in this run" },
  "caveats": [],
  "rollupAppended": false
}
```

### Block status

| Status | Set when | Never set by |
|---|---|---|
| `open` | The slot exists and carries no commitment. | anything |
| `planned` | A commitment is assigned and the boundary has not passed. | anything |
| `verified` | An artifact from this block's declared `expect`, with its own timestamp inside `[start, end]`. | the owner's answer, a ticket's column, an inference |
| `self-reported` | The owner answered and no qualifying artifact was found. | silence |
| `unknown` | The boundary passed, no artifact, no answer. | nothing; this is the honest floor |
| `skipped` | The owner said the block did not happen. | the agent's own judgment |

`verifiedBy` holds objects, never booleans:

```json
{ "surface": "github", "id": "0783b35", "at": "2026-09-23T08:41:02-07:00", "detail": "content/blog/complete-report-isnt-evidence.md" }
```

A proof nobody can re-check later is not a proof. The identifier, the surface and the timestamp are captured at the moment of the check, because nothing re-reads them afterwards.

### The rollup

`_rollup.json` is an array, one row per day, appended by `close`:

```json
{ "date": "2026-09-23", "planned": 4, "verified": 2, "selfReported": 1, "unknown": 1, "ledger": "2026-09-23.json" }
```

The ledger filename travels with the row because the row is a summary and the ledger is the only thing that can prove it. A row whose ledger has been deleted is unfalsifiable, and it should be read that way.

## Links this design holds, and how each one drifts

Stated plainly because this plugin's own shop published the paper on it:

- **Block id to commitment.** Stable only inside one ledger. A check-in resolves its block by start time, never by array position, because a mid-day re-plan renumbers.
- **Ledger filename to day.** The date is in the filename and again in the body. They are compared on every open, and a mismatch is a hard stop rather than a preference for one of them.
- **`triggerId` to a live scheduled task.** A deleted or expired task leaves an id that still looks live. Verify with `list_triggers` before reusing or deleting.
- **`verifiedBy` id to an artifact.** Captured once and never re-read. That is acceptable only because the surface and timestamp are captured with it, which is what makes the claim checkable by a person later.
- **Rollup row to ledger.** Named above.
