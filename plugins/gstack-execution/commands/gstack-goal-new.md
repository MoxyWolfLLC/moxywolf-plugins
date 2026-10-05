---
description: Draft a goal (GO-007) — brief and plan by the agent, goal tests and holdout by another model family, the plain-English reading by a third — and open the one pull request Dorian approves before /gstack-goal can run it
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
argument-hint: <goal-id> "<the outcome, in Dorian's words>"
---

A goal is `goals/<id>/`: `GOAL.md`, `PLAN.md`, `tests/` and `holdout.sha256` (GO-001). `goals/README.md` holds every format `goal_brief.py check` enforces. Read it before drafting. This command drafts the folder and opens its pull request. It never approves, never merges and never starts a run.

The goal id is lowercase words joined by hyphens. An approved goal never changes, so a changed goal is a new id (`<id>-2`).

Work in a checkout of the governed repository, on a branch `build/goal-<id>` made from `origin/main`, and run the scripts from that checkout: `python3 plugins/gstack-execution/scripts/<script> ...`. Every exit but 0 means stop and fix what it names.

1. **The outcome.** Agree it with Dorian in one exchange: what's true when the goal is done, and what it must never do. Pick the one DESIGN.md objective it serves. If it needs the charter loosened, stop. That's a DESIGN.md amendment for him, not a goal (GO-001.5).
2. **Brief and plan.** Write `GOAL.md` and `PLAN.md` yourself in the README's formats.
   - **Scenarios and Goal tests.** Each goal test has its own Scenario. At least one test is an `outcome` test and one an `invariant`.
   - **Allowed paths.** These are the files the items change, plus the touched plugins' `plugin.json` and `.claude-plugin/marketplace.json`. Never a `CODEOWNERS` path.
   - **Stop conditions.** Include "the marketplace's top-level version moves on the goal branch" (GO-004.1).
   - **Pre-mortem.** List the ways the tests could pass while the goal fails. The holdout is drafted against them.
   - **Plan items.** Each item's criteria say which output stream each message goes to and every exit code.
3. **Goal tests.** `goal_new.py tests goals/<id>` asks the gpt family (Codex, read-only) for exactly the tests the brief names and writes them with its `drafted-by` line. Never edit a drafted test by hand: that makes you a co-drafter. If one is wrong, fix the brief or plan and run `tests` again.
4. **Holdout.** `goal_new.py holdout goals/<id>` asks the same family for the holdout. It writes the file to `~/.goal-holdouts/<id>.py` (mode 600, outside every repository), writes only its hash to `holdout.sha256`, and prints the file path, the secret name `GOAL_<ID>_HOLDOUT` and the environment `goal-holdout`. Never open, print or copy the holdout file.
5. **Check.** `goal_brief.py check goals/<id>`, then `goal_brief.py baseline goals/<id>`. Outcome tests must fail on `main` and invariant tests must pass. A test on the wrong side means the brief or plan was unclear: fix it and redo steps 3 and 4.
6. **Reading.** `goal_new.py read goals/<id>` asks the gemini family for the plain-English reading of every goal test. It prints the `## Plain-English reading` section with its `Read by:` line. The builder of the run will be neither family (GO-003.3), so it builds as `claude`.
7. **Pull request.** Commit `goals/<id>/` alone, push as the bot (`agent_token.py exec -- git push`), and open the pull request into `main` titled `Goal: <outcome in a few words> (<id>)`.
   - **The body.** The outcome, the plan's items in one line each, the spend cap, and the reading from step 6 as printed.
   - **What to tell Dorian, in one message:**
     - the pull request link;
     - that it needs his approving review;
     - that the holdout goes into the `goal-holdout` environment's secret `GOAL_<ID>_HOLDOUT` from the file `holdout` printed, at `https://github.com/<owner>/<repo>/settings/environments`. GitHub won't let the bot set it.
8. **After he says the secret is in:** delete the local holdout file (`rm ~/.goal-holdouts/<id>.py`). No run starts while it exists. Merge the goal pull request on his instruction, pinned to the approved head. Then `/gstack-goal <id> --pr <N>`.

Goals come from the open work under each objective, the session handoff and the project's Jira label. Drafting one asks Dorian nothing beyond step 1 and the approval in step 7.
