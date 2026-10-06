# it-operations

Corporate IT: service desk, systems and network administration, virtualization and cloud, telephony and conferencing, endpoints, assets, identity lifecycle, and backup and recovery.

The it operations department from [headcount](https://github.com/cbrock84/headcount), as a plugin in this marketplace, with a department agent added.

## Agent

`agents/it-operations.md` is a department agent Claude can hand work to. It loads `it-operations:chief-information-officer` first, then the specialist skill the request needs, stays inside the department's remit, and returns its answer, the skills it loaded, its sources and its open questions.

## Skills

- `it-operations:backup-and-recovery`
- `it-operations:chief-information-officer`
- `it-operations:cloud-administration`
- `it-operations:collaboration-platform-administration`
- `it-operations:endpoint-management`
- `it-operations:identity-lifecycle-administration`
- `it-operations:it-asset-management`
- `it-operations:network-administration`
- `it-operations:service-desk`
- `it-operations:systems-administration`
- `it-operations:telephony-and-conferencing`
- `it-operations:virtualization-operations`

## Source and license

Copied from [cbrock84/headcount](https://github.com/cbrock84/headcount) at commit `98d1c17`, `plugins/it-operations/skills/`, under the MIT license (Copyright (c) 2026 Chris Brock; the full text is in `LICENSE`). The skills and their `references/sources.md` files are copied as they are, except for the edits listed below. There are two kinds. A reference to a headcount department this marketplace doesn't carry was a skill address, and it's now plain words naming the function, because the address would point at nothing here. A frontmatter `description` with an unquoted colon in it is now in double quotes, with not a word changed, because YAML read the colon as a nested key.

Edits:

- `skills/backup-and-recovery/SKILL.md`: `legal-risk:privacy-and-data-protection` became "privacy and data protection (legal and risk)"
- `skills/chief-information-officer/SKILL.md`: `technology:cloud-infrastructure` became "cloud infrastructure (technology)"
- `skills/cloud-administration/SKILL.md`: `technology:cloud-infrastructure` became "cloud infrastructure (technology)"
- `skills/cloud-administration/SKILL.md`: `legal-risk:privacy-and-data-protection` became "privacy and data protection (legal and risk)"
- `skills/endpoint-management/SKILL.md`: `legal-risk:privacy-and-data-protection` became "privacy and data protection (legal and risk)"
- `skills/systems-administration/SKILL.md`: `technology:cloud-infrastructure` became "cloud infrastructure (technology)"
- `skills/telephony-and-conferencing/SKILL.md`: `legal-risk:privacy-and-data-protection` became "privacy and data protection (legal and risk)"

Not copied: headcount's ChatGPT and Codex manifest (`.codex-plugin/`), its build scripts, verticals and org chart. The agent, this README and `plugin.json` are MoxyWolf's.

## Checks

CI loads every skill here with the catalog check: `run_all_tests.py` runs `plugins/gstack-execution/scripts/test_skill_packaging.py`, which points `skill_packaging.py` at the whole repository and fails on any SKILL.md a loader can't read.

## Version history

- 0.1.0 (2026-10-06): imported from headcount at `98d1c17`, with the department agent.
