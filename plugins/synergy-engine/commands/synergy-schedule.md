---
description: "[DEPRECATED] Use /synergy-loop-start instead. Kept for backward compatibility — redirects."
argument-hint: "[N per run, default 5] [window, e.g. 1-3pm PT]"
allowed-tools: [Read, AskUserQuestion]
---

# /synergy-engine:synergy-schedule — DEPRECATED

> **This command is deprecated.** It set up a cron task that ran the prep half of the synergy cycle but had no durable state, no verifier, no bounds, and no goal-met detection. If a run failed mid-flight, the next cron fire would start over blind. If the scheduled prompt drifted from the tracker schema, nothing caught it.
>
> The replacement is **`/synergy-loop-start`**, which initializes a bounded loop with:
>
> - **Durable state** (`plugins/synergy-engine/.loop-state/<project>/state.json`) — survives crashes, partial runs, and session restarts.
> - **A verifier** (`loop_verify.py`) that runs every tick and checks tracker integrity, schema validity, citation health, the human-gate columns, the quota envelope, the calendar block, and a progress signal.
> - **Hard bounds** — explicit `--budget` (USD cap), daily draft cap, max retries. The loop halts itself when bounds are breached.
> - **Goal-met exit** — the loop stops cleanly when the batch is `Ready for review` AND the calendar block is booked. No infinite ticking.
> - **A status view** (`/synergy-loop-status <project>`) that shows the heartbeat without advancing the loop.

## What to do instead

```text
/synergy-engine:synergy-loop-start <project> --budget 5 --window "1-3pm PT" --daily-cap 5
```

That single command:

1. Bootstraps `state.json` for the project.
2. Runs the first plan tick and writes `next_step.json`.
3. Registers the recurring cron for `/synergy-loop-tick`.

Then monitor with:

```text
/synergy-engine:synergy-loop-status <project>
```

## STEP 1 — Redirect

If a user invokes `/synergy-schedule`, do not run the legacy logic. Instead:

1. Print the deprecation notice above.
2. Ask via AskUserQuestion: "Run `/synergy-loop-start` now with the same parameters?" with options "Yes — start the loop", "No — show me the new docs first".
3. If yes, route to `/synergy-engine:synergy-loop-start <project> --budget <ask-or-default-5> --window <window> --daily-cap <N>`.

## Why this changed

The original `/synergy-schedule` was a thin wrapper over the scheduled-tasks MCP. It worked for the happy path but had no way to recover from drift or partial failure. Loop engineering (verifier + bounds + state + goal exit) is the durable answer. See `references/loop-contract.md` for the column-ownership contract and the seven verifier checks.
