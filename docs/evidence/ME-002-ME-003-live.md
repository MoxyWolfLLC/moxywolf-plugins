# ME-002 and ME-003: live runs, 2026-11-11

Both on Dorian's Mac, through the real code paths, not stubs.

## ME-002.6: spec_review.py caching

`spec_review.py run DESIGN.md --items ME-002,ME-003,ME-004` with the ME-002 code, Sonnet 5.5 executor and `claude-fable-5-2` advisor. Each item's turn paused on its advisor call and was resumed, so each run resent its prefix at least once. The records committed beside the doc (`reviews/spec-review/ME-00{2,3,4}.json`) carry:

| Item | cache.read | cache.write |
|---|---|---|
| ME-002 | 5,440 | 9,886 |
| ME-003 | 14,206 | 8,979 |
| ME-004 | 18,223 | 12,751 |

Later re-runs on this branch overwrite these records; the numbers above are quoted from the first run with the new code.

## ME-003.5: the Claude reviewer with an advisor

`peer_review.run_reviewer("claude", ...)` with Claude Code 2.1.310, default `GSTACK_CLAUDE_ADVISOR` (`fable`), a one-file surface and a one-field schema.

First run, at `5e3da12`: the review returned, but the round recorded the reviewer as `claude-fable-5-1`. The CLI's `modelUsage` listed the advisor with more output tokens than the Opus reviewer, and the old rule took the model with the most output as the one that ran. `seen` then read `null` ("share a model family"). That was a defect this item introduced: a reviewer below or beside the floor could be recorded in place of the one launched.

Fix: the reviewer is the `modelUsage` key that starts with the launched `--model`, falling back to the old rule only when none does; `seen` compares the advisor against the launched model. Test: `test_an_advisor_that_out_writes_the_reviewer_is_not_recorded_as_the_reviewer`.

Second run, after the fix:

```
MODEL claude-opus-5
ADVISOR {"requested": "fable", "seen": true, "seen_reason": null, "disabled_by_env": null}
USAGE {"input": 32323, "output": 1437, "cache_read": 123741, "total": 158153, "source": "claude modelUsage"}
```

The `fable` alias resolved to `claude-fable-5-1` in this CLI version.
