# XE-022 criterion 3: macOS run with a reviewer installed

Captured by script on the Release Owner's Mac. Nothing below was typed by hand.

- Code under test: `932eca71cffa7aa14db72c21a883e7498ba24509`
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
