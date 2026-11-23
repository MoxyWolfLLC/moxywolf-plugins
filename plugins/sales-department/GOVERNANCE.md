# sales-department: Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md).

The agent and the skill below each declare a risk tier and are held to the five tests:

1. **Gate sized to stakes**: a human checkpoint before any high-stakes or irreversible action.
2. **A named human signs**: high-tier output needs one named human to approve, and the approval is recorded.
3. **Provenance**: claim-bearing output carries its source and date; no fabricated citations.
4. **Anti-rubber-stamp**: the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop**: no autonomous irreversible action; a named human owns the outcome.

## Risk surface

This package ships instructions only: one agent definition and one head skill. It has no scripts, no hooks and no connectors of its own. On its own it reads the dispatch and writes an answer.

The risk comes from what it borrows. The installed `sales:` skills, and the tools connected in a session, can send, post, book, publish, spend and write to customer systems. The head skill says a specialist's instructions can't widen this department's authority, and it turns every such step into an approval request.

Since version 0.2.0 (2026-11-07) the department also runs the SDR operation, and that operation acts: it sends through SalesForge and writes to the CRM. Those acts are authorized only inside the bounded-delegation charter, with a reviewed table and the daily report. The charter is the authority for them, not this package and not any specialist. See "Expansion 2026-11-07: the SDR operation" below. This change is exactly the trigger the last section of this file names, and the five tests were run again for it before it shipped.

**The named Release Owner is Dorian Cougias.** He's the gate for external communications, publication, spend, production release, customer-system and CRM writes, deletion, permission changes and sensitive actions. An approval binds him, the action, the audience or system and the exact artifact revision, and a changed artifact needs a new one. The Chief of Staff records his decision in its decision log (`Taskade/<project>/00 – Project Hub/chief-of-staff-log.md`). A high-stakes decision is also recorded through `GitHub/Projects/_gate-log/record_decision.py`, as the charter requires, with a stop recorded as carefully as a signature. To share the row, in `GitHub/Projects`, commit only `_gate-log/gate-decisions.jsonl`, push as the `moxywolf-agent` app, check that `git ls-remote origin refs/heads/main` equals `git rev-parse HEAD`, and pull back; a row whose push didn't land is reported as local only.

**This gate is an instruction, not a control.** Nothing in this package stops a connected tool from acting. The enforcement that exists is in each connector's own permission settings and in Dorian's review. Test 1 and Test 5 are met by instruction and by the recorded scenario evaluations under `docs/evidence/`, and this file doesn't claim more than that.

**Test 3 is carried by the return contract.** Every claim is a supplied fact, a verified observation or an inference, every source has its origin, link, date and retrieval date, and a claim without support stays flagged.

**Test 4 is carried upstream.** The Chief of Staff sends an incomplete result back once and then escalates it without filling the gap. Security reviews output that touches identity, secrets, customer data or an outside integration, and its blocking findings stand.

## Skill and agent risk tiers

| Skill or agent | risk_tier | Gate or note |
|---|---|---|
| `sales-department` (agent): takes a dispatch, loads the head skill and a specialist, returns analysis and drafts | generate | Writes nothing outside its answer. Stops without the context card. Every send, publish, spend, release, deletion, permission change and system write becomes a pending approval for Dorian Cougias. |
| `sales-department` (agent): runs the SDR operation inside the bounded-delegation charter | side-effectful-gated | Sends through SalesForge and writes to the CRM, only inside the charter's bounds, only after a reviewed table, and only with the daily report. Outside the bounds, the generate row above applies. |
| `head-of-sales` (skill): remit, lines, specialist routing, return contract and the gate | generate | Instructions only. Names the gate and says it isn't technical enforcement. |
| Installed `sales:` specialists, when loaded by this department | side-effectful-gated | Not shipped here and not tiered by their own marketplace. Inside this department, any action they can take through a connector waits for Dorian's recorded approval of that exact action and artifact revision, except for SDR-operation acts inside the charter's bounds. |

## Expansion 2026-11-07: the SDR operation

Version 0.2.0 widens the department from draft-only to the SDR operation, inside the bounded-delegation charter. The five tests, run again for this change:

1. **Gate sized to stakes**: unchanged. Dorian stays the Release Owner Gate. Sends inside the charter's bounds still pass two checkpoints before they go out: his approval of the review table for that batch, and the daily report after. Anything outside the bounds still needs his per-item approval of the exact action and artifact revision.
2. **A named human signs**: unchanged. The charter records Dorian's choice of bounded delegation (2026-11-07). The gate log records this expansion decision the same way it records any high-stakes decision. A changed artifact still spends its approval.
3. **Provenance**: unchanged. The return contract still carries every claim as a supplied fact, a verified observation or an inference, with its source and date. The charter and the ICP join the head skill's sources.
4. **Anti-rubber-stamp**: the review table is the threshold. A batch sends only after Dorian approves, edits, or cuts its rows. The department refuses to send a batch with no reviewed table, and it stops on its own on a credit warning, a bounce spike, any STOP or complaint, or any reply suggesting the list or copy is wrong.
5. **Human above the loop**: unchanged. No autonomous irreversible action. Dorian saying "stop" ends all sending immediately, and he may revoke or change any bound at any time. The bounds are reviewed weekly, and a bound that proves wrong gets tightened, not loosened, without a new decision.

What this expansion does not change: the gate is still an instruction, not a control. Nothing in this package stops a connected tool from acting. The enforcement that exists is in each connector's own permission settings, in the charter's bounds, and in Dorian's review.

## What re-triggers this file

A script, a hook, a connector or any step that acts on its own. Adding one means the five tests again and an update here before it ships.
