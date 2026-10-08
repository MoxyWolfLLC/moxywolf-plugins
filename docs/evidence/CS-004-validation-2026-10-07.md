# CS-004 and CS-006 validation record (CS-004 criteria 9 and 10, CS-006 criterion 7)

Recorded 2026-10-07 at `c6ff9bd`. Review `20261007-155817-a6a9289-sqfgr1r2` (F3) said the packet claimed test-first order and passing checks that the reviewer had no way to see. This file puts the commit order, the check ledger's own lines and the captured output in the repository. The commit that adds or updates this file changes only `docs/evidence/`.

A limit, stated up front: this is the builder's copy. The review dispatcher doesn't put ledger lines or commit history on the review surface itself, so a reviewer can read these records and can't yet check them against the source. Closing that is a change to `peer_review.py`, which is outside CS-004.

Everything here ran on the Release Owner's Mac from the repository root, through `plugins/gstack-execution/scripts/check_ledger.py run --repo . -- <command>`. Nothing was pushed, so there is no CI run.

This record was refreshed after the second pass of 2026-10-07 (commits `8ea1772` to `6c3cae8`, on Dorian's ruling about disagreements). The first pass's lines are unchanged. It was refreshed again after the second review's first round (`b2d0853` to `233571f`), and again after CS-006, the claim check, was built on the same branch (`ce29358` on).

## Commit order

`git log --reverse origin/main..HEAD`, oldest first, before this file's own commit:

```text
af86735 2026-10-07T15:16:21-07:00 design: CS-004 dedicated Sales and Marketing departments
ebc29ef 2026-10-07T15:18:51-07:00 test: CS-004 structure checks for the Sales and Marketing departments
a2648b8 2026-10-07T15:23:09-07:00 CS-004: Sales and Marketing department agents under the Chief of Staff
efe43c3 2026-10-07T15:33:56-07:00 CS-004: tighten the head skills and the memo rules after scenario run 1
4ccc93d 2026-10-07T15:40:10-07:00 CS-004: every gated action is a written request, and reading customer data counts
8fb2c69 2026-10-07T15:45:09-07:00 CS-004: close the two gaps scenario run 3 left open
a6a9289 2026-10-07T15:52:01-07:00 CS-004: record the four scenario evaluations (criterion 9)
882688f 2026-10-07T16:02:35-07:00 CS-004: a spent approval can't be reused, and an open field isn't ready (review F1, F2)
6ae75f7 2026-10-07T16:15:51-07:00 CS-004: record scenario runs 5 and 6 and the validation evidence (review F3)
05c5e68 2026-10-07T16:19:56-07:00 CS-004: the checks come before the memo (review F4, F5)
6129585 2026-10-07T16:31:01-07:00 CS-004: record scenario run 7 and refresh the validation record
d3b3019 2026-10-07T16:37:41-07:00 design: record where CS-004's review ended
8ea1772 2026-10-07T16:48:51-07:00 design: CS-004 takes Dorian's ruling on disagreements, and ten departments everywhere
dffdea8 2026-10-07T16:49:13-07:00 tests: CS-004.8 as amended, the disagreement rules are written down
0334f99 2026-10-07T16:50:13-07:00 CS-004: a Sales or finance disagreement doesn't wait for security, and finance's goes by the bookkeeper
d090420 2026-10-07T16:57:36-07:00 design: CS-004.8 says when a result goes to security, and that a result keeps its scope
225aafb 2026-10-07T16:57:36-07:00 CS-004: a memo's facts take one of two forms, and a result keeps its scope
389d7fd 2026-10-07T17:08:37-07:00 design, tests: CS-004.8 names a memo's sources, and the bookkeeper's question carries no customer detail
6c3cae8 2026-10-07T17:08:37-07:00 CS-004: a memo's facts have four sources, and the bookkeeper's question leaves the customer out
32dfca1 2026-10-07T17:15:16-07:00 Merge main: XE-035 is done (PR #191)
9678db5 2026-10-07T17:16:06-07:00 CS-004: record scenario runs 8 to 13, the three places brought to ten, and where the item stands
9026bd2 2026-10-07T17:22:16-07:00 CS-004: refresh the validation record after the second pass
b2d0853 2026-10-07T17:27:55-07:00 tests: review F7, the absence rule is written down in both head skills and the manual
b09d63c 2026-10-07T17:27:56-07:00 CS-004: an unknown state isn't reported as a fact (review F7)
e05131c 2026-10-07T17:39:10-07:00 tests: the last read before a department returns, and the Chief of Staff's send-back for a claim past its source
233571f 2026-10-07T17:39:10-07:00 CS-004: a department rereads its result before returning it, and the Chief of Staff sends back a claim that goes past its source (review F7)
8b066b0 2026-10-07T17:50:17-07:00 CS-004: record scenario runs 14 and 15 and where the second review stands
a42941a 2026-10-07T17:56:07-07:00 CS-004: refresh the validation record after the second review's first round
ce29358 2026-10-07T19:33:45-07:00 design: declare CS-006, the claim check, and record the go-ahead to publish CS-004
67a6134 2026-10-07T19:34:29-07:00 tests: CS-006, the claim check, before the script exists
c350893 2026-10-07T19:36:24-07:00 CS-006: claim_check.py, a line is a quotation found in its source or a labeled line
f8b1b33 2026-10-07T19:37:24-07:00 tests: CS-006.5, .6 and .9, the claim check is in the manual, /cos, both head skills and the README
3d783e0 2026-10-07T19:37:24-07:00 CS-006: what the Chief of Staff gives Dorian, and what Sales and Marketing return, is written in the claim check's forms
3eb2765 2026-10-07T19:53:09-07:00 design: CS-006.3, a source is quoted and never retold
7974100 2026-10-07T19:53:09-07:00 tests: CS-006.3, a line that retells a source fails
7ebed7b 2026-10-07T19:53:33-07:00 CS-006: a source is quoted under its label and never retold
d8ac083 2026-10-07T20:07:24-07:00 design: CS-006.3, an inference can't say what nobody did
9423097 2026-10-07T20:07:24-07:00 tests: CS-006.3, an inference that says what nobody did fails
8c4f669 2026-10-07T20:07:55-07:00 design: CS-006.7 follows criterion 3, a recorded sentence that says what nobody did fails under an inference label too
c00128a 2026-10-07T20:07:55-07:00 CS-006: an inference or a proposal can't say what nobody did
4cb8051 2026-10-07T20:08:34-07:00 design: CS-006.3, the nobody rule is a shape and not three words
d0e74ce 2026-10-07T20:09:20-07:00 CS-006: the nobody rule matches a shape, so honest lines pass
bdc12fe 2026-10-07T20:19:20-07:00 CS-004, CS-006: record scenario runs 16 and 17 and where both items stand
b049379 2026-10-07T20:25:04-07:00 tests: CS-006, a quotation starts and ends on a word, and a source can't take a built-in label's name
c6ff9bd 2026-10-07T20:25:23-07:00 CS-006: a quotation matches whole words, and a source can't be named after a built-in label
```

The test commit, `git show --stat ebc29ef`. It touches the two test files and nothing else:

```text
ebc29ef test: CS-004 structure checks for the Sales and Marketing departments

 plugins/chief-of-staff/tests/test_roster.py        |  15 +-
 .../chief-of-staff/tests/test_sales_marketing.py   | 176 +++++++++++++++++++++
 2 files changed, 190 insertions(+), 1 deletion(-)
```

The first implementation commit is `a2648b8`, after it.

The second pass kept the same order, twice. `dffdea8` added `test_the_disagreement_rules_are_written_down` and nothing else, and the manual change it checks is the next commit, `0334f99`. `389d7fd` added one more assertion to that test, alongside the design correction it follows, and the manual change is the next commit, `6c3cae8`. The second review's fixes did the same: `b2d0853` adds two assertions and `b09d63c` the text they look for, then `e05131c` adds two more and `233571f` the text. `git show --stat dffdea8`:

```text
dffdea8 tests: CS-004.8 as amended, the disagreement rules are written down

 plugins/chief-of-staff/tests/test_sales_marketing.py | 17 +++++++++++++++++
 1 file changed, 17 insertions(+)
```

## The ledger's lines for this branch

Copied from `<review root>/ledger/MoxyWolfLLC-moxywolf-plugins/build/CS-004-sales-marketing-departments.jsonl`. One line per check run. The head is the commit checked out when the run was recorded.

| Run | Started (UTC) | Head | Exit | Clean tree throughout | Command |
|---|---|---|---|---|---|
| `7202862f68ef` | 2026-10-07T22:18:43Z | `af86735` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `b6fff0827638` | 2026-10-07T22:18:43Z | `af86735` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `ea5909d742a4` | 2026-10-07T22:23:09Z | `a2648b8` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `c315da59b9b9` | 2026-10-07T22:23:09Z | `a2648b8` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `30ab376f20a5` | 2026-10-07T22:24:09Z | `a2648b8` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `ca0a33cff599` | 2026-10-07T22:35:39Z | `4ccc93d` | 0 | no | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `8bd360cfc821` | 2026-10-07T22:41:58Z | `8fb2c69` | 0 | no | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `3b50304b9cb6` | 2026-10-07T22:52:01Z | `a6a9289` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `f4da9b6a4d7f` | 2026-10-07T22:52:01Z | `a6a9289` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `2883ad1738b1` | 2026-10-07T22:52:01Z | `a6a9289` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `485b7a5cf87c` | 2026-10-07T22:52:02Z | `a6a9289` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `ed056af574f0` | 2026-10-07T23:02:36Z | `882688f` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `97892066f49b` | 2026-10-07T23:11:32Z | `882688f` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `7fc5c39a10c9` | 2026-10-07T23:11:32Z | `882688f` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `bb1b233e7b8f` | 2026-10-07T23:11:32Z | `882688f` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `be5eae326261` | 2026-10-07T23:15:51Z | `05c5e68` | 0 | no | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `1f98d76c784c` | 2026-10-07T23:24:13Z | `05c5e68` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `4910037ee1d1` | 2026-10-07T23:30:39Z | `05c5e68` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `0aa141f16c0e` | 2026-10-07T23:30:40Z | `05c5e68` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `f622fe3371ed` | 2026-10-07T23:30:40Z | `05c5e68` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `b3128b40fee7` | 2026-10-07T23:31:14Z | `6129585` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `0f7984ef93d0` | 2026-10-07T23:49:13Z | `dffdea8` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `9e9359a41760` | 2026-10-07T23:50:14Z | `0334f99` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `e7c0cc10e29a` | 2026-10-08T00:02:07Z | `225aafb` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `c321aaef3e9f` | 2026-10-08T00:08:37Z | `389d7fd` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `cb841b70cd88` | 2026-10-08T00:08:37Z | `6c3cae8` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `693d2043d01b` | 2026-10-08T00:16:06Z | `9678db5` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `cf85b51098ac` | 2026-10-08T00:16:06Z | `9678db5` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `6b770b371386` | 2026-10-08T00:16:17Z | `9678db5` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `26393c72353b` | 2026-10-08T00:16:07Z | `9678db5` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `9a24834d795a` | 2026-10-08T00:27:55Z | `b2d0853` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `54281170d6a0` | 2026-10-08T00:27:56Z | `b09d63c` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `f5ea50d8ec55` | 2026-10-08T00:39:10Z | `e05131c` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `51a4823b9ceb` | 2026-10-08T00:39:10Z | `233571f` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `37749b3f0a08` | 2026-10-08T00:50:18Z | `8b066b0` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `af905b0cc3c2` | 2026-10-08T00:50:18Z | `8b066b0` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `1be0d827c3ed` | 2026-10-08T00:50:18Z | `8b066b0` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `8935d72f523f` | 2026-10-08T00:50:19Z | `8b066b0` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `fd05e4d28254` | 2026-10-08T02:34:29Z | `67a6134` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `1f1baa1030ed` | 2026-10-08T02:36:24Z | `c350893` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `aea34e40b564` | 2026-10-08T02:37:05Z | `9e0bf5d` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `63ba7ed24a84` | 2026-10-08T02:37:24Z | `f8b1b33` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `38ba570ab7d1` | 2026-10-08T02:37:25Z | `3d783e0` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `0cf3947ad87b` | 2026-10-08T02:46:21Z | `3d783e0` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `3e2dc46ff1f8` | 2026-10-08T02:53:09Z | `7974100` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `032560e45c78` | 2026-10-08T02:53:33Z | `7ebed7b` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `75dfb9a2ee6c` | 2026-10-08T02:53:36Z | `7ebed7b` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `afb08a0cf15b` | 2026-10-08T02:59:29Z | `7ebed7b` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `1066f0433399` | 2026-10-08T03:07:24Z | `9423097` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `577c18d38741` | 2026-10-08T03:07:55Z | `c00128a` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `8af1346dade3` | 2026-10-08T03:07:58Z | `c00128a` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `48305e4a3683` | 2026-10-08T03:08:57Z | `7bdee46` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `68f686f716cd` | 2026-10-08T03:09:00Z | `7bdee46` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `43452f28b0e3` | 2026-10-08T03:09:00Z | `7bdee46` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `b41fcc19025c` | 2026-10-08T03:09:20Z | `d0e74ce` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `b4973e728a40` | 2026-10-08T03:09:23Z | `d0e74ce` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `70e215fe1396` | 2026-10-08T03:09:23Z | `d0e74ce` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `20ec105e072c` | 2026-10-08T03:11:00Z | `d0e74ce` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `1d583f43d7cd` | 2026-10-08T03:17:14Z | `d0e74ce` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `c5ed6015fee1` | 2026-10-08T03:19:20Z | `bdc12fe` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `882498f0a6f7` | 2026-10-08T03:19:20Z | `bdc12fe` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `9cb68f10a755` | 2026-10-08T03:19:20Z | `bdc12fe` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `3833299d2cdc` | 2026-10-08T03:19:23Z | `bdc12fe` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `0ada6c5414ce` | 2026-10-08T03:19:24Z | `bdc12fe` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |
| `eb2eccc27fb2` | 2026-10-08T03:25:04Z | `b049379` | 1 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `06835895bb5f` | 2026-10-08T03:25:23Z | `c6ff9bd` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_roster.py` |
| `ff39d5f3b84d` | 2026-10-08T03:25:23Z | `c6ff9bd` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_sales_marketing.py` |
| `da760f37adff` | 2026-10-08T03:25:23Z | `c6ff9bd` | 0 | yes | `python3 plugins/chief-of-staff/tests/test_claim_check.py` |
| `5c0af9f0e0ca` | 2026-10-08T03:25:27Z | `c6ff9bd` | 0 | yes | `python3 plugins/gstack-execution/scripts/skill_packaging.py --json` |
| `c7419960b548` | 2026-10-08T03:25:27Z | `c6ff9bd` | 0 | yes | `python3 plugins/gstack-execution/scripts/run_all_tests.py` |

Three things to read these lines by:

- The first two exit-1 lines are the baseline. They ran with the new test files in the working tree on top of `af86735`, before any implementation. Those files were committed unchanged as `ebc29ef`.
- The two later exit-1 lines, at `dffdea8` and `389d7fd`, are the second pass's failures before the fix. Each ran at a commit that held the new assertion and not yet the manual text it looks for, with a clean tree. The same command exits 0 at `0334f99` and at `6c3cae8`. The exit-1 lines at `b2d0853` and `e05131c` are the same thing for the second review's fixes, and the command exits 0 at `b09d63c` and `233571f`.
- CS-006 kept the order three times. `test_claim_check.py` exits 1 at `67a6134`, where the test file exists and the script doesn't, and 0 at `c350893`, which adds the script. `test_sales_marketing.py` exits 1 at `f8b1b33`, which adds assertions for the instruction text, and 0 at `3d783e0`. `test_claim_check.py` exits 1 again at `7974100`, which adds the retelling test, and 0 at `7ebed7b`.
- One line names a commit that no longer exists. The `test_sales_marketing.py` run at `9e0bf5d` exited 1. That commit's message said two tests failed, where the run's own output said one, so the commit was amended to quote the output. The amended commit is `f8b1b33`, with the same tree, and the same command was run again there. Three exit-0 lines at `7bdee46` are the same case. That commit's message described the nobody rule as narrowed one step further than its code yet was, so the code and test were completed and the commit amended to `d0e74ce` before it left this machine, and the tests were run again there. And `test_claim_check.py` exits 1 at `9423097`, which adds the test for that rule, and 0 at `c00128a`. It exits 1 once more at `b049379`, which adds the whole-word and reserved-name cases, and 0 at `c6ff9bd`.
- The same two commands exit 0 from `a2648b8` on. A failure in this ledger closes only when the same command passes, so that's what cleared them.
- Three `run_all_tests.py` lines are marked "no" under clean tree. Each started on one commit and was recorded on the next, because instruction text was edited and committed while it ran. Don't lean on those three. Every line marked "yes" started and finished at the head shown with nothing edited.

## Baseline: the tests fail before the departments exist

`test_roster.py`:

```text
FAIL: test_sales_and_marketing_are_departments (__main__.Roster.test_sales_and_marketing_are_departments)
Ran 3 tests in 0.003s
FAILED (failures=1)
examined roster of 8 in plugins/chief-of-staff/skills/chief-of-staff/SKILL.md against 8 department agents under plugins/; non-department routes not examined
```

`test_sales_marketing.py`:

```text
FAIL: test_each_package_carries_every_required_file (__main__.Packages.test_each_package_carries_every_required_file)
FAIL: test_manifest_marketplace_and_readme_agree (__main__.Packages.test_manifest_marketplace_and_readme_agree)
FAIL: test_no_package_shadows_the_installed_namespaces (__main__.Packages.test_no_package_shadows_the_installed_namespaces)
FAIL: test_local_skill_and_source_references_resolve (__main__.Routing.test_local_skill_and_source_references_resolve)
FAIL: test_the_chief_of_staff_routes_ten (__main__.Routing.test_the_chief_of_staff_routes_ten)
FAIL: test_the_expanded_return_contract_and_the_gate_are_written_down (__main__.Routing.test_the_expanded_return_contract_and_the_gate_are_written_down)
Ran 6 tests in 0.003s
FAILED (failures=6)
```

## At `c6ff9bd`

`test_roster.py`:

```text
Ran 3 tests in 0.003s
OK
examined roster of 10 in plugins/chief-of-staff/skills/chief-of-staff/SKILL.md against 10 department agents under plugins/; non-department routes not examined
```

`test_sales_marketing.py`:

```text
Ran 7 tests in 0.008s
OK
examined 12 required files across 2 packages
examined 3 packages against 47 marketplace entries: manifest, entry and README versions
examined 2 local skills in 2 packages; the installed sales: and marketing: catalogs are another marketplace's and are not examined
examined 2 distinct local references in 13 files, and 2 head skills' sources and specialists; whether a sales: or marketing: skill is installed is resolved at run time and not examined here
examined a roster of 10, the manual's two boundary sections, the dispatcher and the README
examined the manual's review and memo sections and the dispatcher
examined 9 return fields and the gate's wording in 2 head skills, 2 GOVERNANCE.md files and the manual
```

`test_claim_check.py` (CS-006):

```text
Ran 11 tests in 3.058s
OK
examined a document of structure only and an empty one: both fail, because nothing was examined
examined curly quotes, emphasis marks in the source, and two quotations joined by 'and'
examined the wrong source, a changed word, an ellipsis and an unknown source
examined 5 lines that retell a source, one of them recorded in run 16, and 4 that only refer to one
examined 4 lines that say what nobody did, three of them recorded in runs 16 and 17, and 9 that don't
examined 6 recorded sentences: each fails bare and as a bullet; labeled as an inference, the two that say what nobody did still fail and the other four pass
```

`skill_packaging.py --json` (232 packages on `main`, plus the two new head skills):

```text
examined: 234 packages, checks: 234, failed: 0, gate: PASS
```

`run_all_tests.py`, last lines:

```text
PASS  plugins/gstack-execution/scripts/version_bump.py --selftest
PASS  plugins/gstack-execution/scripts/vocab_check.py --selftest

examined 75 checks: 75 passed, 0 failed
```

`version_bump.py --base origin/main --head HEAD`:

```text
version bump: PASS, range origin/main..HEAD (67328b6..c6ff9bd), 43 changed file(s), examined 3 plugin(s): chief-of-staff, marketing-department, sales-department
```

`check_ledger.py open-issues`:

```text
0 open issues
```

## Not run

- No CI run. Nothing was pushed, which is the approved delivery boundary.
- No installed run. The two packages aren't installed anywhere, so no live `/cos` dispatched them.
- These are structure checks and a packaging check. What the agents do is in `CS-004-scenarios-2026-10-07.md` and `CS-004-scenarios-round-2-2026-10-07.md`.
- That the bookkeeper's name appears nowhere in this repository was checked by hand at this revision (a case-insensitive search of the working tree for his first name and his firm's name found no file). No test can check it without spelling the name.
