---
description: Run an approved goal (GO-003) — the plan's items in order onto goal/<id>, each through /gstack-build, stopping on a regression, HALT, a changed goal, spend at 80% or an exhausted plan
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: <goal-id> --pr <number of the PR that added the goal> [--builder <family>/<model>]
---

A goal is a brief Dorian approved (`goals/<id>/`, GO-001). This command runs it. It delegates which item to build next; it never delegates authority: every item still goes through `/gstack-build`'s cross-vendor review, and nothing reaches `main` except through the goal pull request and its gates.

`goal_run.py` holds the run's state. It reads `main`, CODEOWNERS and the goal folder from the checkout it lives in, so run the copy inside a checkout of the governed repository, from that checkout's root, never the installed plugin's: `python3 plugins/gstack-execution/scripts/agent_token.py exec --goal-run -- python3 plugins/gstack-execution/scripts/goal_run.py ...`. `--goal-run` mints a token with contents and pull_requests only, so nothing in the run can add or change a workflow; the item builds run under it too, with `GSTACK_GOAL_RUN_DIR` set to the vault's goal-runs folder. An installed copy refuses. Every exit but 0 means stop.

1. **Start.** `goal_run.py start <id> --pr <N> --builder <family>/<model>`. It verifies the approval, refuses a builder whose family drafted or read the goal tests, refuses a token that reaches secrets, and opens `goal/<id>` from `main`. A refusal ends the command: report it to Dorian as written.
2. **Loop.** `git fetch origin main`, then `goal_run.py next <id>`.
   - `{"step": "build", "item": ...}`: export `GSTACK_GOAL_LEDGER` as the printed `ledger`, then build that item with `/gstack-build`, its branch made from the printed `branch_from` (the goal branch's fetched head, so it carries every item merged before it) and its pull request targeting the printed `base_branch`, the item's criteria as the acceptance criteria and `--max-rounds` no more than the printed `max_rounds`. When it merges, run `goal_run.py merged <id> --item <n> --head <goal/<id> head after the merge>` and loop. When the build ends any other way (`rounds_exhausted`, `review_unavailable` or another non-pass outcome), run `goal_run.py failed <id> --item <n> --reason "<the outcome and its escalation>"`: the run stops there, and `goal_run.py record <id>` gives the record to report.
   - `{"step": "finish"}`: every goal test passes. Finish:
     1. `goal_run.py finalize <id>` commits the run record alone and opens its pull request into `goal/<id>`. When `goal-envelope` is green, merge it as the bot (it changes only `goal-runs/<id>/RESULT.md`).
     2. `goal_run.py propose <id>` opens the goal pull request from `goal/<id>` into `main`.
     3. Run `/gstack-peer-review` on that pull request's whole diff (a fresh cross-vendor review, coverage `checked`). `goal-envelope`, `goal-tests`, `goal-holdout` and `tests` must be green, and Dorian approves at the head; GitHub enforces all of it.
     4. If `goal-holdout` fails, run `goal_run.py stop <id> --reason "goal-holdout failed: possible reward hack"` and report it to Dorian. Don't touch the holdout or the tests.
   - exit 1: the run has ended, `stopped` or `exhausted`, with its reason. Stop and report it to Dorian.
3. **After the goal pull request merges into `main`:** `goal_run.py complete <id> --pr <its number> --merge <merge sha>`. It records `complete` only when GitHub shows that pull request from `goal/<id>` merged into `main` as that commit, at the head whose goal tests passed. Then `goal_run.py record <id>` for the run record.

Never edit `goals/<id>/`, the state folder or the ledger by hand. A changed goal is a new goal, approved again.
