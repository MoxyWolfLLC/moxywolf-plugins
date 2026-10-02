---
description: Run an approved goal (GO-003) — the plan's items in order onto goal/<id>, each through /gstack-build, stopping on a regression, HALT, a changed goal, spend at 80% or an exhausted plan
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: <goal-id> --pr <number of the PR that added the goal> [--builder <family>/<model>]
---

A goal is a brief Dorian approved (`goals/<id>/`, GO-001). This command runs it. It delegates which item to build next; it never delegates authority: every item still goes through `/gstack-build`'s cross-vendor review, and nothing reaches `main` except through the goal pull request and its gates.

`goal_run.py` holds the run's state. Run every command under the bot: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agent_token.py" exec -- python3 "${CLAUDE_PLUGIN_ROOT}/scripts/goal_run.py" ...`, with `GSTACK_GOAL_RUN_DIR` set to the vault's goal-runs folder. Every exit but 0 means stop.

1. **Start.** `goal_run.py start <id> --pr <N> --builder <family>/<model>`. It verifies the approval, refuses a builder whose family drafted or read the goal tests, refuses a token that reaches secrets, and opens `goal/<id>` from `main`. A refusal ends the command: report it to Dorian as written.
2. **Loop.** `git fetch origin main`, then `goal_run.py next <id>`.
   - `{"step": "build", "item": ...}`: export `GSTACK_GOAL_LEDGER` as the printed `ledger`, then build that item with `/gstack-build`, its pull request targeting the printed `base_branch`, the item's criteria as the acceptance criteria and `--max-rounds` no more than the printed `max_rounds`. When it merges, run `goal_run.py merged <id> --head <goal/<id> head after the merge>` and loop.
   - `{"step": "finish"}`: every goal test passes. The finish (holdout, run record, the goal pull request into `main`) is GO-003 criteria 6 and 7.
   - exit 1: the run has ended, `stopped` or `exhausted`, with its reason. Stop and report it to Dorian.
3. **After the goal pull request merges into `main`:** `goal_run.py complete <id> --merge <merge sha>`, then `goal_run.py record <id>` for the run record.

Never edit `goals/<id>/`, the state folder or the ledger by hand. A changed goal is a new goal, approved again.
