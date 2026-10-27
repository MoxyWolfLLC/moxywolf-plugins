## Serves
Eleventh objective: goal mode

## Outcome
Deliver the preserved Gstack delivery implementation through the existing gated merge route, release recording, marketplace update and synchronization of the required Mac checkout. Repair the five identified delivery defects together; correct the acceptance evidence without rewriting history. A PR, a passing review, an implementation merge, or an old checkout-sync flag is not completion.

This successor was requested by Dorian on 2026-10-27 at 14:07 PT. It authorizes exactly one more single-round implementation review for the unchanged item at 675bb133f7b63e8e17cad0a585a3b12c03501386. It changes the review-attempt allowance only. Scope, gates, the six-call stop and the ten-hour stop are unchanged and carried forward. It supersedes the execution authority of goal gstack-delivery-completion (PR #262, approved head 058667660071b2915499a371b4c4a1f3b288cb3d), not its records. That goal's item 1 review, 20261027-124210-98b5ed8-o897p6eo, stays exhausted at 3 of 3 rounds:
- Rounds 1 and 2 ran codex/gpt-6-astra. They returned blocking findings F1–F5. F1–F3 were verified resolved in round 2; F4 and F5 were left as evidence gaps.
- Round 3 was refused before the reviewer ran, because it named four ledger runs that were not at the reviewed head. No model call was made.

Its counter is not reset or reused. Its findings, dispositions, unknowns and round records are attached to the new review as history. The completion goal's spend-ledger correction (spend-correction-20261027, authorized by Dorian at 13:57 PT) stays as recorded.

Inputs: build branch build/gstack-delivery-completion-1-repair-release at 675bb13, unchanged, whose base is main at 292e75a4a8cc2a2bff6214f6d1ae93841d98920b. Its 13 acceptance criteria are unchanged, and the original inputs and evidence rules below still govern it. The original inputs were published candidate b3211600fdd32e95dffcce81773d9228cc41a1c6, its child 4b32cda9ea7f484da31b11e406e5f9d1c5c17498, and closeout ZIP sha256 ee274721e38f6abb27213c04fce5bdb0fb140bffb1f78d7672dc0e75b5f21041. No new implementation is authorized. If main has moved from 292e75a when this goal starts, stop and report rather than rebasing or rebuilding the item.

Before dispatch, preflight validates the complete evidence package without opening a round. It calls the dispatcher's own surface-building and evidence-validation functions, and each ledger run it names must be read, at the reviewed head and receipt-verified, exactly as the round requires. The four historical red receipts are presented through one current-head receipt. That receipt verifies each historical log against its ledger sha256 and reproduces it in full, naming its original commit, its failed exit code and its hash. Its success proves the integrity of that evidence, not that those historical tests passed. Only after preflight passes is the review dispatched, once, with --max-rounds 1. A rejected round or a blocking result ends the implementation checkpoint: the item is recorded as failed and the run stops.

The one implementation item includes the existing graph-context runtime, bounded review recovery, delivery executors, completion reporting and checkout synchronization already in those candidates, plus exactly these five repairs: (1) validate repository/PR/candidate/target identity before accepting a merge; (2) preserve and validate CI PR/current-base bindings; (3) refuse resume advancement for terminal or held runs; (4) consult persisted merge-request state across process restarts and re-observe an uncertain result instead of automatically resending; (5) re-observe every required checkout before marking delivery complete. Persisted declarations alone establish none of these facts.

Acceptance evidence is corrected in this approval. Keep the retrospective comparison labelled retrospective; never claim tests ran before implementation when they did not. The old per-test log is retained as historical evidence with its hash and limitations, not relabelled as a newly executed ledger receipt. A new, clearly dated and head-bound per-test run may substantiate the reconstruction, provided the baseline and test-file identities are verified; it must not replace or erase any failed receipt. Unknown 3107b5e1e958 is answered by the accepted retrospective label and stays unresolved as a chronological fact unless the existing tool legitimately records a narrower resolution. Its closure is not an acceptance criterion. All release gates, including any open-unknown gate, still apply.

Review acceptance is pre-merge: exact proposed PR identity and candidate/base, complete diff, current verified evidence, existing gates and the five repairs. Post-merge verification is separate: observe the exact reviewed head merged into the approved target, run record-release, then verify required synchronization and the release companion. No reviewer is asked to certify a future merge. Prior reviews and their findings are attached as history, never substituted for a fresh review of the repaired complete candidate.

Reuse goal-5's eight independently drafted goal tests byte-for-byte and its holdout hash. Their gpt drafter and gemini reading are preserved and identified as reused; no new reading is claimed. The additional five repair cases are implementation regression tests, not hand edits to the independent goal tests. The unseen holdout remains on the Mac; before publishing the approval PR, verify that the same opaque file can be made available outside the repository under this new goal id using a filesystem hard link, without printing, rewriting or re-drafting it, with its approved hash unchanged.

Authority and route: approval means Dorian's approving GitHub review at this folder's exact PR head, followed by goal_brief.py verify. Before starting, record the predecessor run as failed at item 1 with goal_run.py failed, under its own rule, giving its actual outcome; this ends its execution authority. Then start goal/gstack-delivery-completion-2 from then-current main. Open one pull request from the unchanged build branch at 675bb13 into goal/gstack-delivery-completion-2. Merge it only into the goal branch, after its exact-head cross-vendor review and required checks at that pull request. PR #263 is closed with a link to its successor, and its branch and records are preserved. Any main-to-goal synchronization uses a checked sync PR, never a push. Rerun goal tests after the item merge. Finalize the run record and holdout through the existing PR path; then a fresh whole-goal review and the required GitHub Actions goal-holdout/tests/goal-envelope/goal-tests precede the goal-to-main merge. Run record-release for each governed merge. Then make the declared marketplace top-level-version-only release companion PR into main, through its normal review, checks, merge and record-release. Act as the app, never Dorian. No admin bypass, gate exception, narrow-packet acceptance or coverage override is authorized.

This approval explicitly authorizes exactly one additional implementation review: one review id with one round for the unchanged candidate at 675bb13. It also keeps the predecessor's allowances of up to two passes for the whole-goal checkpoint and one for the marketplace companion, none of which has been used. All of these sit within the remaining counted-call aggregate below. The predecessors' spent review counts remain historical; they are not erased or presented as unused. The exhausted review keeps its id and count. This allowance is new authority for one round, not a reset of that review. A blocking or rejected implementation round ends the implementation checkpoint, and this approval permits no fix round after it. A finding in the whole-goal or companion checkpoint that is fixed within the approved scope needs no further routine permission; changed scope, gates or exhausted limits stop the run.

Required synchronization target only: /Users/doriancougias/GitHub/moxywolf-plugins, on Dorian's Mac, origin MoxyWolfLLC/moxywolf-plugins, branch main. Bind the actual Mac hostname and accepted remote spelling from that checkout in the delivery record before execution; do not assume the cloud host is the Mac. ~/Developer/moxywolf-plugins and ~/review-host-i050 are excluded. The required checkout was last observed clean on the candidate branch at b321160. An authorized operator may switch it to main only after confirming it is clean and preserving its candidate branch/ref; sync-checkout itself never switches branches. If it has become dirty, unavailable, divergent, wrong-host or otherwise ineligible, preserve it unchanged and report sync_pending. The implementation may be released while synchronization is pending, but delivery is not complete.

Limits carried forward, not reset: the ten active hours Dorian approved for the completion goal at 11:52 PT on 2026-10-27 remain the single limit across both goals. As of this folder's preparation, the completion goal's charged time totals 8,771 seconds (about 2.44 hours). That total is made up of:
- 1,303.562 s of approval preparation, of which 900 s is a labelled allowance rather than a measurement
- 42 s of publication
- 660 s of unmeasured publication handling, charged conservatively
- about 6,765 s of measured execution from 18:52:44Z to 21:11:09Z, net of 1,540 s of recorded waits

The active seconds spent preparing this successor are measured and added to that total. The approved run persists the cumulative total. Waiting time is reported separately. Approval, restart, a successor goal and replacement review ids never reset it.

At most four additional counted model calls: the six approved for the completion goal minus the two it used, codex/gpt-6-astra review rounds 1 and 2. They cover the one implementation review round, the whole-goal review and the companion review. Counted has the repository's existing goal_spend.py meaning: subscription calls and metered calls with no reported cost. This goal's spend ledger starts empty and records only its own calls. The predecessor's ledger, its two calls and its correction stay where they are. Max calls 6 below keeps the existing 80% gate from stopping non-model delivery actions immediately after the fourth authorized call. The separate, stricter authorization is four: refuse before a fifth new counted call in this goal, irrespective of the nominal native field. Neither five nor six calls is authorized; no gate implementation is changed or bypassed. Priced gateway/council calls still consume the metered budget, are all recorded individually with model/provider/cost, and are reported separately as total model invocations; this is not a promise of only six total model requests. Unknown-cost calls count. The existing $50 OpenRouter cap and $40 early stop are retained, and all new priced charges are measured. No unrecorded model dispatch is permitted, including during preparation or outside the goal runner.

Historical accounting is incomplete. The preserved ledgers establish:
- 14 counted calls before the completion goal
- the completion goal's 2 counted calls
- priced charges of $0.000351541 before the completion goal, plus its $0.000300784 for one three-voice model_select council (19:41:25Z)

They omit earlier goal-drafting calls, some council charges and measured active time. Do not report 16 as an exhaustive lifetime total or fabricate the missing values. Maintain the recorded 16-call baseline separately from new calls. The prospective four-call stop corresponds to the same 20 recorded counted calls as before; it is not an assertion that every historical invocation is known. Preparation of this successor has dispatched no models.

Before each future call, verify both its checkpoint allowance and the aggregate remaining budget, reserving at least one counted call each for the still-required whole-goal and companion reviews. A new draft or unknown-cost scoring call consumes that same four-call allowance; it is not outside budget. The packet's model selection may need the existing priced decider council again. That consumes the metered budget, is recorded individually and is not a counted call. Do not invoke extra models solely to prepare this unchanged-test approval.

GSTACK_GOAL_LEDGER is set only on the command of a real dispatch. It is never exported for test or receipt commands, which append fixture entries to whatever ledger it names.

The candidate's receipts at 675bb13 (full runner b469cbfffe51, focused suites, the eight goal tests 97ee3dbfaffe) and its CI there (tests, goal-envelope and goal-tests all success) are evidence to re-observe, not to assume. Recompute version changes against the actual target/base: never freeze a version number independently of that comparison, and never move the marketplace top-level version on the goal branch.

No implementation, goal-run start or merge is authorized until this approval's exact head is approved and its normal readiness checks pass. This folder may be prepared and its approval PR published before then, through the app identity. The goal PR itself is the approval vehicle; there is no additional live-doc or design-review round requested here.

## Non-goals
- any new feature beyond the preserved delivery outcome and the five listed repairs
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
6

## Max items
1

## Max review rounds per item
1

## Stop conditions
- a new goal test regression, an unexplained required-check regression, or the same required check failing after two repair cycles without a resolved cause
- any change reaching hooks or another CODEOWNERS path, or a required repair needing a gate-owned file changed
- the marketplace's top-level version moves on the goal branch
- the cumulative charged time carried from the completion goal plus this goal's measured active work reaches ten hours; preserve partial delivery state and report the remaining work
- a fifth new counted call in this goal would be required, or the unchanged native 80% Max calls gate stops; after the fourth call only already-authorized non-model delivery actions may continue if all existing gates permit; preserve all releases already completed
- the existing $40 provider/spend early stop is reached or any provider budget is unreadable
- the evidence preflight fails, or the single implementation round is rejected or returns blocking findings; record the item as failed and stop, with no fix round
- main has moved from 292e75a when the goal starts, or the candidate at 675bb13 would need any change
- a whole-goal checkpoint needs a third pass or the companion a second; replacement ids do not reset the respective allowances
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
- a round is spent by evidence the dispatcher refuses (the predecessor's round 3); run the dispatcher's own validation as a preflight before the single round, and name only runs at the reviewed head
- test commands write fixture calls into the goal's spend ledger; never export GSTACK_GOAL_LEDGER outside a real dispatch command
