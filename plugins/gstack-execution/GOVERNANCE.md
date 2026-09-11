# gstack-execution — Governance

This plugin is held to the MoxyWolf plugin conformance standard. See
[`../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md`](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md)
for the full standard. Every skill/command passes each of the five tests that applies to it:

1. **Gate sized to stakes** — a human checkpoint before any high-stakes / irreversible action.
2. **A named human signs** — high-tier output requires one *named* human to approve, recorded.
3. **Provenance** — claim-bearing output carries source + date; no fabricated citations.
4. **Anti-rubber-stamp** — refuses to ship below threshold; oversight is auditable.
5. **Human above the loop** — no autonomous irreversible action; a named human owns the outcome.

Risk tiers: `read-only` | `generate` | `side-effectful-gated` | `high-stakes`.

The code-write paths (`gstack-build` and `gstack-ship`) carry the no-auto-merge rule: **never auto-push to a
protected branch and never auto-merge — a named human owns the merge; the pipeline prepares the
PR and stops.**

| Skill / command | risk_tier | gate / note |
|---|---|---|
| `gstack-build` | side-effectful-gated | Authorized feature-branch edits/commits/pushes and PR preparation; passing review prepares a handoff, human GitHub merge is recorded before done. No protected push or agent merge. |
| `gstack-design-doc` | generate | Human approval precedes writing design changes; authorized feature-branch commits/pushes only. |
| `gstack-plan-review` | read-only | Bounded plan review; decisions remain with the human. |
| `gstack-peer-review` | side-effectful-gated | Read-only other-tool reviewer; builder fixes in scope and records dispositions. Named Release Owner, exact acceptance and blocker coverage required. |
| `gstack-verify` | read-only | Advisory claim verification; never a shipping gate. |
| `peer_review.py release` | side-effectful-gated | Writes local revision-bound handoff; always stops awaiting human release. Never merges. |
| `peer_review.py record-release` | side-effectful-gated | Reads GitHub merge identity/head and writes local decision; no remote mutation. |
| `gstack-ship` | side-effectful-gated | Prepares PR only. No auto-push to protected branch, no auto-merge; a named human owns the merge (Tests 1, 5). Stops on blocking test/CRITICAL review findings. |
| `gstack-review` | read-only | Pre-landing structural review; reports findings, no writes. |
| `gstack-codex-review` | read-only | Adversarial review of just-committed code; reports only. |
| `gstack-cso` | read-only | Security audit (OWASP, STRIDE, supply chain, secrets); reports only. |
| `gstack-investigate` | read-only | Root-cause debugging with hypothesis testing; analysis only. |
| `gstack-qa` | side-effectful-gated | Browser QA; any code fixes are local edits offered to the human, not pushed (Tests 1, 5). |
| `gstack-browse` | read-only | Browser-based page verification / dogfooding; observation only. |
| `gstack-design` | generate | Design-system consultation + local UI generation; no deploy. |
| `gstack-execution` (skill) | side-effectful-gated | Shared methodology; governs the commit/push/PR boundary above — no autonomous irreversible action. |

Routine feature-branch work remains authorized. The packet's `release_owner` is the named human's GitHub login. The [peer-review contract](skills/gstack-execution/references/peer-review-contract.md#release-boundary) defines the evidence checks and release handoff. A passing machine review cannot authorize a protected push or merge. Blocking deferral requires an approved design amendment and a new review.

Local review records are not tamperproof, and this dispatcher is not an OS security sandbox. The human merge credential must not be delegated to agents; branch protection is enforced externally. `record-release` records GitHub's named `User` merge actor for the exact reviewed head, not a claim of substantive human review. Shared gate-log integration and data-use gates are deferred to GA-004.
