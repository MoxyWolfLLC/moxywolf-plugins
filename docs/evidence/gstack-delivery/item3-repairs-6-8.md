# Goal gstack-delivery-completion-3, item 1: repairs 6-8, test-first, and the local demonstration

The repairs answer review `20261027-144404-675bb13-9l70pwgt` F1-F3 at `675bb13`.

The receipts below are check_ledger runs on branch `build/gstack-delivery-completion-3-1-final-path`. Byte copies of their logs are in this folder, each named by its ledger id, and they hash to the sha256 on their ledger lines.

## Red: the regression tests at the tests-only commits

| ledger run | head | command | exit | log sha256 |
|---|---|---|---|---|
| b59d4a36cec7 | a1b8509 | `python3 test_goal_delivery.py` | 1 | 90c8a98b076d443708e73065ad2662a207c8c8fe082eff2f891407f48304308a |
| 24f9453f5518 | a1b8509 | `python3 -m unittest -v test_goal_run` | 1 | 9b7ba49182071c72a7153db5b86c4e9bd6086907766c288ad89cc963eeb066a7 |
| 359313b991c4 | a01dc21 | `python3 test_goal_delivery.py` | 1 | 00a8cc204068b18f654cf77cba5a95ecee786c8ad7202114661c775eb4deb136 |
| c8995444d696 | a01dc21 | `python3 -m unittest -v test_goal_run` | 1 | 7e0ead5e7dfaa8d2d0391ce26291dbf933e68cb6590451e300978314c3646988 |

At `a01dc21`, each repair's cases fail at the defect:
- **Repair 6** (the goal change at its finalized head):
  - `test_g6_the_goal_change_merges_at_its_finalized_head_on_a_review_pinned_to_the_tested_head` errors.
  - `test_g6_the_goal_change_is_planned_at_its_finalized_head_on_a_review_of_the_tested_head` fails, because resume is pending at "not the candidate head".
  - `test_g6_record_release_records_the_goal_merge_at_its_finalized_head` fails, because record-release refuses "the exact reviewed head".
- **Repair 7** (a failed Git read): `test_g7_a_failed_git_inspection_is_never_read_as_clean_and_writes_nothing` fails for six of the seven failing Git reads. Fetch already failed closed.
- **Repair 8** (the checkout's repository and every merge): `test_g8_each_checkout_is_bound_to_its_repository_and_every_required_merge_is_checked` errors, and `test_g8_a_checkout_is_observed_against_every_merge_of_its_own_repository` fails, because only the newest merge was passed.

Two notes on the red runs:
- **The fixture fault at `a1b8509`.** The first test_goal_run red run, `24f9453f5518`, failed FinalizedRelease in its fixture: it read `release`'s exit code, which is nonzero by design. It did not fail at record-release. That run is kept. `a01dc21` fixes the fixture, and `c8995444d696` is the red run that shows the defect.
- **The g7 change after red.** The g7 test was changed after its red run, in `8efb263`. Synchronization reads the remote tip by fetch, not ls-remote, so the test no longer requires sync_checkout to fail on a failing ls-remote. Observation must still fail. The commit message says so.

## Green

The same commands pass at the repaired head. They are attached as head-bound receipts at the reviewed head.

## The local demonstration (e1d7cbb00b7f, at 6cb82cd)

`python3 -m unittest -v test_goal_run.EndToEndDemonstration` exited 0. Its log is `item3-demo-e1d7cbb00b7f.log`, sha256 6bb043b59fc7072183f0b45a1844778d6c6791e1c0d5ece76d29242dac194d53, 1304 bytes.

**What it uses.** Temporary repositories and a fake GitHub, labelled as such: a dict served to the runner in-process and to peer_review.py over a local HTTP server. Through these it runs the real goal_run, goal_delivery, goal_guard and peer_review code.

**What it runs, in order:**
1. finalize, as one commit on the tested head merged into the goal branch, and propose
2. a real peer_review open, round and release of the whole goal at the tested head, with a fake reviewer CLI giving a clean verdict
3. resume, which takes the GO-011.2 merge decision through the real act() and final_merge_allowed and merges the finalized head
4. record-release, which records it at the finalized head, against the tested reviewed head, as `agent_merge_autonomous` with the GO-011.2 relation
5. complete, which records the goal merge and leaves delivery open
6. the marketplace top-level-version companion, with its own review, merged outside the run and recorded by resume
7. synchronization, which fast-forwards the required checkout to a tip containing both merges, and the completion decision, which ends the run complete

**What it does not observe.** It observes no real merge, GitHub check or Mac checkout. Those are observed after the real merges.
