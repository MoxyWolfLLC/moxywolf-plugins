# sales-department

Account qualification, opportunity and pipeline analysis, sales preparation and draft outreach. Owns account-specific pursuit.

MoxyWolf's Sales department, as a department agent the Chief of Staff routes to. Design: CS-004 in `DESIGN.md`.

The package is named `sales-department`, not `sales`, so it doesn't shadow the installed `sales:` skills. Those stay where they are, in another marketplace, and this department loads them as its specialists.

## Agent

`agents/sales-department.md` is the department agent. It loads `sales-department:head-of-sales` first, checks the dispatch, loads the installed specialist the request needs, stays inside the remit, and returns nine labelled fields. It analyzes and drafts. It doesn't send, publish, spend, release, delete, change permissions or write to a customer system.

## Skill

- `sales-department:head-of-sales` is the department's operating manual: the remit, the lines with the other departments, specialist routing, the Release Owner Gate, the Security review rule, the evidence rules and the return contract. Its sources are in `skills/head-of-sales/references/sources.md`.

## Specialists it borrows

Named in the head skill, verified in the installed `sales` plugin (Anthropic, 2.0.1) on 2026-10-07, and resolved again at run time:

- `sales:account-research`
- `sales:call-prep`
- `sales:draft-outreach`
- `sales:pipeline-review`
- `sales:forecast`

If one isn't installed in a session, the work that depends on it is blocked and the agent says so. It doesn't substitute for it.

## The gate

Dorian Cougias is the Release Owner Gate. This is an instruction-level gate, not technical enforcement: see `GOVERNANCE.md`.

## Checks

- `plugins/chief-of-staff/tests/test_sales_marketing.py` checks the package's files, its versions against the marketplace, that nothing shadows `sales:`, that the Chief of Staff routes to it, and that its local references resolve. `plugins/chief-of-staff/tests/test_roster.py` holds it to the roster.
- Those are structure checks. Whether the agent holds the gate is examined by the scenario evaluations recorded under `docs/evidence/`.

## Version History

- 0.1.0 (2026-10-07): CS-004. The department agent, the head skill and its sources, and `GOVERNANCE.md`.
