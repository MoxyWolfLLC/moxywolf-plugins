---
title: Mistake ledger — Moxywolf Plugins
type: mistake-ledger
item: SM-003
note: Written by /session-end Step 3.6 and validated by project-init/scripts/mistake_ledger.py. Each row became a check, a rule at the point of action, or a one-off. A repeat escalates.
---

# Mistake ledger — Moxywolf Plugins

| id | date | what | caught_by | evidence | disposition | target | repeats |
|---|---|---|---|---|---|---|---|
| M-001 | 2026-09-24 | A review packet named its CI run's repo as `/tmp/xe019`; the repository resolved to `/private/tmp/xe019`, so the dispatcher read no CI evidence. The resolution was already recorded in project memory and PR #42. | reviewer | review 20260924-162903-25a6677-7hrcgdnp | became_check | XE-020 | |
| M-002 | 2026-09-24 | The health report called `CHARTER.md` and `PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md` stale from their commit dates; both are `status: active` and cited by 35 `GOVERNANCE.md` files. | self | git grep before the archive move, 2026-09-24 | became_rule | plugins/github-repo-analyzer/skills/github-repo-analyzer/SKILL.md | |
| M-003 | 2026-09-24 | The secret scan's generic patterns missed a plaintext Composio `ak_` key in the archived May handoff, public since `0bea07b`. | reviewer | review 20260924-163251-860613c-9aou_1nn F1 | became_rule | plugins/github-repo-analyzer/skills/github-repo-analyzer/SKILL.md | |
