# Goals

Each goal is a folder, `goals/<id>/`, approved by Dorian in one pull request (DESIGN.md, eleventh objective, GO-001).

- `GOAL.md`, the goal brief. Its sections: Serves (the DESIGN.md objective it works under), Outcome, Non-goals, Scenarios, Goal tests, Allowed paths, Spend cap, Provider budgets, Max calls, Max items, Max review rounds per item, Stop conditions, Pre-mortem.
- `PLAN.md`, the items in run order, each with its own acceptance criteria.
- `tests/`, the goal tests, written by a model other than the builder.
- `holdout.sha256`, the hash of the holdout, which never lives in the repository.

Formats `goal_brief.py check` enforces:

- Serves: exactly one `##` objective heading from `main`'s DESIGN.md.
- Scenarios: `- ` bullets, at least one "Given …, then …" line and one "… must never happen" line.
- Goal tests: `- tests/<file>.py::<Class>.<method> (outcome)` or `(invariant)`, one per line, each naming a unittest method that exists. Each test file starts with `# drafted-by: <family>/<model>` (one family for all), and each test's docstring has a `Scenario:` line copied from the brief. A goal test never imports the candidate: it runs it as a separate program from the checkout in the `GOAL_CANDIDATE` environment variable (for example `subprocess.run([sys.executable, "-m", "tool"], cwd=os.environ["GOAL_CANDIDATE"])`) and checks what it does. A test file that needs the repository to load is refused, and a test that loads candidate code into its own interpreter doesn't run. `goal_brief.py baseline goals/<id>` runs them against `origin/main`: outcome tests must fail there, invariant tests must pass.
- The goal pull request's description has a `## Plain-English reading` section covering every goal test and a `Read by: <family>/<model>` line, from a family other than the drafter's.
- Allowed paths: `- ` bullets of globs. `*` stays inside one folder; `**` spans folders, so it can always reach a protected `hooks/` folder and is refused. No glob may reach a `CODEOWNERS` path, even one that doesn't exist yet.
- Spend cap: `$5` or `5.00`. Provider budgets: `- <provider>: $<amount>`, each positive, summing to no more than the cap. Max items 1 to 10, Max review rounds per item 1 to 3, Max calls a whole number. No other notation.
- PLAN.md: an optional `# ` title, then `1. <item>` lines at column 0, each followed by at least one indented `- <acceptance criterion>`. Any other line is refused.
- holdout.sha256: one 64-character lowercase hex SHA-256.

The check reads DESIGN.md and CODEOWNERS from `origin/main`, never the working tree, and refuses to run if it can't.

An approved goal never changes. `goal_brief.py verify` accepts only the approval of the pull request that adds `goals/<id>/`, so a changed goal is a new folder (for example `<id>-2`) with its own approval.

A brief only narrows the project charter. `plugins/gstack-execution/scripts/goal_brief.py check goals/<id>` refuses one that doesn't. This folder is a `CODEOWNERS` path, so nothing here changes without Dorian's approving review.
