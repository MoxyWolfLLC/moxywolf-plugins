# XE-023 and XE-024: macOS runs

Captured by script on the Release Owner's Mac. Nothing below was typed by hand.

- Commit checked out when captured: `1165d5acc65abf57c387d47e16da6792bde04731`. The commit that adds this file changes nothing else. Check the code byte for byte with `shasum -a 256` against the list below.
- Host: macOS-26.6.2-arm64-arm-64bit-Mach-O, Python 3.14.3. `/tmp` resolves to `/private/tmp`.

## `python3 plugins/gstack-execution/scripts/endform_workflow.py --selftest` (exit 0)

Last line: `selftest ok`

## `python3 plugins/gstack-execution/scripts/run_all_tests.py` at this commit

```
examined 43 checks: 43 passed, 0 failed
```

## SHA-256 of the files these runs executed

```
c9b27b04b0dfb6b58566f4aa90abcf42a804cfa09d0e6a3739932bfee0560035  plugins/gstack-execution/scripts/endform_workflow.py
c06b464e3f5d305f4f46ae39c7cb5af7424bbc922c149dbce3adb733dd977aaf  plugins/gstack-execution/scripts/run_all_tests.py
68b7e94f1315da5f3ce0bf745a2554f2f78f64b1628e774e3c34a4069f070494  plugins/gstack-execution/scripts/test_task_graph.py
cc8756335f599737a497c74dcaf153dd2e0676db8a97eba5a8426c1b0c9acebc  plugins/gstack-execution/scripts/task_graph.py
366aba311cd51066351cb7d90077fca84d99b1cefd177803c3070e9fbb41bbad  plugins/gstack-execution/scripts/peer_review.py
```
