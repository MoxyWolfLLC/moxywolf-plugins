# operations

Program management, process design, vendor and supplier management, and operational delivery.

The operations department from [headcount](https://github.com/cbrock84/headcount), as a plugin in this marketplace, with a department agent added.

## Agent

`agents/operations.md` is a department agent Claude can hand work to. It loads `operations:chief-operating-officer` first, then the specialist skill the request needs, stays inside the department's remit, and returns its answer, the skills it loaded, its sources and its open questions.

## Skills

- `operations:business-continuity-and-resilience`
- `operations:capacity-and-demand-planning`
- `operations:chief-operating-officer`
- `operations:facilities-and-workplace`
- `operations:incident-management`
- `operations:operating-cadence`
- `operations:process-design`
- `operations:procurement-and-sourcing`
- `operations:quality-management`
- `operations:service-level-management`
- `operations:supply-chain-and-logistics`
- `operations:vendor-management`

## Source and license

Copied from [cbrock84/headcount](https://github.com/cbrock84/headcount) at commit `98d1c17`, `plugins/operations/skills/`, under the MIT license (Copyright (c) 2026 Chris Brock; the full text is in `LICENSE`). The skills and their `references/sources.md` files are copied as they are, except for the edits listed below. There are two kinds. A reference to a headcount department this marketplace doesn't carry was a skill address, and it's now plain words naming the function, because the address would point at nothing here. A frontmatter `description` with an unquoted colon in it is now in double quotes, with not a word changed, because YAML read the colon as a nested key.

Edits:

- `skills/chief-operating-officer/SKILL.md`: the frontmatter `description` became "the same text in double quotes, because an unquoted colon broke the YAML"
- `skills/facilities-and-workplace/SKILL.md`: `legal-risk:contract-review` became "contract review (legal and risk)"
- `skills/procurement-and-sourcing/SKILL.md`: `legal-risk:contract-review` became "contract review (legal and risk)"
- `skills/procurement-and-sourcing/SKILL.md`: `legal-risk:privacy-and-data-protection` became "privacy and data protection (legal and risk)"
- `skills/service-level-management/SKILL.md`: `legal-risk:contract-review` became "contract review (legal and risk)"

Not copied: headcount's ChatGPT and Codex manifest (`.codex-plugin/`), its build scripts, verticals and org chart. The agent, this README and `plugin.json` are MoxyWolf's.

## Checks

CI loads every skill here with the catalog check: `run_all_tests.py` runs `plugins/gstack-execution/scripts/test_skill_packaging.py`, which points `skill_packaging.py` at the whole repository and fails on any SKILL.md a loader can't read.

## Version history

- 0.1.0 (2026-10-06): imported from headcount at `98d1c17`, with the department agent.
