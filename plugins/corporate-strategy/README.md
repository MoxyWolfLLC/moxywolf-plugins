# corporate-strategy

Portfolio strategy, corporate development, strategic alliances, and scenario planning.

The corporate strategy department from [headcount](https://github.com/cbrock84/headcount), as a plugin in this marketplace, with a department agent added.

## Agent

`agents/corporate-strategy.md` is a department agent Claude can hand work to. It loads `corporate-strategy:chief-strategy-officer` first, then the specialist skill the request needs, stays inside the department's remit, and returns its answer, the skills it loaded, its sources and its open questions.

## Skills

- `corporate-strategy:chief-strategy-officer`
- `corporate-strategy:market-entry`
- `corporate-strategy:mergers-and-acquisitions`
- `corporate-strategy:portfolio-strategy`
- `corporate-strategy:scenario-planning`
- `corporate-strategy:strategic-alliances`

## Source and license

Copied from [cbrock84/headcount](https://github.com/cbrock84/headcount) at commit `98d1c17`, `plugins/corporate-strategy/skills/`, under the MIT license (Copyright (c) 2026 Chris Brock; the full text is in `LICENSE`). The skills and their `references/sources.md` files are copied as they are, except for the edits listed below. There are two kinds. A reference to a headcount department this marketplace doesn't carry was a skill address, and it's now plain words naming the function, because the address would point at nothing here. A frontmatter `description` with an unquoted colon in it is now in double quotes, with not a word changed, because YAML read the colon as a nested key.

Edits:

- `skills/chief-strategy-officer/SKILL.md`: `executive:chief-executive` became "the chief executive"
- `skills/strategic-alliances/SKILL.md`: `marketing:partnership-marketing` became "partnership marketing (marketing)"

Not copied: headcount's ChatGPT and Codex manifest (`.codex-plugin/`), its build scripts, verticals and org chart. The agent, this README and `plugin.json` are MoxyWolf's.

## Checks

CI loads every skill here with the catalog check: `run_all_tests.py` runs `plugins/gstack-execution/scripts/test_skill_packaging.py`, which points `skill_packaging.py` at the whole repository and fails on any SKILL.md a loader can't read.

## Version history

- 0.1.0 (2026-10-06): imported from headcount at `98d1c17`, with the department agent.
