# Goal mode acceptance, 2026-10-03 to 2026-10-04

Goal mode's production acceptance: a real goal run from start to merge with nothing from Dorian but his approvals. Every action was made as `moxywolf-agent[bot]`. Run state and records: `goal-runs/<id>/` in the vault.

**Result: passed on the third real goal, `vault-review-list-2` (PR #158, merged as `ed6c398`).** It went from start through two items, finalize, propose, a fresh review and every goal check, with Dorian's touches limited to approving the goal folder, pasting the holdout and approving the goal PR. The two goals before it each stopped at a gap, and each gap is fixed and merged.

## The runs

| Goal | Outcome | What it found |
|---|---|---|
| `cloud-review-survives` (#138) | stopped | Docker mounts the goal-tests sandbox's `/tmp` noexec, so its stub `gitleaks` could never run and the tests failed on any code; `baseline` passed only because it ran on the host (fixed in #140). Item 1 moved the marketplace's top-level version on the goal branch while main moved the same line, so the goal PR failed the version check and every sync conflicted; and the runner finished as soon as the goal tests passed, dropping the untested item 2 (both fixed in #145). The work landed through an ordinary reviewed PR (#144). |
| `vault-review-list` (#146) | stopped by `goal-holdout` | Both fixes held: item 2 was built after the tests passed, and the sync passed the version check in goal mode. The holdout failed with nothing anyone could diagnose (fixed in #153: a failing holdout now names its failing tests and error lines, never its source). Re-run, it showed the cause: an empty folder's message went to standard error, and the holdout read the plan's "says so" as standard output. |
| `vault-review-list-2` (#154) | **complete** | Same feature, the plan naming the stream for every message, a fresh holdout. Items #155 and #156 (Codex, `no_blocking_findings`), finalize #157, goal PR #158: `goal-holdout`, `goal-tests`, `goal-envelope` and `tests` green, a fresh review with no blocking findings, Dorian's approval at the head. Spend $0 metered, 3 counted calls. The release bump (#159) moved the top-level version afterwards. |

## Fixed along the way

- #140: the goal-tests sandbox's `/tmp` allows exec, and `baseline` runs inside that container (GO-002.2).
- #145: every plan item is built; the goal never moves the top-level version; the release bump moves it (GO-003.3, GO-004.1).
- #148: `test_version_bump.py`'s historic ranges run outside goal mode.
- #153: a failing holdout is diagnosable (GO-003.6).

## Agent errors, for the record

- Merging #145 before #146 left #146 behind main, which dismissed Dorian's approval; deleting its branch during cleanup briefly closed it. Restored and reopened; Dorian re-approved.
- Merging two approved PRs in sequence under the up-to-date rule always costs one re-approval; merge order now accounts for it.

## Open

- The version check fails on push runs of `build/*` and `goal-finalize/*` branches. It blocks nothing, because pull-request runs are the required ones, but it shows red.
- `tests.yml` still has no explicit read-only `permissions` block (Dorian's, since the bot can't edit workflows).
- The flaky timing test `test_task_graph.py::test_diamond_overlaps_and_preserves_all_findings`.
