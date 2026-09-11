# Peer Review Contract

The single source of truth behind `/gstack-peer-review` (and its compatibility entry point `/gstack-codex-review`). `scripts/peer_review.py` enforces the mechanical parts (commit identity, output validation, round limits, tool routing); this file carries the parts a model has to read. The reviewer prompt embeds the sections marked **[reviewer]** verbatim.

## Operating rule

> Review the implementation against the agreed outcome. Inspect direct dependencies where necessary to establish correctness. Fix demonstrated blockers automatically within scope. Preserve unrelated findings separately. Do not turn review into a new project or return routine implementation decisions to the user.

This is a bounded cross-tool review loop, not a general audit. The plugin controls scope and stopping rules; neither model is asked to "keep reviewing until satisfied". Broad adversarial design review (challenging the approach) lives in `/gstack-plan-review`, before code exists. Here the approach is settled.

## Routing

| Builder | Reviewer |
|---|---|
| `claude` (Claude Code) | `codex` |
| `codex` | `claude` (Claude Code) |

The builder identity is supplied explicitly (`--builder`), never inferred from git authorship. If the other tool is not installed or not runnable, the outcome is `review_unavailable`. The dispatcher never substitutes the same tool and presents it as an independent review.

The reviewer runs in a fresh, non-interactive session against a detached read-only snapshot of the exact head commit. It is instructed not to edit the implementation or deploy; tool restrictions and snapshot permissions constrain writes. Production and human merge credentials must not be delegated to this process. It must not launch another reviewer (`GSTACK_PEER_REVIEW_SESSION` is set in its environment and the dispatcher refuses to open or run a review when it is present). Tests that need writes run in the builder's disposable validation worktree, not in the reviewer's snapshot.

## Model floors

Anything this plugin runs through Codex uses **Astra (`gpt-6-astra`) or higher**; anything it runs through Claude Code uses **Opus 5 (`claude-opus-5`) or higher** (Fable and Mythos qualify). Stated by Dorian 2026-09-11. The dispatcher passes `-m`/`--model` explicitly, reads back the model each CLI reports it actually ran, and ends the round as `model_below_floor` if either side is under the line. `GSTACK_CODEX_MODEL` / `GSTACK_CLAUDE_MODEL` change the model, never the floor.

## The review packet

The builder supplies one packet per completed implementation checkpoint (not per file edit). `peer_review.py open` validates it and refuses to proceed on a missing field or a commit that does not resolve.

| Field | Purpose |
|---|---|
| `outcome` | The user outcome in one or two sentences |
| `acceptance_criteria` | Nonempty list of unique, nonblank statements defining "done" |
| `release_owner` | Named accountable human's GitHub login; matched to the merge actor when recording release |
| `repos` | List of `{path, base, head}`. Exact commits, one pair per repository. Approval of one pair never carries to another |
| `changed_behavior` | What now behaves differently, and the entry points where execution reaches it |
| `exclusions` | Settled decisions and out-of-scope areas the review must not reopen |
| `tests` | `{commands, results, environment}`. What was run, what it showed, where |
| `prior_findings` | Finding IDs and dispositions from earlier rounds (filled in by the dispatcher after round 1) |

The builder's summary is a claim to check, not evidence. The reviewer opens the code at the pinned commits.

## Scope **[reviewer]**

Review the diff `base..head` in each repository against the packet's outcome and acceptance criteria. Direct-dependency boundary, not directory boundary. You may also inspect, with a stated reason:

- direct callers of changed functions;
- helpers and contracts those functions immediately depend on;
- the API/client or writer/database boundary the change crosses;
- tests intended to demonstrate the changed behavior.

Example: a change to a writer's offsets permits examining the browser's offset calculation and the database constraint. It does not authorize redesigning the parser.

Do not reopen anything listed under `exclusions`. Do not challenge the approach; that review already happened. Style, speculative scale, and alternate designs never block an otherwise correct implementation.

## What blocks **[reviewer]**

A finding is `blocking` only when you can show, with file and line evidence:

> This change causes, exposes, or depends on this defect, and it prevents an agreed acceptance criterion or creates a concrete correctness, security, or data-loss risk.

Everything else is `follow_up`. A serious unrelated exposure you happen to see is reported as `separate` (still visible, never absorbed into this feature, never blocking it).

Passing tests that assert the requested feature is refused do not satisfy acceptance. "No blocking findings" is a valid result; there is no minimum finding count.

## Finding format **[reviewer]**

Return JSON only, matching this schema (the dispatcher rejects anything else as `malformed_output`):

```json
{
  "verdict": "no_blocking_findings | blocking_findings",
  "acceptance": [{"criterion": "...", "met": true, "evidence": "file:line or test output"}],
  "findings": [
    {
      "id": "F1",
      "severity": "blocking | follow_up | separate",
      "file": "path", "line": 0,
      "what": "the defect, specific to this change",
      "evidence": "how the change causes, exposes, or depends on it",
      "criterion": "which acceptance criterion it prevents, or the concrete risk",
      "fix": "concrete remediation, described not applied"
    }
  ],
  "blocker_resolutions": [],
  "regressions_from_fixes": [],
  "notes": "one paragraph at most"
}
```

Acceptance must contain exactly one entry for every packet criterion, using the exact criterion text, a boolean `met`, and nonblank evidence. Unknown, duplicate, or missing criteria are rejected. A clean verdict requires all criteria met and no blocking findings.

`blocker_resolutions` is empty in the initial round. In fix rounds it covers every previous blocking finding exactly once with a boolean `resolved` and nonblank evidence. A resolved entry requires a `fixed` or `disproved` builder disposition and cannot also remain blocking. An unresolved entry must retain its blocking finding.

`regressions_from_fixes` contains only IDs of blocking findings in the same response; the matching finding carries the evidence. Orphan regression strings are rejected, so each regression participates in the next round’s blocker-resolution coverage.

Finding IDs are stable across rounds. In a fix-verification round, reuse the IDs from `prior_findings`; a genuinely new blocker gets the next unused ID and must meet the same evidence and scope rules.

## The loop

```
Builder completes checkpoint
          ↓
Other tool reviews pinned code and direct dependencies         (round 1: initial)
          ↓
Builder reproduces or substantiates each blocking finding
          ↓
Builder fixes accepted findings and runs focused checks
          ↓
Reviewer checks those fixes and regressions introduced by them (rounds 2, 3: fix-verification)
          ↓
Acceptance verification → ready for release decision
```

Default limit: one initial review plus two fix-verification passes (`--max-rounds 3`). A fix-verification round reviews the new head against the previous head plus the prior findings; it does not restart a full review. When rounds are exhausted with blockers still open, the outcome is `rounds_exhausted` and the dispatcher emits a concise escalation naming each unresolved finding and the exact disagreement. Exhausting the limit never becomes approval.

## Dispositions

The builder records one disposition per finding before the next round runs:

| Disposition | Meaning |
|---|---|
| `fixed` | Changed in the new head; the next round verifies it |
| `disproved` | Reproduction attempted and the defect does not exist; evidence attached |
| `deferred` | Real, out of scope for this checkpoint; tracked as follow-up |
| `unresolved` | Builder and reviewer disagree after evidence; escalates |

Unknown finding IDs are rejected, and `disproved` requires nonblank evidence. The CLI refuses blocking deferral: the human must approve a design amendment and the builder must open a new review against that contract. A disposition alone cannot waive a blocker.

## Outcomes

Every run ends in exactly one:

| Outcome | Means |
|---|---|
| `no_blocking_findings` | Reviewer found nothing blocking; acceptance verified |
| `fixes_verified` | Prior blockers fixed, no regressions, acceptance verified |
| `blocking_findings` | Blockers open; the builder's turn |
| `rounds_exhausted` | Limit hit with blockers open; escalation attached |
| `review_unavailable` | The other tool is not installed or not runnable |
| `missing_commits` | A base or head in the packet does not resolve |
| `timeout` | Reviewer exceeded the time limit |
| `malformed_output` | Reviewer returned something the schema rejects |
| `model_below_floor` | The reviewer ran (or was configured to run) below the model floor |

Only `no_blocking_findings` and `fixes_verified` are passing round outcomes; all other round outcomes exit nonzero. Only `opened` and `blocking_findings` accept another round. A terminal result closes the review; retry requires a new review ID.

## Release boundary

`peer_review.py release <review-id> --target <branch>` (target defaults to `main`) revalidates the stored raw review against the packet and prior blockers, checks the review identity, and requires clean local HEADs matching every reviewed head. It writes a revision-bound `release.json` with the target branch and request timestamp, then deliberately exits nonzero with `awaiting_human_release`. It never merges and has no approval flag. Build and ship report `ready_for_human_release`; review success alone does not authorize release.

The named human merges in GitHub under their own login. `peer_review.py record-release <review-id> --repo <path> --pr <number>` reads GitHub's PR record through `gh api`: the PR must be merged into the origin repository and requested target branch after the handoff timestamp, its head must equal the reviewed head, and `merged_by` must be the packet's Release Owner with GitHub type `User`. It writes a local merge decision with the review ID, action, head, merge commit, actor, timestamps, and source URL. It performs no remote write. Record each repository separately before reporting completion.

This is a governance boundary, not a security sandbox or signature system. Local state files are writable by the agent and are not tamperproof. GitHub identity identifies the merge account, not proof of substantive human review; the human's merge credential must not be delegated to the agent, and branch protection is externally enforced. Shared oversight logging and data-use gates belong to the later GA-004 scope.

## Storage

Everything for one review lives under one review ID: `$GSTACK_PEER_REVIEW_DIR/<review-id>/` (default `~/.gstack/peer-review/`). `packet.json`, `round-N.json` (raw reviewer output plus validation result), `dispositions.json`, `state.json` (outcome, rounds used, head per round). The final check exercises the user's workflow, not only the internal helpers; the builder's `tests` field in the packet is where that evidence goes.
