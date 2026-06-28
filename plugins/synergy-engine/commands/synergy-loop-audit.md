---
description: Read-only audit of a synergy prep loop — engineering health + governance health side by side. Surfaces override rate and chain-of-custody anomalies.
argument-hint: "<project-slug> [--json]"
allowed-tools: [Read, Bash]
---

# /synergy-engine:synergy-loop-audit — read both halves of the report

This is the third leg of the Governed Autonomy stool, alongside `/synergy-loop-start` (which declares the Release Owner) and the per-tick nonce chain (which makes a fake passing review detectable). The audit roll-up is the mirror that lets the Release Owner check whether the system is actually being governed — or whether it's just running.

It is **read-only**. It never mutates state, never opens a chain, never writes to the tracker. Safe to run anywhere, any time, as often as you want.

## What it shows

Two sections, both required, both surfaced together:

### Engineering health (was the loop machinery exercised?)

- `ticks_total` — number of resolved ticks recorded
- `verifier_hard_stops` and rate — how often the seven deterministic checks tripped
- `transient_retries` — how often a tick soft-failed and was retried
- `halt_fires` and rate — any cause of hard stop, ever
- `current_halt_reason` — whether the loop is halted right now
- `mid_loop_interventions` — chain audit events that signal something went sideways mid-tick (mismatch, replay, missing, overwritten chain)
- `chain_consume_failures` — strict subset above; the smoke gun for "someone tried to close a chain without doing the work." Non-zero is suspicious. Always.

### Governance health (was the human actually overriding?)

- `batches_sent` — rows the human moved past Ready for review into Posted / Pending Accept / Accepted / Engaged
- `batches_staged` — rows still sitting at Ready for review (the queue waiting for the human)
- `batches_killed` — rows the human moved to Parked or Cold
- `sent_as_staged_ratio` — of everything the human decided on, what fraction went out. **High = rubber-stamp risk.** The paper (§10) explicitly refuses to set a threshold here; the Release Owner sets the line.
- `kill_ratio` — fraction killed
- `mean_response_minutes_to_first_send` — from the last calendar block to the earliest Posted timestamp. A very short response combined with a very high `sent_as_staged_ratio` is the worst combination: bot-reflex sending of a human-stamped queue.

## STEP 1 — Run the audit

```bash
LOOPDIR="$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/.loop-state/<project>"
TRACKER=$(grep -E '^tracker_path' "$LOOPDIR/state.json" | head -1 | sed 's/.*"tracker_path": *"\([^"]*\)".*/\1/')
python3 -B "$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/scripts/loop_audit.py" \
    "$LOOPDIR" "$TRACKER"
```

Pass `--json` if you want the raw structure (e.g. for a downstream dashboard or for piping into `jq`).

## STEP 2 — Read both halves together

The paper is explicit (§§10–11): you cannot judge governance health from engineering metrics alone, and you cannot judge engineering health from governance metrics alone. The two must be read side by side.

The four corners:

| engineering OK | governance OK | reading |
|---|---|---|
| yes | yes | loop is doing what it claims; reviewer is doing what they claim |
| yes | no | the loop is running fine, the human is rubber-stamping (or absent) |
| no | yes | the human is overriding actively, the loop is broken (verifier tripping, chain anomalies) |
| no | no | both halves are degraded — stop the loop, do not "fix" by adjusting thresholds |

If `chain_consume_failures > 0`, investigate **before** trusting any other number from that period. That signal means at least one resolve was attempted with a wrong/replayed nonce, which means either (a) a race condition you need to track down, or (b) something actively tried to skip the verifier.

## STEP 3 — Report

Echo the formatted text output to the user verbatim. Do not summarize or editorialize the numbers — the design intentionally surfaces raw ratios without a verdict. The Release Owner judges the verdict.

If `current_halt_reason` is non-empty, append a one-liner pointing them at `/synergy-loop-status <project>` for the full halt context.

## Guardrails

- This command never writes to `state.json`, never appends to `chain-audit.jsonl`, never touches the tracker. If you find yourself wanting to "fix" a number, file an issue against the loop itself instead.
- Do not interpret the `sent_as_staged_ratio` for the user. The paper is deliberate about this — they set the threshold, not the tool.
- The audit reads `tick-*.log` files and `chain-audit.jsonl`. If they're missing, the corresponding metrics show as zero — that itself is a finding (loop has produced no recorded activity).
