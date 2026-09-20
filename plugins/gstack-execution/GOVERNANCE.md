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

## Gate configuration: delegated by capability, not by trust

> **THE GATES ARE LIVE. THE SEPARATION IS STILL NOT.** Read those as two facts, because on
> 2026-09-15 they came apart in exactly the way this section was written to prevent.
>
> What is real: `OpenControls-AI/cki@main` carries branch protection with three required status
> checks - `node suites (no deps)`, `python suites` and `dr094 gate` - and `enforce_admins` on.
> GitHub refuses the merge now; the process is no longer the only thing standing there.
>
> What is not real: `GITHUB_GATE_TOKEN` does not exist. Those checks were configured with the
> vault's **classic** PAT, by a direct `PATCH` to
> `/repos/{owner}/{repo}/branches/main/protection/required_status_checks`, at the release owner's
> explicit instruction. So the pushing credential and the administering credential are still the same
> token, which is the property this document withholds.
>
> And note HOW that happened. `repo_gates.py ensure` refuses a classic token, and it did its job -
> it was never called. Calling the REST API directly walked around it. A control that lives in one
> script is a convention, not a boundary, and the agent that bypassed it was the one the boundary
> exists to constrain. Until the fine-grained token exists and gate configuration goes through it,
> what protects this is that the bypass is written down here.
>
> A separate fine-grained token WAS minted that day - `cki-ci-oc-website-read`, `Contents: Read` on
> `OpenControls-AI`, held as the `CROSS_REPO_TOKEN` CI secret. It is not this token and cannot serve
> as one: it holds no `Administration` permission, by design.


Branch protection was "enforced externally" and nothing checked it, which meant a workflow could run
on every pull request, go red, and merge anyway while the team believed it was covered. `cki@main`
produced eight check-runs in that state. Verifying and configuring required checks is therefore a
delegated act now, and the delegation is built so that it cannot become merge authority.

**Two credentials, and the separation is the point.**

| Credential | What it is | What it may do |
| --- | --- | --- |
| `moxywolf-agent` app token | minted per command by `scripts/agent_token.py` from the app key in the vault (GA-005); `Contents` and `Pull requests` write, `Metadata` read | feature branches, pull requests, reads, and a merge through a pull request when the Release Owner tells the agent to. Cannot push to `main`, and carries no `Administration`. Acts as `moxywolf-agent[bot]`, never under a person's login. |
| `GITHUB_GATE_TOKEN` | a **fine-grained** token, scoped to the named repositories, `Administration: read and write`, `Contents: read` | add required status checks. Cannot push anything. |

A token that can *set* a required check can also *remove* it, and with protection removed a token that
can push has merge authority. So delegating gate configuration on a classic `repo`-scoped token would
hand an agent exactly the authority this document withholds, in the act of configuring the control that
enforces it. A fine-grained token with `Contents: read` cannot push whatever it does to protection, so
the property survives the delegation. That is why the credential is not simply "the PAT with more
scopes."

This is **enforced, not requested**: `scripts/repo_gates.py ensure` asks GitHub what kind of token it
was given - a classic credential returns `x-oauth-scopes`, a fine-grained one omits the header - and
refuses a classic token by name, citing its scopes. It also refuses a token it cannot identify. The
check is on capability, not on the `ghp_`/`github_pat_` prefix, because a prefix is a naming convention
and this decision is not about naming.

**What stays outside agent authority, unchanged.** Every personal credential. Pushing to a protected
branch. Merging a pull request nobody asked for: the agent merges only on the Release Owner's instruction,
posted on the pull request first, and `record-release` refuses a bot merge without one (GA-005). `ensure` only ever *adds* a required context: it never removes one,
never relaxes a protection setting, and refuses to write a configuration built on a failed read - the
API's PUT replaces the whole protection object, so anything not carried forward is protection silently
destroyed. Enabling protection on an unprotected branch is out of scope and reported as a wider
decision for the Release Owner.

**The plan can make this impossible, and it is the ORGANISATION's plan, not the account's.** Branch
protection needs a paid plan on the org that owns the repository. MoxyWolf's repositories are split
across two organisations and only one of them is paid:

| Organisation | Plan | Consequence |
| --- | --- | --- |
| `MoxyWolfLLC` | team, 13 seats, 7 filled | protection available; the API answers `404 Branch not protected` |
| `OpenControls-AI` | free, 5 members | protection unavailable; the API answers `403 Upgrade to GitHub Pro` |

`cki` and `oc-website` are in the free org, which is why their eight check-runs are advisory and were
always going to be - not because of any token. A 403 from the protection endpoint is ambiguous by design
and must be read from its **message**, not its status: insufficient rights and unavailable-on-this-plan
are different answers with different fixes, and `repo_gates.py` exits 2 and 3 to keep them apart. The
two routes out are upgrading the free org, or moving those repositories into the paid one, which has
six seats already paid for.

**When GitHub cannot hold the gate, the process is the gate.** On such a repository the plugin's refusal
is the only thing standing between a red suite and a merge, so it has to actually refuse: `/gstack-build`
does not report `ready_for_human_release` while a suite is red or has examined nothing, and the handoff
states plainly that the merge is unprotected and rests on the Release Owner reading the evidence. That is
weaker than a required check and must be described as weaker. The upgrade path is a paid plan on the
organisation; until then, no document should describe these suites as gates.

**What an agent run looks like without the gate token**, which is the normal case: `repo_gates.py check`
reports the check-runs the branch produced and `UNREADABLE (HTTP 403)` for what it requires, because
reading protection needs rights the push token does not have. That is reported as neither evidence that
nothing is required nor that anything is. The observed names go into the handoff for the Release Owner
to confirm.

Local review records are not tamperproof, and this dispatcher is not an OS security sandbox. Personal credentials must not be delegated to agents; branch protection is enforced externally. `record-release` records GitHub's merge actor for the exact reviewed head: the named `User` as `human_merge_recorded`, or the agent's app as `agent_merge_on_instruction` with the instruction it posted before merging. Neither is a claim of substantive human review, and the instruction comment is the agent's own record of what it acted on. The [task graph contract](skills/gstack-execution/references/task-graph-contract.md) defines data-use checks and shared gate-log observations. The packet records permission; it does not authenticate its author or establish OS isolation.

## Governed task graphs

[`scripts/task_graph.py`](scripts/task_graph.py) consumes the static declarations in [`workflows`](workflows). Nodes declare dependencies, consumed inputs, output ownership and effects. The executor admits ready nodes within the concurrency cap and refuses unsupported effects, conflicting writers and incomplete dependencies. CSO and verify converge through an other-tool checker; review partitions delegate to the existing cross-tool dispatcher. There is no merge or deploy handler.

Data-use checks precede dispatch and report export: named policy owner, classification, repository/history permission, tool destinations, exact proof command argv and output roots. Missing authorization denies the action. Local policy and logs are writable records, not authenticated grants; runtime and OS permissions remain separate.

| Action | Authority and record |
|---|---|
| Graph plan/run | Authorized source analysis, model disclosure and local artifact generation within packet permissions. Failed dependencies block convergence. |
| Proof execution | Exact allowed argv, serialized local proof path; captures actual output and exit status. |
| Report export | Complete report and authorized destination required; repeated identical export is idempotent. |
| Human observation | Evidence-linked local observation, optionally shared gate-log entry; does not authorize execution or release. |
| Oversight summary | Separates observations from machine events; override/timing measures are investigation signals, not proof of substantive review. |

A signed observation label is not a digital signature. Human observations do not convert machine success into human approval. Release remains the named human's GitHub action under the peer-review contract.
