---
read_when: "loop_tick.py and loop_verify.py load this before any state change. The column-ownership table and the seven verifier checks here are non-negotiable."
status: canonical
---

# Synergy Engine prep loop — contract

The prep loop owns the **unsupervised** half of the engine: fingerprint refresh, discovery, citation harvest, and staging draft rows into the tracker as `Ready for review`. Everything that touches the outside world — comments, connects, emails, accept-replies, live content edits — stays on the human side. This file is the seam.

## The non-negotiable rule

The loop **never sends, comments, connects, posts, likes, edits live content, or flips any status past `Ready for review`.** If the verifier detects the loop touched the send side, it hard-stops the loop, writes `LOOP_VIOLATED_HUMAN_GATE` into state, and refuses to resume. This rule comes from `references/cadence-and-guardrails.md` and is restated here because it is the loop's whole reason to exist.

## Tracker column ownership

The xlsx tracker (schema: `references/tracker-schema.md`) is shared state between the loop and the human. Ownership is per-column, not per-row, and is strict.

| Col | Field | Owner | Notes |
|---|---|---|---|
| A | Target | Loop | Set on discovery; never edited after |
| B | Persona | Loop | From the legal enum in tracker-schema |
| C | Tier | Loop | A / B / C / peer |
| D | Path | Loop | A / B / GA / cite-only / cited |
| E | Synergy | Loop | High / Medium / Low / Cold |
| F | LinkedIn Profile | Loop | Full `/in/<slug>/` URL |
| G | Last Touch | **Human** | Loop must never write |
| H | Liked | **Human** | Loop must never write |
| I | Commented | **Human** | Loop must never write |
| J | Comment / engagement summary | Loop | The draft itself |
| K | Cited URL | Loop | Must HEAD-200 verify before write |
| L | Connect / DM | **Human** | Loop must never write |
| M | Status | **Shared (gated)** | Loop may write only `Not started`, `Queued`, `Ready for review`. All other values are human-owned. |
| N | Next Action | Loop | Exact next move; for queued rows includes the post URL |
| O | Next Action Date | Loop | Drives the queue |
| P | Notes | Loop (append-only) | Loop may append; never delete or rewrite |

A loop-written row at minimum has `A, B, C, D, E, F, J, M=Ready for review, N, O` populated. If `Path` is `A`, `GA`, or `cited`, `K` is also required.

## Status values the loop is allowed to write

`Not started`, `Queued`, `Ready for review`. That's it. Every other status (`Posted`, `Pending accept`, `Accepted`, `Replied`, `Engaged`, `Parked`, `Cold`) is human-only and triggers verifier check #4 if the loop writes it.

## The seven verifier checks

`loop_verify.py` runs these in order, every tick, after the tick has done its one unit of work. All seven are deterministic and use no LLM call. Any failure aborts the tick.

1. **Tracker integrity.** The xlsx opens; sheet `Outreach Tracker` exists; columns A-P are present and named per schema; no duplicate `(Target, LinkedIn Profile)` rows.
2. **Schema-valid writes.** Every row written this tick has its required columns populated and every enum field (`Persona`, `Tier`, `Path`, `Synergy`, `Status`) holds a value from the legal set in `references/tracker-schema.md`.
3. **Citations verified.** For every row with `Path` in `{A, GA, cited}` written this tick, `Cited URL` resolves to HTTP 200 on HEAD (with a 5s timeout, 1 retry), and `Comment / engagement summary` is non-empty.
4. **Human gate untouched.** No row this tick has `Liked`, `Commented`, `Connect / DM`, `Last Touch`, or `Status` written to any value other than `Not started`, `Queued`, or `Ready for review`. If this check fails: **hard stop, write `LOOP_VIOLATED_HUMAN_GATE` to state, alert, do not resume.**
5. **Quota envelope.** Daily API counters under their per-day ceilings (`max_apify_per_day`, `max_apollo_per_day`, `max_openalex_per_day`). Weekly LinkedIn connect envelope (~100/wk, ~20-25/day from `cadence-and-guardrails.md`) honored across the loop's draft activity even though the loop itself doesn't send.
6. **Calendar block present.** If `handoff.drafts_ready_for_review >= N`, a future Google Calendar event in the configured window exists with the agreed title pattern.
7. **Progress signal.** At least one of: queued count grew, citation-registry pending shrank, drafts-ready grew, fingerprint was refreshed. If none, increment `consecutive_no_progress_ticks`; at 3 in a row, hard stop.

## Exit codes from `loop_tick.py`

The cron reads these.

| Code | Meaning |
|---|---|
| 0 | Tick succeeded; verifier passed; not yet done |
| 10 | Goal met (batch ready and calendar block booked); stop clean |
| 20 | Hard stop (budget, no-progress cap, deadline, or check #4) |
| 30 | Transient error (network, API timeout); retry next tick |
| 40 | Quota ceiling hit today; back off to next day |

## Bounds (all enforced by `loop_verify.py` or `loop_tick.py`)

- `max_ticks_per_week`: default 5
- `max_consecutive_no_progress`: default 3
- `max_apify_per_day`: default 200
- `max_apollo_per_day`: default 100
- `max_openalex_per_day`: default 500
- `budget_usd_remaining`: required; loop will not start without one
- `wall_clock_deadline_utc`: optional but recommended; the loop stops at this instant even mid-tick

## Atomic state writes

`loop_state.py` writes `state.json` by writing `state.json.tmp`, fsyncing, and renaming. A half-written state file is never readable. The loop refuses to start if `state.json` is unreadable or fails schema validation against `schema_version`.

## What this loop does not own

- Anything in `references/outreach-channels.md` Part 2 (the connect-note send discipline). That's purely human-side.
- The "Post as" identity selector. The loop never opens LinkedIn.
- Choosing which row to engage at the calendar block. The loop only stages; the human picks.
- The reply step on accepted invites. `synergy-cite-accept-check` stays a human-gated command.

If a future change ever asks the loop to do any of the above, that change has to first delete this contract file, on the record.
