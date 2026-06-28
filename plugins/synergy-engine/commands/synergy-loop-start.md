---
description: Stand up a bounded prep loop for one project. Initializes loop state, runs the first plan tick, and reports the next step. Never posts.
argument-hint: "<project-slug> --owner '<name>' --budget <usd> [--window 1-3pm PT] [--daily-cap 5]"
allowed-tools: [Read, Bash, AskUserQuestion, mcp__scheduled-tasks__create_scheduled_task]
---

# /synergy-engine:synergy-loop-start — bootstrap a bounded prep loop

Replaces `/synergy-schedule` for the loop-engineering model. Where `/synergy-schedule` only registered a cron, this command **initializes a durable loop state**, runs the **first plan tick**, and (optionally) registers the recurring cron that fires `/synergy-loop-tick` on cadence. The loop drives the prep half of the synergy cycle — fingerprint, discover, cite-harvest, stage drafts, book calendar — and stops itself when (a) the batch is ready and the calendar block is booked, (b) a hard stop fires, or (c) the budget runs out.

It **never posts**. The send half (`/synergy-run`, `/synergy-cite-run`, `/synergy-cite-accept-check`) stays human-gated, per the plugin's cadence-and-guardrails.

## STEP 1 — Parameters

From the argument or AskUserQuestion, collect:

- **Project slug** (required): e.g. `aiscrapesafe`. Used to scope state under `plugins/synergy-engine/.loop-state/<project>/`.
- **`--owner '<name>'`** (required): the **Release Owner** — the single named human accountable for everything this loop produces, per §4-5 of the Governed Autonomy paper. This name is baked into `state.json` and surfaced on every audit report. There is no default; refuse to proceed without it.
- **`--budget <usd>`** (required): hard-cap budget for the loop. The bounds gate halts the loop the moment `budget_usd_remaining <= 0`. There is **no default** — you must pass one.
- **`--window`** (optional, default `1-3pm PT`): calendar window for the review block.
- **`--daily-cap`** (optional, default `5`): max drafts the loop may stage per UTC day.
- **`--cadence`** (optional, default `0 */6 * * *` = every 6 hours UTC): cron for the recurring `/synergy-loop-tick` task. Skip with `--no-cron` to run ticks manually.

Confirm the tracker path from `synergy-engine-config.md`. If the project has never been initialized, route to `/synergy-init` first.

## STEP 2 — Bootstrap loop state

Create the loop state directory and initialize `state.json` atomically:

```bash
LOOPDIR="$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/.loop-state/<project>"
mkdir -p "$LOOPDIR"

python3 -B - <<'PY'
import sys
sys.path.insert(0, "$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/scripts")
from pathlib import Path
import loop_state as ls

bounds = ls.BoundsBlock(
    budget_usd_remaining=<budget>,
    daily_cap_drafts=<daily-cap>,
)
s = ls.init(
    loop_state_dir=Path("$LOOPDIR"),
    project="<project>",
    tracker_path="<tracker-path>",
    release_owner="<owner>",
    bounds=bounds,
)
print("state initialized:", s.project, "owner=" + s.release_owner, "budget=$" + str(s.bounds.budget_usd_remaining))
PY
```

Refuse to proceed if `state.json` already exists for this project — direct the user to `/synergy-loop-status` and (if they want a fresh start) to delete the directory manually. Never clobber existing state.

## STEP 3 — Run the first plan tick

Fire one `plan` tick so the agent sees `next_step.json` immediately and any bootstrap drift fails fast:

```bash
python3 -B "$CLAUDE_PLUGIN_ROOT/plugins/synergy-engine/scripts/loop_tick.py" plan "$LOOPDIR"
```

Echo the plan JSON to the user (step, reason, slash_command). Common first-plan outcomes:

- **`BOOK_CALENDAR`** if the tracker already has `Ready for review` drafts (likely for a project mid-flight).
- **`REFRESH_FINGERPRINT`** if the topic fingerprint hash is stale.
- **`DISCOVER_AUTHOR` / `DISCOVER_CONTENT`** if the queue is empty and the daily cap allows.
- **`IDLE`** with `exit_code=20` if a hard stop or budget exhaustion fired (rare on a fresh init unless budget was set near zero).

## STEP 4 — Register the recurring tick (unless --no-cron)

`mcp__scheduled-tasks__create_scheduled_task` with the cadence cron. The prompt must be fully self-contained for a fresh session:

> Run one synergy-engine loop tick for project `<project>`. Read `state.json` at `plugins/synergy-engine/.loop-state/<project>/`. Call `python3 -B scripts/loop_tick.py plan <loopdir>` and then execute the slash command in `next_step.json`. After the action completes, call `loop_tick.py resolve <loopdir> --step <S> --result <ok|fail|partial|skip> --metric KEY=VAL ...`. Exit on exit_code 10 (goal met), 20 (hard stop), or 40 (quota backoff). Never post, like, comment, or connect autonomously. The loop only does the prep half.

## STEP 5 — Report

Print:

```
Synergy loop started — project <project>

State dir:      plugins/synergy-engine/.loop-state/<project>/
Release Owner:  <owner>
Budget:         $<n> remaining
Daily cap:      <n> drafts/day
Cadence:        every <hours>h (next tick: <utc>)
First plan:     <STEP> — <reason>

Next steps:
  - The cron will fire /synergy-loop-tick automatically.
  - Watch progress: /synergy-loop-status <project>
  - Pre-approve tools by clicking "Run now" once on the scheduled task.
```

Note: drafts staged by the loop appear in the tracker as `Ready for review`. The loop will book a Google Calendar block once enough are staged. **You** open the block and run `/synergy-run` (or `/synergy-cite-run`) to actually send. The loop never sends.
