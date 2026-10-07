# marketing-department

Audience, positioning, campaign and content planning, and performance analysis. Owns audience-level demand generation.

MoxyWolf's Marketing department, as a department agent the Chief of Staff routes to. Design: CS-004 in `DESIGN.md`.

The package is named `marketing-department`, not `marketing`, so it doesn't shadow the installed `marketing:` skills. Those stay where they are, in another marketplace, and this department loads them as its specialists.

## Agent

`agents/marketing-department.md` is the department agent. It loads `marketing-department:head-of-marketing` first, checks the dispatch, loads the installed specialist the request needs, stays inside the remit, and returns nine labelled fields. It analyzes and drafts. It doesn't send, publish, spend, release, delete, change permissions or write to a customer system.

## Skill

- `marketing-department:head-of-marketing` is the department's operating manual: the remit, the lines with the other departments, specialist routing, the Release Owner Gate, the Security review rule, the evidence rules and the return contract. Its sources are in `skills/head-of-marketing/references/sources.md`.

## Specialists it borrows

Named in the head skill, verified in the installed `marketing` plugin (Anthropic, 1.2.0) on 2026-10-07, and resolved again at run time:

- `marketing:campaign-plan`
- `marketing:content-creation`
- `marketing:brand-review`
- `marketing:seo-audit`
- `marketing:performance-report`

If one isn't installed in a session, the work that depends on it is blocked and the agent says so. It doesn't substitute for it.

## The gate

Dorian Cougias is the Release Owner Gate. This is an instruction-level gate, not technical enforcement: see `GOVERNANCE.md`.

## Checks

- `plugins/chief-of-staff/tests/test_sales_marketing.py` checks the package's files, its versions against the marketplace, that nothing shadows `marketing:`, that the Chief of Staff routes to it, and that its local references resolve. `plugins/chief-of-staff/tests/test_roster.py` holds it to the roster.
- Those are structure checks. Whether the agent holds the gate is examined by the scenario evaluations recorded under `docs/evidence/`.

## Version History

- 0.1.0 (2026-10-07): CS-004. The department agent, the head skill and its sources, and `GOVERNANCE.md`.
