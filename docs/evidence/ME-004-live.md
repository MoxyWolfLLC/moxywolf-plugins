# ME-004.4: live council deliberations, 2026-11-11

Two real deliberations through `plugins/council/scripts/openrouter_dispatch.py` at this branch's head, on Dorian's Mac: medium lineup, voting protocol, the stage prompts from `skills/deliberation-engine/references/stage-prompts.md`, one question about when prompt caching pays in a one-shot pipeline. The numbers are each job's `cache` entry from its stage's `_summary.json`, with `prompt_tokens` from the same response. The six summaries are committed unedited beside this file as `ME-004-live/run<1|2>-stage<1|2|3>-summary.json`; the per-job result files, which hold the models' answers, are not.

## Run 2 (the one to read)

Claude's output cap was raised to 10,000 tokens so its answers weren't empty. Chairman: Strategist (`anthropic/claude-sonnet-5`).

| Job | Model | Asked for caching | Prompt tokens | cache.read | cache.write |
|---|---|---|---|---|---|
| s1-analyst | `openai/gpt-4o` | no | 200 | 0 | 0 |
| s1-challenger | `google/gemini-2.5-flash` | no | 227 | 0 | 0 |
| s1-strategist | `anthropic/claude-sonnet-5` | yes | 320 | 0 | 0 |
| s1-synthesist | `x-ai/grok-4.3` | no | 395 | 128 | 0 |
| s2-analyst | `openai/gpt-4o` | no | 4196 | 0 | 0 |
| s2-challenger | `google/gemini-2.5-flash` | no | 3143 | 0 | 0 |
| s2-strategist | `anthropic/claude-sonnet-5` | yes | 5634 | 0 | 5632 |
| s2-synthesist | `x-ai/grok-4.3` | no | 4384 | 128 | 0 |
| s3-chairman | `anthropic/claude-sonnet-5` | yes | 7820 | 0 | 7818 |

Reading, by criterion 4, for the three jobs that asked for caching:

- `s1-strategist`: reads and writes both 0 on a 320-token prompt. Below the cache minimum (1,024 tokens for Sonnet 5).
- `s2-strategist`: read 0, write 5,632. A cost with no saving.
- `s3-chairman`: read 0, write 7,818. A cost with no saving.

Across the deliberation Claude wrote 13,450 tokens to the cache and read none. A 5-minute cache write is billed at 1.25 times the input price, so the extra is a quarter of the input price on those tokens, well under a cent here, with nothing saved. Every other job is reported as caching not requested; Grok's 128 cached tokens are its provider's own automatic caching.

Reported to Dorian: in the session of 2026-11-11 at about 19:51 PT ("Claude wrote 13,450 tokens to the cache and read none back"), and in pull request #298's description. He had not replied when this was written.

Nothing was switched off. Whether to set `"cache": false` in the deliberation engine's jobs is Dorian's call.

## Run 1 (kept, thin)

Claude ran at the documented 3,000-token cap, spent all of it thinking and returned empty content at stage 1, so it took no part in stages 2 and 3. Chairman: Synthesist (`x-ai/grok-4.3`).

| Job | Model | Asked for caching | Prompt tokens | cache.read | cache.write |
|---|---|---|---|---|---|
| s1-analyst | `openai/gpt-4o` | no | 200 | 0 | 0 |
| s1-challenger | `google/gemini-2.5-flash` | no | 227 | 0 | 0 |
| s1-strategist | `anthropic/claude-sonnet-5` | yes | 320 | 0 | 0 |
| s1-synthesist | `x-ai/grok-4.3` | no | 395 | 128 | 0 |
| s2-analyst | `openai/gpt-4o` | no | 2743 | 0 | 0 |
| s2-challenger | `google/gemini-2.5-flash` | no | 1406 | 0 | 0 |
| s2-synthesist | `x-ai/grok-4.3` | no | 2880 | 128 | 0 |
| s3-chairman | `x-ai/grok-4.3` | no | 3390 | 128 | 0 |

The only job that asked for caching was the 320-token stage 1 prompt: below the cache minimum. The empty answer at the documented cap is a separate defect in the Claude slot, not part of ME-004.

## Not shown

A deliberation where a cache read happens. No stage in the current pipeline sends the same prefix to Claude twice within five minutes, so none is expected.
