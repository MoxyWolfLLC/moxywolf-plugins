# marketing-department: Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto. See the fleet-wide standard and migration plan in [`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md).

The agent and the skill below each declare a risk tier and are held to the five tests:

1. **Gate sized to stakes**: a human checkpoint before any high-stakes or irreversible action.
2. **A named human signs**: high-tier output needs one named human to approve, and the approval is recorded.
3. **Provenance**: claim-bearing output carries its source and date; no fabricated citations.
4. **Anti-rubber-stamp**: the skill refuses to ship below a defined threshold; oversight is auditable.
5. **Human above the loop**: no autonomous irreversible action; a named human owns the outcome.

## Risk surface

This package ships instructions only: one agent definition and one head skill. It has no scripts, no hooks and no connectors of its own. On its own it reads the dispatch and writes an answer.

The risk comes from what it borrows. The installed `marketing:` skills, and the tools connected in a session, can send, post, book, publish, spend and write to customer systems. The head skill says a specialist's instructions can't widen this department's authority, and it turns every such step into an approval request.

**The named Release Owner is Dorian Cougias.** He's the gate for external communications, publication, spend, production release, customer-system and CRM writes, deletion, permission changes and sensitive actions. An approval binds him, the action, the audience or system and the exact artifact revision, and a changed artifact needs a new one. The Chief of Staff records his decision in its decision log (`Taskade/<project>/00 – Project Hub/chief-of-staff-log.md`). A high-stakes decision is also recorded through `Taskade/_Shared Files/_gate-log/record_decision.py`, as the charter requires, with a stop recorded as carefully as a signature.

**This gate is an instruction, not a control.** Nothing in this package stops a connected tool from acting. The enforcement that exists is in each connector's own permission settings and in Dorian's review. Test 1 and Test 5 are met by instruction and by the recorded scenario evaluations under `docs/evidence/`, and this file doesn't claim more than that.

**Test 3 is carried by the return contract.** Every claim is a supplied fact, a verified observation or an inference, every source has its origin, link, date and retrieval date, and a claim without support stays flagged.

**Test 4 is carried upstream.** The Chief of Staff sends an incomplete result back once and then escalates it without filling the gap. Security reviews output that touches identity, secrets, customer data or an outside integration, and its blocking findings stand.

## Skill and agent risk tiers

| Skill or agent | risk_tier | Gate or note |
|---|---|---|
| `marketing-department` (agent): takes a dispatch, loads the head skill and a specialist, returns analysis and drafts | generate | Writes nothing outside its answer. Stops without the context card. Every send, publish, spend, release, deletion, permission change and system write becomes a pending approval for Dorian Cougias. |
| `head-of-marketing` (skill): remit, lines, specialist routing, return contract and the gate | generate | Instructions only. Names the gate and says it isn't technical enforcement. |
| Installed `marketing:` specialists, when loaded by this department | side-effectful-gated | Not shipped here and not tiered by their own marketplace. Inside this department, any action they can take through a connector waits for Dorian's recorded approval of that exact action and artifact revision. |

## What re-triggers this file

A script, a hook, a connector or any step that acts on its own. Adding one means the five tests again and an update here before it ships.
