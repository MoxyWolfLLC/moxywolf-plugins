---
description: Run the autoresearch optimization loop on Council's prompts
allowed-tools: Read, Write, Edit, Grep, Bash(echo:*), mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_SEARCH_TOOLS, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MULTI_EXECUTE_TOOL, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_MANAGE_CONNECTIONS, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_GET_TOOL_SCHEMAS, mcp__b51b4119-1c0a-4c04-ae60-0d11c60b2fe8__RUBE_REMOTE_WORKBENCH
argument-hint: "[--budget 2.00] [--dry-run] [--variable <name>]"
---

Run the Council autoresearch optimization loop. This systematically modifies Council's stage prompts, tests them against benchmark queries from pattern memory, and keeps only changes that improve evaluation scores.

**Prerequisites check (always run first):**

1. Read `council-memory.json` from the workspace
2. Count deliberation records that have a `user_rating` field
3. If fewer than 3 rated deliberations → abort with: "Need at least 3 rated deliberations to optimize. Rate your next few results with feedback (👍/👎 or a comment after any `/deliberate`)."
4. Verify the OpenRouter connection is active (same check as `/deliberate`)

**Parse flags:**
- `--budget 2.00` → max USD to spend on this optimization run (default: $2.00)
- `--dry-run` → propose modifications and show what would be tested, but don't execute any API calls. Useful for previewing the optimization plan.
- `--variable <name>` → only optimize a specific variable (e.g., `synthesis_voting_chairman`, `analyst_role`, `review_ranking_criteria`). Skips the priority order and targets this variable directly.

**Execution:**

Load the 3-file autoresearch pattern from `${CLAUDE_PLUGIN_ROOT}/skills/deliberation-engine/references/`:
- `stage-prompts.md` — the editable artifact (prompts being optimized)
- `eval-criteria.md` — locked criteria (how to score — **never modify this file**)
- `autoresearch-loop.md` — agent instructions (the optimization process — **never modify this file**)

Follow the 7-step loop defined in `autoresearch-loop.md`:

1. **Select Benchmark Queries** from pattern memory (3-5 rated deliberations, diverse categories)
2. **Establish Baseline** by running current prompts against benchmarks and scoring against 5 eval criteria
3. **Propose a Modification** — one variable at a time, following the priority order (unless `--variable` overrides)
4. **Test the Modification** — run modified prompts against the same benchmarks
5. **Evaluate** — compare pass rates, apply decision thresholds from `eval-criteria.md`
6. **Log the Experiment** — write to the `optimization_log` array in `council-memory.json`
7. **Iterate or Stop** — check budget, diminishing returns, and variable coverage

Each experiment runs a full deliberation for each benchmark query, so costs approximately (benchmark_count × $0.08-0.12) per experiment.

**If `--dry-run`:**
- Complete steps 1-3 only
- Show the benchmark set, baseline scores, and proposed first modification
- Show estimated cost for the full optimization run
- Do not make any API calls or modify any files

**After completion:**
Present the optimization summary as specified in `autoresearch-loop.md` (experiments run, budget used, baseline → final pass rate, changes kept/reverted/skipped, recommendations).

**Logging:**
All experiment records are written to `council-memory.json` under the `optimization_log` key. Each record includes: experiment_id, timestamp, variable_modified, modification_type, description, baseline/modified pass rates, criteria deltas, decision, cost, and benchmark count.

**Safety rails (enforced — no exceptions):**
1. Never modify `eval-criteria.md` or `autoresearch-loop.md`
2. Always revert `stage-prompts.md` on failed experiments
3. One variable per experiment
4. Hard budget enforcement — stop before exceeding
5. Same benchmark set across all experiments in the run
6. Preserve prompt identity — refine, don't replace
