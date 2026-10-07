# chief-of-staff

Routes an ask to the department agents that own it, runs them in parallel, checks what they return, and brings Dorian a result, a proposal or a decision memo.

It manages the ten department agents in this marketplace: finance, people, it-operations, security, pmo, operations, corporate-strategy, customer-experience, sales-department and marketing-department. Design: the twelfth objective in `DESIGN.md` (CS-001 to CS-004).

## Skills

- `chief-of-staff:chief-of-staff` is the operating manual. It covers the reading order, the roster and where the lines between departments fall, the authority table, the Release Owner Gate, the return contract, the decision memo and the decision log.
- `/cos <ask>` hands an ask to the Chief of Staff.

The Chief of Staff runs in the main session, not as a subagent, because it has to dispatch agents and a subagent can't.

## What it reads

- `MoxyWolf Vault/_Shared Knowledge/Operating Norms/chief-of-staff-context.md`: the context card, which is the only home for MoxyWolf's company facts.
- It writes one log entry per run to `Taskade/<project>/00 – Project Hub/chief-of-staff-log.md`.

## Check

`tests/test_roster.py` fails when the roster and the department agents in `plugins/` drift apart. `tests/test_sales_marketing.py` checks the Sales and Marketing packages: their files, their versions against the marketplace, that neither shadows the installed `sales:` or `marketing:` skills, and that their local references resolve. Both are structure checks. Whether an agent holds the Release Owner Gate is examined by the scenario evaluations recorded under `docs/evidence/`.

## Sources

Built to Anthropic's Claude Managed Agents article, the Claude Agent SDK cookbook's Chief of Staff agent, and AI Maker's "AI Chief of Staff setup" post, all read 2026-10-06. The authority levels and the producer-auditor rule are ideas from headcount's `executive` plugin (`cbrock84/headcount` at `98d1c17`, MIT), written here in our own words. No file was copied.

## Version History

- 0.2.0 (2026-10-07): CS-004. A disagreement that involves sales-department or finance doesn't wait for security, and one that involves finance carries a section for the outside bookkeeper (Dorian, 2026-10-07). Routes ten departments: sales-department and marketing-department join the roster, with the Revenue and mixed-ask lines, the Release Owner Gate, five dispatch fields and the nine-field return contract for those two.
- 0.1.0 (2026-10-06): CS-001. Operating manual, `/cos` and the roster check.
