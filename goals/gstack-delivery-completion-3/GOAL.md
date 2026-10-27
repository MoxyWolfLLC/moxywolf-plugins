## Serves
Eleventh objective: goal mode

## Outcome
Deliver the preserved Gstack delivery implementation through the existing gated merge route, release recording, marketplace update and synchronization of the required Mac checkout. Repair the five identified delivery defects and the three blockers found at 675bb13 together; correct the acceptance evidence without rewriting history. A PR, a passing review, an implementation merge, or an old checkout-sync flag is not completion.

This successor was requested by Dorian on 2026-10-27 at 14:57 PT. It approves one repair item for the three blockers that the single authorized round of goal gstack-delivery-completion-2 found at 675bb133f7b63e8e17cad0a585a3b12c03501386. It then carries the repaired candidate through the existing delivery route. It supersedes the execution authority of goal gstack-delivery-completion-2 (PR #264, approved head 29dacff1b7c3efba478d0501b189dae923a67802), whose run is recorded stopped at item 1, not its records.

Its review 20261027-144404-675bb13-9l70pwgt (codex/gpt-6-astra, 1 of 1 round, rounds_exhausted) and the completion goal's exhausted review 20261027-124210-98b5ed8-o897p6eo keep their ids, counts, findings and dispositions. They are attached to the new review as history.

The builder checked each blocker in the code at 675bb13 before preparing this approval:
- **F1.** `goal_delivery.next_action` requires a clean review at exactly the change's head (goal_delivery.py:201). `peer_review.py record-release` requires the merged pull request's head to equal the reviewed head (peer_review.py:3271). The GO-011.2 whole-goal review is pinned to the head where the goal tests passed, without the holdout (goal_run.final_review_pinned). `goal_guard.final_merge_allowed` merges the finalized head, one commit later carrying the run record and the holdout. So the goal-to-main change can never pass delivery planning or release recording.
- **F2.** `observe_checkout` (goal_delivery.py:330) and `sync_checkout` (:283, :303) read `git status` stdout without its exit code. An unreadable index therefore reads as clean.
- **F3.** `_observe_checkouts` (goal_run.py:870) and the sync executor (:1018-1022) select required merges by target branch alone and check only the last one. They bind no repository and leave earlier required merges unchecked.

F4 (version_bump evidence) is a separate evidence gap. It is answered with the existing PR-run report of the event, base, head and version_bump result, not with code. The 14 embedded-instruction locations the round reported are follow-ups, not this item's scope.

Inputs: build branch build/gstack-delivery-completion-1-repair-release at 675bb13, unchanged, over main 292e75a, with PR #265 into goal/gstack-delivery-completion-2. The repair is built on a new branch from 675bb13. Its pull request goes into goal/gstack-delivery-completion-3, whose base is main at the merge of this approval: db65b1d plus only this goal folder. Any other movement of main at start stops the run. PR #265 is closed with a link to its successor, and its branch is preserved.

The three repairs:

(6) Finalized-head compatibility through release recording. Delivery planning and record-release accept the goal-to-main merge only in the relationship GO-011.2 already defines. The whole-goal review must be clean and pinned to the tested head without its holdout, as goal_run.final_review_pinned decides. The merged head must be the recorded finalized head: one commit on that tested head changing only goal-runs/<id>/RESULT.md and goal-runs/<id>/holdout.py, or the existing resync form. Every other change keeps the exact-head rule. This does not relax a gate: it accepts nothing goal_guard.final_merge_allowed would refuse, it reuses that relationship rather than restating it, and the holdout never enters a review surface. goal_guard.py and every other gate-owned file are unchanged.

(7) Failed Git inspections refuse synchronization. Every Git read that observe_checkout and sync_checkout rely on, including status, rev-parse, symbolic-ref, remote, merge-base, ls-remote and fetch, is checked for its exit code before its output is interpreted. A failed or unreadable inspection reports sync_pending with that reason and performs no checkout write.

(8) Repository-specific verification of every required merge. Each required checkout is bound to its repository by its remote's repository identity. Its required merges are that repository's verified merges into its branch, all of them, and each must be an ancestor of the checkout's HEAD and of the remote tip. This applies in observation, synchronization and the completion decision. No newest-merge inference is drawn from record order, and another repository's merge never counts for it.

Before the review is dispatched, a local end-to-end demonstration runs as a ledger receipt at the candidate head. It uses temporary local repositories and a recorded fake of the GitHub API, labelled as such, and runs the real goal_run, goal_delivery, goal_guard and peer_review code through these steps:
1. finalize
2. whole-goal review binding
3. the GO-011.2 merge decision
4. record-release
5. the marketplace top-level-version companion
6. required-checkout synchronization
7. the completion decision

Its output is committed as evidence. It demonstrates the path; it does not replace observing the real merges and checkout afterwards.

The one implementation item includes the existing graph-context runtime, bounded review recovery, delivery executors, completion reporting and checkout synchronization already in those candidates, plus exactly these five original repairs, now with repairs (6)-(8) above: (1) validate repository/PR/candidate/target identity before accepting a merge; (2) preserve and validate CI PR/current-base bindings; (3) refuse resume advancement for terminal or held runs; (4) consult persisted merge-request state across process restarts and re-observe an uncertain result instead of automatically resending; (5) re-observe every required checkout before marking delivery complete. Persisted declarations alone establish none of these facts.

Acceptance evidence is corrected in this approval. Keep the retrospective comparison labelled retrospective; never claim tests ran before implementation when they did not. The old per-test log is retained as historical evidence with its hash and limitations, not relabelled as a newly executed ledger receipt. A new, clearly dated and head-bound per-test run may substantiate the reconstruction, provided the baseline and test-file identities are verified; it must not replace or erase any failed receipt. Unknown 3107b5e1e958 is answered by the accepted retrospective label and stays unresolved as a chronological fact unless the existing tool legitimately records a narrower resolution. Its closure is not an acceptance criterion. All release gates, including any open-unknown gate, still apply.

Review acceptance is pre-merge: exact proposed PR identity and candidate/base, complete diff, current verified evidence, existing gates, the five original repairs and repairs (6)-(8). Post-merge verification is separate: observe the exact reviewed head merged into the approved target, run record-release, then verify required synchronization and the release companion. No reviewer is asked to certify a future merge. Prior reviews and their findings are attached as history, never substituted for a fresh review of the repaired complete candidate.

Reuse goal-5's eight independently drafted goal tests byte-for-byte and its holdout hash. Their gpt drafter and gemini reading are preserved and identified as reused; no new reading is claimed. The repair cases for all eight repairs are implementation regression tests, not hand edits to the independent goal tests. The unseen holdout remains on the Mac; before publishing the approval PR, verify that the same opaque file can be made available outside the repository under this new goal id using a filesystem hard link, without printing, rewriting or re-drafting it, with its approved hash unchanged.

Authority and route: approval means Dorian's approving GitHub review at this folder's exact PR head, followed by goal_brief.py verify. The predecessor run is already recorded stopped. Start goal/gstack-delivery-completion-3 from then-current main.

Build the three repairs test-first on build/gstack-delivery-completion-3-1-final-path from 675bb13:
- red receipts at the tests-only commit
- green receipts at the repaired head
- the local demonstration receipt

Open one pull request into the goal branch. Merge it only into the goal branch, after its exact-head cross-vendor review and required checks at that pull request. Close PR #265 with a link to it.

Any main-to-goal synchronization uses a checked sync PR, never a push. Rerun the goal tests after the item merge. Finalize the run record and holdout through the existing PR path. Then a fresh whole-goal review and the required GitHub Actions goal-holdout, tests, goal-envelope and goal-tests precede the goal-to-main merge, which the bot performs under GO-011.2. Run record-release for each governed merge. Then make the declared marketplace top-level-version-only release companion PR into main, through its normal review, checks, merge and record-release.

Act as the app, never Dorian. No admin bypass, gate exception, narrow-packet acceptance or coverage override is authorized. Execution proceeds through merge, release recording and Mac synchronization without routine questions. It returns to Dorian only for an exhausted limit, a changed scope, or a gate that requires his action.

This approval authorizes up to three review passes for the repaired implementation item (initial plus two repair rounds), up to two for the whole-goal checkpoint, and one for the marketplace companion, all within the six-call aggregate below. The predecessors' spent review counts remain historical; they are not erased or presented as unused. Their exhausted reviews keep their ids and counts, and this is new authority for a new candidate, not a reset of either. A replacement id consumes the same checkpoint's remaining allowance. A finding fixed within the approved scope needs no further routine permission; changed scope, gates or exhausted limits stop the run.

Required synchronization target only: /Users/doriancougias/GitHub/moxywolf-plugins, on Dorian's Mac, origin MoxyWolfLLC/moxywolf-plugins, branch main. Bind the actual Mac hostname and accepted remote spelling from that checkout in the delivery record before execution; do not assume the cloud host is the Mac. ~/Developer/moxywolf-plugins and ~/review-host-i050 are excluded. The required checkout was last observed clean on the candidate branch at b321160. An authorized operator may switch it to main only after confirming it is clean and preserving its candidate branch/ref; sync-checkout itself never switches branches. If it has become dirty, unavailable, divergent, wrong-host or otherwise ineligible, preserve it unchanged and report sync_pending. The implementation may be released while synchronization is pending, but delivery is not complete.

Time: the ten active hours Dorian approved at 11:52 PT on 2026-10-27 remain the single limit across the completion goal, goal-2 and this goal. Through 21:48:10Z, 10,662.562 seconds (about 2.96 hours) were charged:
- 2,005.562 s of approval preparation and publication, of which 1,560 s were labelled allowances and unmeasured handling
- 8,657 s of measured active work from 18:52:44Z, net of 1,869 s of recorded waits

That leaves at most about 7.04 hours. The seconds spent preparing this approval from 21:57:00Z are measured and charged against it. The run persists the cumulative total. Waiting time is reported separately. Approval, restart, a successor goal and replacement review ids never reset it.

Calls: this approval proposes six further counted model calls, replacing the three that remained (6 approved for the completion goal, minus its 2 and goal-2's 1). Counted has the repository's existing goal_spend.py meaning: subscription calls and metered calls with no reported cost.

They are allocated across the review allowances above:
- implementation up to 3
- whole-goal up to 2
- companion 1

Before each call, verify its checkpoint allowance and the aggregate. Reserve at least one call each for the whole-goal and companion reviews while they remain required.

This goal's spend ledger starts empty and records only its own calls. The predecessors' ledgers, their calls and the 13:57 correction stay where they are. Max calls 8 below keeps the existing 80% gate from stopping non-model delivery actions immediately after the sixth authorized call. The separate, stricter authorization is six: refuse before a seventh new counted call in this goal, irrespective of the nominal native field. No gate implementation is changed or bypassed.

Priced gateway and council calls, such as model_select, still consume the metered budget. Each is recorded individually with model, provider and cost, and reported separately as total model invocations. Unknown-cost calls count. The existing $50 OpenRouter cap and $40 early stop are retained, and all new priced charges are measured. No unrecorded model dispatch is permitted, including during preparation or outside the goal runner.

Historical accounting is incomplete. The preserved ledgers establish:
- 14 counted calls before the completion goal
- the completion goal's 2
- goal-2's 1, for 17 in all
- priced charges of $0.000351541 before the completion goal, $0.000300784 in it and $0.000691482 in goal-2

They omit earlier goal-drafting calls, some council charges and measured active time. Do not report 17 as an exhaustive lifetime total or fabricate the missing values. The recorded 17-call baseline is kept separately from new calls. With the six proposed here, the recorded counted total may reach 23; that is not an assertion that every historical invocation is known. Preparation of this approval has dispatched no models.

GSTACK_GOAL_LEDGER is set only on the command of a real dispatch. It is never exported for test or receipt commands, which append fixture entries to whatever ledger it names.

The candidate's receipts at 675bb13 and its CI evidence are history for the repaired head, not substitutes for it. Recompute version changes against the actual target and base: never freeze a version number independently of that comparison, and never move the marketplace top-level version on the goal branch.

No implementation, goal-run start or merge is authorized until this approval's exact head is approved and its normal readiness checks pass. This folder may be prepared and its approval PR published before then, through the app identity. The goal PR itself is the approval vehicle; there is no additional live-doc or design-review round requested here.

## Non-goals
- any new feature beyond the preserved delivery outcome, the five original repairs and repairs (6)-(8)
- the 14 embedded-instruction follow-ups reported by goal-2's review
- editing goal_spend.py, goal_guard.py, goal_envelope.py, workflows, CODEOWNERS, hooks, package manifests or any other gate-owned file
- relaxing a merge, approval, coverage, data, deployment, holdout, review or unknowns gate
- changing frozen independent goal tests, rewriting prior records, laundering failing receipts or inventing historical measurements
- consolidating experimental pilot transports, adding a model transport, database, service or agent framework
- STIGViewer changes or the separate startup-readiness patch
- the five-task everyday-work evaluation and the two live interruption demonstrations, which remain separately approved real changes

## Scenarios
- Given a packet whose selected artifact is fresh but whose attested prerequisite or embedded pointer binding is stale, then the executor refuses before any worker starts and creates no run directory
- Given a review fix round that names a ledger run at the new head, then the round's record carries that run with head_matches true and receipt_verified true, and the retained packet and earlier round bytes are unchanged
- Given a ledger receipt that belongs to an older head or another repository, then it reports head_matches false or receipt_verified false and cannot clear the candidate
- Given a delivery whose change has used its three review passes, then a fourth reservation under a new review ID is refused and a restart preserves the count
- Given GitHub has accepted the exact-head merge and the process exits before record-release, then a fresh process discovers that merge, records it once, synchronizes the required clean checkout, and reports complete without issuing a second merge request
- Given a required checkout that is dirty, on an unexpected branch, divergent, on the wrong host, or unavailable, then its tracked and untracked bytes, status and Git metadata are unchanged and the delivery reports sync_pending naming that checkout and reason
- Given a goal whose declared release companion is not merged and recorded, then delivery_status is not complete
- A second merge request for a change GitHub has already merged must never happen
- A repeated authorization question for an already authorized step must never happen
- A dirty required checkout being stashed, reset, cleaned, switched or overwritten to appear synchronized must never happen
- record-release performing or requesting a merge must never happen

## Goal tests
- `tests/test_delivery.py::Delivery.test_stale_binding_refuses_before_dispatch` (outcome)
- `tests/test_delivery.py::Delivery.test_fix_round_refreshes_head_bound_ledger` (outcome)
- `tests/test_delivery.py::Delivery.test_wrong_head_or_tampered_receipt_cannot_clear_head` (outcome)
- `tests/test_delivery.py::Delivery.test_replacement_review_cannot_reset_attempt_limit` (outcome)
- `tests/test_delivery.py::Delivery.test_resume_after_accepted_merge_records_once` (outcome)
- `tests/test_delivery.py::Delivery.test_dirty_required_checkout_preserved_and_pending` (outcome)
- `tests/test_delivery.py::Delivery.test_release_companion_required_before_complete` (outcome)
- `tests/test_delivery.py::Delivery.test_record_release_never_merges` (invariant)

## Allowed paths
- plugins/gstack-execution/scripts/graph_context.py
- plugins/gstack-execution/scripts/test_graph_context.py
- plugins/gstack-execution/scripts/task_graph.py
- plugins/gstack-execution/scripts/test_task_graph.py
- plugins/gstack-execution/scripts/goal_delivery.py
- plugins/gstack-execution/scripts/test_goal_delivery.py
- plugins/gstack-execution/scripts/goal_run.py
- plugins/gstack-execution/scripts/test_goal_run.py
- plugins/gstack-execution/scripts/peer_review.py
- plugins/gstack-execution/scripts/test_ledger_evidence.py
- plugins/gstack-execution/scripts/test_ci_run_paths.py
- plugins/gstack-execution/commands/gstack-build.md
- plugins/gstack-execution/commands/gstack-goal.md
- plugins/gstack-execution/skills/gstack-execution/references/task-graph-contract.md
- plugins/gstack-execution/skills/gstack-execution/references/peer-review-contract.md
- plugins/gstack-execution/README.md
- plugins/gstack-execution/.claude-plugin/plugin.json
- .claude-plugin/marketplace.json
- docs/evidence/gstack-delivery/*
- docs/evidence/gstack-delivery/registry/*

## Spend cap
$50

## Provider budgets
- openrouter: $50

## Max calls
8

## Max items
1

## Max review rounds per item
3

## Stop conditions
- a new goal test regression, an unexplained required-check regression, or the same required check failing after two repair cycles without a resolved cause
- any change reaching hooks or another CODEOWNERS path, or a required repair needing a gate-owned file changed
- the marketplace's top-level version moves on the goal branch
- the cumulative charged time carried from the completion goal and goal-2, plus this goal's measured active work, reaches ten hours; preserve partial delivery state and report the remaining work
- a seventh new counted call in this goal would be required, or the unchanged native 80% Max calls gate stops; after the sixth call only already-authorized non-model delivery actions may continue if all existing gates permit; preserve all releases already completed
- the existing $40 provider/spend early stop is reached or any provider budget is unreadable
- the implementation item needs a fourth pass, the whole-goal checkpoint a third or the companion a second; replacement ids do not reset the respective allowances
- the evidence preflight before a dispatch fails and can't be corrected within scope; a round is never dispatched on evidence the preflight refuses
- main has moved at start beyond this approval's own merge
- a repair would need a file outside the allowed paths or a gate-owned file, including goal_guard.py
- the local demonstration can't pass without weakening a check
- authority, budget, checkpoint counts, candidate/base identity, deployed environments or required GitHub gate observations are unreadable, changed without authority or contradictory
- a gate, review or CI check would need bypassing, an approval impersonated, or a false claim of evidence accepted for delivery to proceed
- a deploy to any environment other than goal-holdout, beyond the repository's existing build triggers, would be required; any newly discovered deployment environment is Dorian's call before starting
- no permitted recovery exists within scope and the remaining budget

## Pre-mortem
- reviewing the old b321160 alone misses defects carried into the executor; review the complete repaired candidate including the 4b32cda changes
- a merged PR at the right head but wrong target is marked verified; require repository, PR, candidate and target identity before persisting any progress
- green check names survive after their PR/base bindings are discarded; retain and verify the binding metadata
- a stopped or held run records a release or synchronizes even though its merge path would refuse; apply authority guards to every advancing action
- a fresh process ignores a persisted uncertain merge request and sends it again; verify restart behavior while GitHub still reports the outcome as unconfirmed
- a cached synced flag masks new edits or branch movement; re-observe checkout identity, branch, cleanliness and required merge ancestry before completion
- a review asks for evidence of a future merge; keep pre-merge acceptance and post-merge delivery verification separate
- a retrospective log is relabelled as a receipt or a chronological unknown is declared resolved without proof; preserve source hashes and the explicit limits
- the full runner fails because a worktree lacks declared dependencies; establish the environment and retain both the failed and later passing receipts
- model selection/council calls or preparation calls are omitted; record every invocation and distinguish counted from priced calls
- a required checkout is dirtied while work occurs elsewhere; leave it untouched and report sync_pending rather than forcing completion
- an unrelated main change defeats a previously passing version/envelope check; validate the actual proposed target/base before every review and gated merge
- a round is spent by evidence the dispatcher refuses (the predecessor's round 3); run the dispatcher's own validation as a preflight before every round, and name only runs at the reviewed head
- test commands write fixture calls into the goal's spend ledger; never export GSTACK_GOAL_LEDGER outside a real dispatch command
- the goal-to-main merge passes its gate but delivery planning or record-release can't recognize it; the local demonstration must exercise that path before review
- a Git inspection fails silently and reads as clean; check every exit code before reading its output
- one repository's merge satisfies another's checkout, or only the newest of several required merges is checked; bind each checkout to its repository and check every required merge
