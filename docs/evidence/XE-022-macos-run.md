# XE-022 criterion 3: macOS run with a reviewer installed

Captured by script on the Release Owner's Mac. Nothing below was typed by hand.

- Commit checked out when captured: `da5ab35ae050721d9b2805b1f8f565265a3f4053`. The commit that adds this file changes nothing else, so the code a reviewer sees is the code that ran. Check it byte for byte with `shasum -a 256` against the list below.
- Host: macOS-26.6.2-arm64-arm-64bit-Mach-O, Python 3.14.3
- `shutil.which("codex")`: `/Users/doriancougias/.nvm/versions/node/v24.15.0/bin/codex`
- `codex --version`: `codex-cli 0.154.0`

## `python3 plugins/gstack-execution/scripts/test_dispatch_collect.py` (exit 0)

```
ok  test_a_dispatch_whose_process_is_killed_reports_failed_not_pending_forever
ok  test_a_relative_path_entry_cannot_carry_a_reviewer_past_the_fixture
ok  test_a_reviewer_that_exits_nonzero_completes_the_round_as_unavailable
ok  test_collect_before_dispatch_says_so
ok  test_dispatch_refuses_a_second_review_in_flight
ok  test_dispatch_returns_immediately_then_collect_completes
ok  test_the_unavailable_fixture_hides_an_installed_reviewer

7 passed

```

## SHA-256 of every repository file the run executed or read

```
0d814bb08c44d67f5135846f4fc05afef2ea88b6c9671c67e8f6eac7572b500b  plugins/gstack-execution/scripts/governance.py
366aba311cd51066351cb7d90077fca84d99b1cefd177803c3070e9fbb41bbad  plugins/gstack-execution/scripts/peer_review.py
066cda49df90edf6b19b03cb16acc4412deb6f8fb53c00569797edccbc386dd8  plugins/gstack-execution/scripts/test_dispatch_collect.py
598f3d985765a7670d8830e0fb18c0b09e830c7ea4487f98bb6f7114608ba16f  plugins/gstack-execution/skills/gstack-execution/references/vocabulary.json
```

## round-1.json of the unavailable case

```json
{
 "outcome": "review_unavailable",
 "reviewer": null,
 "model": null,
 "transport": null,
 "error": "no independent reviewer available for builder claude; tried codex, gemini, openrouter-gpt, openrouter-gemini, openrouter-deepseek (a cli entry needs its binary on PATH, an api entry needs its credential)"
}
```
