# finance

Financial modeling, budgeting and forecasting, unit economics, and financial decision support.

The finance department from [headcount](https://github.com/cbrock84/headcount), as a plugin in this marketplace, with a department agent added.

## Agent

`agents/finance.md` is a department agent Claude can hand work to. It loads `finance:chief-financial-officer` first, then the specialist skill the request needs, stays inside the department's remit, and returns its answer, the skills it loaded, its sources and its open questions.

## Skills

- `finance:budgeting-and-forecasting`
- `finance:capital-allocation`
- `finance:capital-structure-and-covenants`
- `finance:chief-financial-officer`
- `finance:cost-accounting`
- `finance:financial-modeling`
- `finance:financial-reporting-and-close`
- `finance:financial-statement-analysis`
- `finance:internal-controls-and-audit`
- `finance:revenue-recognition`
- `finance:tax`
- `finance:treasury-and-liquidity`
- `finance:unit-economics`

## Source and license

Copied from [cbrock84/headcount](https://github.com/cbrock84/headcount) at commit `98d1c17`, `plugins/finance/skills/`, under the MIT license (Copyright (c) 2026 Chris Brock; the full text is in `LICENSE`). The skills and their `references/sources.md` files are copied as they are, except for the edits listed below. There are two kinds. A reference to a headcount department this marketplace doesn't carry was a skill address, and it's now plain words naming the function, because the address would point at nothing here. A frontmatter `description` with an unquoted colon in it is now in double quotes, with not a word changed, because YAML read the colon as a nested key.

Edits:

- `skills/chief-financial-officer/SKILL.md`: the frontmatter `description` became "the same text in double quotes, because an unquoted colon broke the YAML"
- `skills/internal-controls-and-audit/SKILL.md`: `legal-risk:corporate-governance` became "corporate governance (legal and risk)"
- `skills/internal-controls-and-audit/SKILL.md`: `legal-risk:enterprise-risk` became "enterprise risk (legal and risk)"
- `skills/revenue-recognition/SKILL.md`: `revenue:chief-revenue-officer` became "the chief revenue officer"
- `skills/revenue-recognition/SKILL.md`: `revenue:pricing-and-packaging` became "pricing and packaging (revenue)"
- `skills/revenue-recognition/SKILL.md`: `legal-risk:contract-review` became "contract review (legal and risk)"
- `skills/tax/SKILL.md`: `revenue:pricing-and-packaging` became "pricing and packaging (revenue)"

Not copied: headcount's ChatGPT and Codex manifest (`.codex-plugin/`), its build scripts, verticals and org chart. The agent, this README and `plugin.json` are MoxyWolf's.

## Checks

CI loads every skill here with the catalog check: `run_all_tests.py` runs `plugins/gstack-execution/scripts/test_skill_packaging.py`, which points `skill_packaging.py` at the whole repository and fails on any SKILL.md a loader can't read.

## Version history

- 0.1.0 (2026-10-06): imported from headcount at `98d1c17`, with the department agent.
