---
description: Advance the synergy loop by one tick — plan the next step, execute it, resolve. Driven by the cron registered by /synergy-loop-start.
argument-hint: "<project-slug>"
allowed-tools: [Read, Bash, mcp__1be1916d-cb9d-4355-9832-c5b1b6332416__create_event]
---

# /synergy-engine:synergy-loop-tick — one bounded advance of the loop

This command is the recurring worker. The cron registered by `/synergy-loop-start` fires it on cadence (default every 6 hours). It plans the next step, executes it, records the outcome, and either exits with a continue/halt/goal-met code.

It **never posts**. The send half stays human-gated.

## STEP 1 — Plan

```bash
LOOPDIR="$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/.loop-state/<project>"
python3 -B "$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/scripts/loop_tick.py" plan "$LOOPDIR"
```

The plan call writes `next_step.json` and prints the same JSON to stdout. Parse it:

- **`exit_code = 10`** → goal met. Stop. Report and exit. The user runs `/synergy-run` to send the batch.
- **`exit_code = 20`** → hard stop. Print `halt_reason` from state, exit. Do not advance.
- **`exit_code = 40`** → quota backoff. Skip this tick. Cron will retry on the next fire.
- **`exit_code = 0`** with `step != IDLE` → execute the step (Step 2).

For any non-IDLE plan, the `manifest` block now also contains:

- `tick_id` — a short hex id for this tick
- `plan_nonce` — a 128-bit nonce minted at plan time. **You must capture this and pass it back on resolve.** Without it, resolve refuses to run.
- `release_owner` — the human accountable for whatever this tick produces (audit trail)
- `chain_audit_path` — where every issue/consume/reject event for this tick is appended

## STEP 2 — Execute the step

Each step maps to a concrete action. The plan's `slash_command` field tells you which one. Common steps:

| Step | Action |
|---|---|
| `REFRESH_FINGERPRINT` | Run `/synergy-engine:synergy-fingerprint`. Note: fingerprint hash will refresh on resolve. |
| `DISCOVER_AUTHOR` | Run `/synergy-engine:synergy-discover` with focus on author center. |
| `DISCOVER_CONTENT` | Run `/synergy-engine:synergy-discover` with focus on content center. |
| `HARVEST_CITATIONS` | Run `/synergy-engine:synergy-cite-harvest`. |
| `STAGE_DRAFTS` | Run the drafting logic from `/synergy-schedule` STEP 2's prompt (Path A/B, cite-then-tell, write to tracker as `Ready for review`). **Before each tracker row write**, mint a `tracker_nonce`; consume it after the write succeeds. |
| `BOOK_CALENDAR` | Call `mcp__...__create_event` to book a Google Calendar event titled "Review <project> outreach batch (<N> drafts)" in the configured window. **Mint a `calendar_nonce` immediately before the create call; consume it after the event ID comes back.** Capture the returned event ID. |
| `IDLE` | Should have been caught in Step 1. If you reach here, resolve with `result=skip` and `--plan-nonce ''`. |

For STAGE_DRAFTS and BOOK_CALENDAR, the mid-step nonce dance is:

```bash
TRACKER_NONCE=$(python3 -B scripts/loop_tick.py issue-tracker-nonce "$LOOPDIR" \
    --plan-nonce "$PLAN_NONCE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["nonce"])')
# ... do the tracker write ...
python3 -B scripts/loop_tick.py consume-nonce "$LOOPDIR" --kind tracker --nonce "$TRACKER_NONCE"
```

Same shape for `issue-calendar-nonce` / `--kind calendar` around the calendar create. Each nonce is single-use. A replay or mismatch fails the consume with exit 20 and writes a `nonce_replayed` / `nonce_consume_mismatch` row to `chain-audit.jsonl`.

Collect the metrics each action produced (e.g. how many drafts staged, calendar block ID, API call counts, USD spent) so the resolve call can record them.

## STEP 3 — Resolve

```bash
python3 -B "$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/scripts/loop_tick.py" resolve "$LOOPDIR" \
    --step <STEP_NAME> \
    --result <ok|fail|partial|skip> \
    --plan-nonce "$PLAN_NONCE" \
    --metric queued_added=<n> \
    --metric apify_calls=<n> \
    --metric apollo_calls=<n> \
    --metric pending_after=<n> \
    --metric calendar_block_id=<id> \
    --metric calendar_block_utc=<iso> \
    --metric budget_usd_spent=<usd> \
    [--rows-written "Name1,Name2,Name3"] \
    [--fingerprint-refreshed]
```

Required metric keys depend on the step:

- **REFRESH_FINGERPRINT** → `--fingerprint-refreshed` flag.
- **DISCOVER_***  → `queued_added`, `apollo_calls` or `openalex_calls`.
- **HARVEST_CITATIONS** → none required; `budget_usd_spent` recommended.
- **STAGE_DRAFTS** → `--rows-written`, `pending_after`, `apify_calls`, `budget_usd_spent`.
- **BOOK_CALENDAR** → `calendar_block_id` (REQUIRED — check #6 verifies this is present when BOOK_CALENDAR ran), `calendar_block_utc` recommended.

The resolve call runs `loop_verify.py` automatically and writes `last_verifier.json` + `tick-<utc>.log`. The exit code propagates back:

- **`0`** → continue. Next cron fire will plan again.
- **`10`** → goal met. Loop has stopped itself. Stop here. The user is expected to act.
- **`20`** → hard stop (verifier check #4 violation, retry budget exhausted, etc.). Stop and surface `halt_reason` to the user.
- **`30`** → transient failure. Cron retries on next fire.
- **`40`** → quota backoff. Cron retries on next fire.

## STEP 4 — Report (concise)

One-line summary:

```
synergy-loop-tick <project>: <STEP> <result> (verifier <ok|fail>) — exit=<n>
```

Plus, if exit was 10 or 20, a second line telling the user what to do next:

- exit 10 → "Batch ready + calendar booked. Open the block and run /synergy-run."
- exit 20 → "Loop halted: <halt_reason>. Run /synergy-loop-status <project> for details."

## Guardrails (non-negotiable)

- Never post, like, comment, or connect autonomously.
- Never write to columns `Liked? (G)`, `Commented? (H)`, `Connect Sent? (I)`, `LinkedIn Post URL Used (L)` — those belong to the human send half.
- Never flip Status to `Engaged` or `Pending accept`.
- Always pass the metric the just-run step needs (especially `calendar_block_id` after BOOK_CALENDAR — check #6 will fail otherwise).
- Always pass `--plan-nonce` on resolve. Always mint and consume tracker/calendar nonces around the side effects. Skipping this means the chain stays open; the next tick will overwrite it (recorded as `chain_overwritten` in the audit log) and the audit roll-up will flag the gap.
- If a step fails three ticks in a row with the same step name, the bounds gate will halt the loop. Do not try to work around this; investigate the underlying failure.
