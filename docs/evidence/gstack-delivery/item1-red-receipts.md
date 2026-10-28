# Item 1 (completion goal): test-first red receipts

New red/green evidence for the five repairs and the round-1 fixes. It is distinct from the
accepted historical retrospective comparison in `item2-fail-before-per-test.historical.md`.

The receipts are check_ledger runs on branch `build/gstack-delivery-completion-1-repair-release`.
Each one was recorded at the commit that added the regression tests, before the repair commit.
The review round attaches these runs with `--ledger-run`, so the dispatcher re-reads each receipt
and checks it against the sha256 on its ledger line. This file only names them.

| ledger run | head (tests only) | command | exit | receipt sha256 | bytes |
|---|---|---|---|---|---|
| bea795ea0a9a | 1d1d5fd | `python3 test_goal_delivery.py` | 1 | 8772b620b135149fc93ef489db7b5db41e8b778a6936835be0391431f01570f2 | 6953 |
| d75fa1c5da3e | 1d1d5fd | `python3 -m unittest -v test_goal_run` | 1 | b524fb6b95d3e3708a714fc625f8ea3825acb251ef7364cbc2820a032f33f3d6 | 12477 |
| e11127aa12f1 | 3273eb2 | `python3 test_goal_delivery.py` | 1 | 14465f684888cec8795b4d44f9ea1359254d3fabe3debdf95ddace05c0b2edf5 | 3991 |
| 4dbd6acff7d3 | 3273eb2 | `python3 -m unittest -v test_goal_run` | 1 | 388ed55cd78cd9c879a7b6e98adfc59040e236f7fc508643f56980db955677a0 | 14771 |

- `1d1d5fd` adds the r1–r5 tests, and `5338ef0` repairs them.
- `3273eb2` adds the f1–f3 tests, and `82fd034` fixes them.
- The green runs are the head-bound receipts of the same commands at the reviewed head.

## Check bindings (criterion 3)

`next_action` checks provenance through `goal_guard.checks_green` in
`plugins/gstack-execution/scripts/goal_guard.py`, and that check is unchanged by this item.
`goal_guard.checks_green` compares each goal check's external_id with
`goal_checks.provenance` (`plugins/gstack-execution/scripts/goal_checks.py`). It refuses a check
bound to another PR or an old base, and it refuses a check bound to nothing.
Its own tests are in `plugins/gstack-execution/scripts/test_goal_guard.py`, around lines 187-190.
