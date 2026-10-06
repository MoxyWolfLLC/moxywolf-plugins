# people

Org design, hiring and interviewing, compensation and leveling, and workforce planning.

The people department from [headcount](https://github.com/cbrock84/headcount), as a plugin in this marketplace, with a department agent added.

## Agent

`agents/people.md` is a department agent Claude can hand work to. It loads `people:chief-human-resources-officer` first, then the specialist skill the request needs, stays inside the department's remit, and returns its answer, the skills it loaded, its sources and its open questions.

## Skills

- `people:benefits-and-leave`
- `people:chief-human-resources-officer`
- `people:compensation-and-leveling`
- `people:employee-relations`
- `people:employment-compliance`
- `people:hiring-and-interviewing`
- `people:learning-and-development`
- `people:onboarding-and-offboarding`
- `people:org-design`
- `people:payroll-operations`
- `people:performance-management`
- `people:workforce-planning`

## Source and license

Copied from [cbrock84/headcount](https://github.com/cbrock84/headcount) at commit `98d1c17`, `plugins/people/skills/`, under the MIT license (Copyright (c) 2026 Chris Brock; the full text is in `LICENSE`). The skills and their `references/sources.md` files are copied as they are, except for the edits listed below. There are two kinds. A reference to a headcount department this marketplace doesn't carry was a skill address, and it's now plain words naming the function, because the address would point at nothing here. A frontmatter `description` with an unquoted colon in it is now in double quotes, with not a word changed, because YAML read the colon as a nested key.

Edits:

- `skills/chief-human-resources-officer/SKILL.md`: the frontmatter `description` became "the same text in double quotes, because an unquoted colon broke the YAML"

Not copied: headcount's ChatGPT and Codex manifest (`.codex-plugin/`), its build scripts, verticals and org chart. The agent, this README and `plugin.json` are MoxyWolf's.

## Version history

- 0.1.0 (2026-10-06): imported from headcount at `98d1c17`, with the department agent.
