# Goals

Each goal is a folder, `goals/<id>/`, approved by Dorian in one pull request (DESIGN.md, eleventh objective, GO-001).

- `GOAL.md`, the goal brief. Its sections: Serves (the DESIGN.md objective it works under), Outcome, Non-goals, Scenarios, Goal tests, Allowed paths, Spend cap, Provider budgets, Max calls, Max items, Max review rounds per item, Stop conditions, Pre-mortem.
- `PLAN.md`, the items in run order, each with its own acceptance criteria.
- `tests/`, the goal tests, written by a model other than the builder.
- `holdout.sha256`, the hash of the holdout, which never lives in the repository.

A brief only narrows the project charter. `plugins/gstack-execution/scripts/goal_brief.py check goals/<id>` refuses one that doesn't. This folder is a `CODEOWNERS` path, so nothing here changes without Dorian's approving review.
