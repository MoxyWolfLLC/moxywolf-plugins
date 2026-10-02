# Goals

Each goal is a folder, `goals/<id>/`, approved by Dorian in one pull request (DESIGN.md, eleventh objective, GO-001).

- `GOAL.md`, the goal brief. Its sections: Serves (the DESIGN.md objective it works under), Outcome, Non-goals, Scenarios, Goal tests, Allowed paths, Spend cap, Provider budgets, Max calls, Max items, Max review rounds per item, Stop conditions, Pre-mortem.
- `PLAN.md`, the items in run order, each with its own acceptance criteria.
- `tests/`, the goal tests, written by a model other than the builder.
- `holdout.sha256`, the hash of the holdout, which never lives in the repository.

Formats `goal_brief.py check` enforces:

- Serves: exactly one `##` objective heading from `main`'s DESIGN.md.
- Scenarios: `- ` bullets, at least one "Given …, then …" line and one "… must never happen" line.
- Goal tests: `- <test id> (outcome)` or `- <test id> (invariant)`, one per line.
- Allowed paths: `- ` bullets of globs. `*` stays inside one folder; `**` spans folders, so it can always reach a protected `hooks/` folder and is refused. No glob may reach a `CODEOWNERS` path, even one that doesn't exist yet.
- Spend cap: `$5` or `5.00`. Provider budgets: `- <provider>: $<amount>`, each positive, summing to no more than the cap. Max items 1 to 10, Max review rounds per item 1 to 3, Max calls a whole number. No other notation.
- PLAN.md: `1. <item>` lines, each followed by at least one indented `- <acceptance criterion>`.
- holdout.sha256: one 64-character lowercase hex SHA-256.

The check reads DESIGN.md and CODEOWNERS from `origin/main`, never the working tree, and refuses to run if it can't.

A brief only narrows the project charter. `plugins/gstack-execution/scripts/goal_brief.py check goals/<id>` refuses one that doesn't. This folder is a `CODEOWNERS` path, so nothing here changes without Dorian's approving review.
