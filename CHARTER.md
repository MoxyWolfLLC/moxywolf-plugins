---
type: project-charter
project: MoxyWolf Software (governed-autonomy charter)
created: 2026-06-22
updated: 2026-06-22
status: active
---

# MoxyWolf Software Charter — Governed Autonomy

The constitution for how MoxyWolf builds software. It encodes the MoxyWolf AI Governance Manifesto (researched, Council-vetted) as durable, checkable invariants, and it is enforced operationally by [`PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md). It governs all MoxyWolf software; the `moxywolf-plugins` fleet is the first adopter and the reference implementation.

## Mission
Build smart, not big: let the machine run as fast as the stakes allow, keep a named human above the loop who owns the outcome, and size the gate to what's at risk.

## Principles

1. **Risk tier + Release Owner — the load-bearing rule.** *Every skill declares a risk tier, and routes high-stakes (irreversible / customer-reaching / money-moving) actions through a named Release Owner who signs, with the decision logged.*
2. **The gate is sized to the stakes.** Low-risk reversible work runs with automated checks and sampled review; medium-risk gets rotating human approval that can stop the line; high-risk or irreversible work takes one named signature before it ships. A rule that says "a human signs everything" eats the judgment it's trying to protect.
3. **Human above the loop.** No autonomous irreversible action. A named human owns the result regardless of how much of the work the machine did. The axis of accountability is never automated, even when the work is.
4. **Provenance is the substance layer.** Claim-bearing or factual output carries its source and date. No fabricated citations; unverifiable claims are flagged, not shipped.
5. **Audit the oversight, not just the output.** High-stakes decisions are logged; override rate and response time are tracked so a rubber-stamp pattern is detectable. A gate that's never triggered isn't quality, it's a gate asleep.
6. **Tiers are revisable, not sacred.** Automated validation that earns trust at the low tiers may climb, and we want it to. What never moves is the accountability axis: someone always owns the result.
7. **We hold ourselves to this first.** We build the gate into our own software and point it at ourselves before asking anyone else to adopt it.

## Technical Constraints
- Each plugin carries a `GOVERNANCE.md` with a per-skill risk tier (`read-only` | `generate` | `side-effectful-gated` | `high-stakes`) and passes the five conformance tests in the plan.
- High-stakes gate decisions are recorded via `Taskade/_Shared Files/_gate-log/record_decision.py`; `override_report.py` produces the override-rate and response-time rollup.
- Reference patterns to copy from: `4d-blog-engine` (the Release Owner gate), `research-pipeline` / `academic-pipeline` (provenance and citation verification).

## Architectural Boundaries
- No autonomous high-stakes action: sending, publishing, moving money, e-signature, deletion, or writes to customer systems / CRM / DB / config happen only behind a named-human sign-off.
- Provenance routing: claim-bearing publish paths run through a citation verifier; no skill invents citation data.
- A new side-effectful capability re-triggers the five tests and a `GOVERNANCE.md` update before it ships.
- Any changed plugin's `version` is bumped in the same commit as the change; the `version` field is what gates updates.

## Non-Negotiables
- Never fabricate a citation, a statistic, or a person's name. Only a real, named human signs.
- No autonomous irreversible action, regardless of how capable the automation looks.
- Commits to MoxyWolf repos: Claude authors the commit text; a human pushes via GitHub Desktop; never write to `.git/`.
- Effort is described by complexity and dependencies, never wall-clock weeks or dollar budgets.

## Version History
- 2026-06-22: Initial charter. Encodes the AI Governance Manifesto as MoxyWolf's software constitution and features the risk-tier / Release-Owner clause that the Plugin Conformance & Migration Plan enforces.
