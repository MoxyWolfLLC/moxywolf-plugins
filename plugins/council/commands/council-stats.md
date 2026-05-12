---
description: View Council learning metrics and deliberation history
allowed-tools: Read
argument-hint: [summary | models | history | cost | optimization]
---

Display Council performance metrics from the persistent pattern memory file (`council-memory.json` in the workspace folder).

## How to read the data

1. Use the `Read` tool to load `council-memory.json` from the workspace directory
2. If the file doesn't exist, report: "No deliberation history yet. Run `/deliberate` to get started."
3. Parse the JSON and compute the requested metrics

## Subcommands

**If no arguments or `summary`:**

Show the quick dashboard. Compute from the memory file:

- **Total deliberations:** length of `deliberations` array
- **Total cost:** sum of all `cost_usd` values
- **Average cost:** mean `cost_usd`
- **Average latency:** mean `latency_ms`, displayed in seconds (e.g., "12.4s")
- **Average confidence:** mean `confidence`, displayed as percentage (e.g., "82%")
- **Top categories:** count deliberations per `query_features.category`, show top 3
- **Rating breakdown:** count each `user_rating` value (positive, negative, neutral, null)
- **Avg deliberation value added:** mean of all non-null `deliberation_value_added` scores, displayed as percentage
- **Router status:** check `routing_model`:
  - If `last_rebuilt` is null and `sample_size` < 20: "Learning ({N}/20 samples)"
  - If `last_rebuilt` is not null: "Active ({N} rules, accuracy: {X}%, last rebuilt {date})"
  - If sample_size is 0: "Not started — run deliberations to train"
- **Routing breakdown:** count deliberations by `routing_decision` (deliberate vs single_model) and `routing_source`

Format as a clean text dashboard — no raw JSON.

**If `models`:**

Show the model performance leaderboard from `model_performance`. For each model, display:

- Average rank (sorted best to worst)
- Win rate as percentage
- Chairman selections count
- Self-preference rate as percentage (flag models with rate > 15% with a warning marker)
- Best categories (avg rank <= 1.5 in that category)
- Worst categories (avg rank >= 3.5 in that category)

Format as a table. Highlight the top performer.

**If `history`:**

Show the last 10 deliberations from the `deliberations` array (most recent first). For each, display:

- Record ID
- Relative time ("2m ago", "1h ago", "yesterday")
- Query summary
- Chairman model (short name, e.g., "claude-sonnet-4" not the full path)
- Confidence as stars (★★★★★ = 0.9-1.0, ★★★★ = 0.7-0.89, ★★★ = 0.5-0.69, ★★ = 0.3-0.49, ★ = 0-0.29)
- Cost
- User rating indicator: (+) for positive, (-) for negative, (~) for neutral, blank for unrated

**If `cost`:**

Show cost breakdown:

- **Total spend:** sum of all `cost_usd`
- **This session:** sum of deliberations from today (match date in `timestamp`)
- **By model count:** group deliberations by length of `models_used`, show avg cost and count for each group (2, 4, 6 models)
- **Estimated stage split:** Stage 1 ~42%, Stage 2 ~38%, Stage 3 ~20% (these are estimates based on the cost model in deliberation-engine; individual stage costs aren't tracked separately)
- **Monthly spend:** sum costs for the current calendar month
- **Budget remaining:** if a budget cap is configured in `/council-config`, show remaining. If not configured, show "No budget cap set"

**If `optimization`:**

Show optimization history from the `optimization_log` array:

- **Last optimization run:** date, experiment count, baseline → final pass rate
- **Total optimization spend:** sum of all experiment `cost_usd` values
- **Changes kept / reverted / skipped:** counts by `decision`
- **Recent experiments (last 5):** experiment_id, variable_modified, modification_type, pass rate delta, decision
- **Current prompt version:** note that `stage-prompts.md` reflects all kept changes

If no optimization history exists, report: "No optimization runs yet. Rate 3+ deliberations, then run `/council-optimize` to start improving Council's prompts."
