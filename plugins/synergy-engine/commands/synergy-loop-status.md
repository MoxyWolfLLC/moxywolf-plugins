---
description: Show the synergy loop's live state — last tick, verifier result, budget remaining, drafts ready, and what the next tick will do.
argument-hint: "<project-slug>"
allowed-tools: [Read, Bash]
---

# /synergy-engine:synergy-loop-status — print the loop's heartbeat

Read the loop state for `<project-slug>` and print a one-screen status. Complements (does not replace) `/synergy-status`, which reads the tracker. This one reads the **loop's own state**: what it decided, what it did, what bounds it has left, and what's next.

If no `state.json` exists, route to `/synergy-loop-start`.

## STEP 1 — Locate state

```bash
LOOPDIR="$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/.loop-state/<project>"
test -f "$LOOPDIR/state.json" || { echo "No loop state for <project>. Run /synergy-loop-start <project> --budget <n>."; exit 0; }
```

## STEP 2 — Read state + last verifier + last tick

```bash
python3 -B - <<'PY'
import sys, json
sys.path.insert(0, "$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/scripts")
from pathlib import Path
import loop_state as ls

loopdir = Path("$LOOPDIR")
s = ls.load(loopdir)

# Last verifier report (loop_verify writes last_verifier.json every run)
lv = loopdir / "last_verifier.json"
verifier = json.loads(lv.read_text()) if lv.exists() else None

# Most recent tick log
tick_logs = sorted(loopdir.glob("tick-*.log"))
last_tick = tick_logs[-1].name if tick_logs else None

# Next step the agent should run
ns = loopdir / "next_step.json"
next_step = json.loads(ns.read_text()) if ns.exists() else None

out = {
    "project": s.project,
    "ticks_total": s.ticks_total,
    "halt_reason": s.halt_reason,
    "budget_remaining": s.bounds.budget_usd_remaining,
    "drafts_today": s.bounds.drafts_staged_today,
    "daily_cap": s.bounds.daily_cap_drafts,
    "drafts_ready_for_review": s.drafts_ready_for_review,
    "fingerprint_hash": s.fingerprint_hash[:12] if s.fingerprint_hash else None,
    "last_tick_utc": s.last_tick_utc,
    "last_tick_log": last_tick,
    "verifier_ok": verifier.get("ok") if verifier else None,
    "verifier_failures": [c["name"] for c in (verifier or {}).get("checks", []) if not c.get("ok")],
    "next_step": next_step,
}
print(json.dumps(out, indent=2, sort_keys=True))
PY
```

## STEP 3 — Format for the user

Render the JSON as a readable block:

```
Synergy loop — <project>

Ticks total:    <n>          Last tick:  <utc> (<delta> ago)
Budget left:    $<n>          Daily cap:  <staged>/<cap> drafts today
Fingerprint:    <hash12>      Drafts ready for review: <n>

Verifier (last run): <PASS | FAIL — checks: <list>>
Halt reason:    <none | hard stop: ...>

Next step (from next_step.json):
  Step:         <STEP_NAME>
  Reason:       <...>
  Slash:        <slash_command>

Recent ticks:
  <utc>  <STEP>  <result>  exit=<n>  (verifier <ok|fail>)
  <utc>  <STEP>  <result>  exit=<n>  (verifier <ok|fail>)
  <utc>  <STEP>  <result>  exit=<n>  (verifier <ok|fail>)
```

For "recent ticks", read the last 3 `tick-*.log` files and pull `step / result / exit_code / verifier_ok` from each.

## STEP 4 — Suggest action based on state

After the block, print one of these:

- **`halt_reason` is set** → "Loop is halted. Inspect `last_verifier.json` and the most recent tick log. Resume with `/synergy-loop-start <project> --budget <n>` once you've addressed the cause."
- **`verifier_ok = false`** → "Last verifier run failed. Check `last_verifier.json` for the failing check. The loop will keep retrying transient failures; hard stops require manual unblock."
- **`drafts_ready_for_review >= 5` and no calendar block in state** → "Batch is ready. Next tick should book the calendar block. If it doesn't, force it: `python3 scripts/loop_tick.py plan <loopdir>`."
- **`next_step.step == IDLE` and `exit_code == 10`** → "Goal met. The loop completed its bounded objective for this batch. Run `/synergy-loop-start` again to start the next batch, or `/synergy-run` to send the staged drafts."
- **Otherwise** → "Loop is healthy. Next scheduled tick will run automatically."

## Notes

- This command is **read-only**. It never advances the loop. To force a plan, call `loop_tick.py plan` directly.
- For the underlying tracker state (engaged / queued / due by topic), use `/synergy-status` instead.
- All times in state are UTC. Convert to local for display if helpful.
