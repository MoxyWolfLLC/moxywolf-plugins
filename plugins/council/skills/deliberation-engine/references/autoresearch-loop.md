# Autoresearch Optimization Loop

**The agent instructions file** — tells the optimization agent how to modify, test, and iterate on Council's prompts. This is the third file in the 3-file autoresearch pattern:

| File | Role | Mutable? |
|------|------|----------|
| `stage-prompts.md` | Editable artifact — the prompts being optimized | Yes (by this loop) |
| `eval-criteria.md` | Locked criteria — how to score modifications | No (change only deliberately by the user) |
| `autoresearch-loop.md` | Agent instructions — this file | No (defines the optimization process) |

---

## Overview

The optimization loop improves Council's deliberation quality by systematically modifying prompts, testing them against benchmark queries, and keeping only changes that improve evaluation scores. One variable at a time, modify → test → score → keep or revert → repeat.

**Inspiration lineage:** Karpathy's autoresearch (630 lines, 700 experiments, 20 optimizations in 2 days) → OpenAI Self-Evolving Agents Cookbook (GEPA reflective prompt evolution) → Council prompt optimization.

---

## Prerequisites

Before running the loop:

1. **Minimum 3 rated deliberations** in pattern memory. The loop needs benchmark queries with known outcomes. If insufficient, abort with: "Need at least 3 rated deliberations to optimize. Rate your next few results with feedback."

2. **Current baseline score.** Run the current (unmodified) prompts against the benchmark set and score against all 5 eval criteria. This is the baseline that modifications must beat.

3. **Optimization budget.** Check the user's monthly optimization budget in config (default: $2/month). Each experiment costs one deliberation (~$0.08-0.12). Calculate max experiments = budget / avg_cost.

---

## The Loop

### Step 1: Select Benchmark Queries

Read pattern memory and select 3-5 benchmark queries following the rules in `eval-criteria.md`:
- Must have user_rating
- Diverse categories
- Mix of positive and negative outcomes
- Lock the benchmark set for the entire optimization run

### Step 2: Establish Baseline

Run the current `stage-prompts.md` against all benchmark queries:
- Execute a full deliberation for each benchmark query
- Score each against the 5 eval criteria
- Compute baseline pass rate = total passes / (5 × N benchmarks)
- Record this as the baseline

### Step 3: Propose a Modification

Select one prompt variable to modify. The optimization proceeds through these variables in priority order (highest impact first):

**Priority 1 — Synthesis prompts** (Stage 3):
- Chairman instructions for voting protocol
- Chairman instructions for consensus protocol
- How to handle disagreements
- How to structure the final answer

**Priority 2 — Review prompts** (Stage 2):
- Ranking criteria and weights
- Anonymization format and instructions
- Anti-bias instructions (length bias, self-preference)
- How to identify strongest points and gaps

**Priority 3 — Role prompts** (Stage 1):
- Analyst role definition and approach
- Strategist role definition and approach
- Challenger role definition and approach
- Synthesist role definition and approach

**Priority 4 — Protocol selection thresholds:**
- When to use voting vs. consensus
- Confidence thresholds for protocol switching

**Modification strategies** (rotate through these):

1. **Sharpen:** Make the instruction more specific. Replace vague guidance ("be thorough") with concrete actions ("list at least 3 specific examples").

2. **Constrain:** Add a guardrail. "Do not exceed 500 words" or "You must take a clear position, not hedge."

3. **Expand scope:** Add a dimension the prompt currently ignores. "Also consider the operational cost of this approach" or "Factor in team skill fit."

4. **Restructure:** Change the output format. Move from prose to structured JSON, or add required sections.

5. **Remove:** Strip instructions that may be causing over-constraint. Sometimes less guidance produces better results.

Only modify ONE variable per experiment. Multi-variable changes make it impossible to attribute improvement.

### Step 4: Test the Modification

1. Create a temporary copy of `stage-prompts.md` with the single modification applied
2. Run the modified prompts against all benchmark queries
3. Score each benchmark against the 5 eval criteria
4. Compute modified pass rate

### Step 5: Evaluate

Compare modified pass rate against baseline:

| Outcome | Action |
|---------|--------|
| Pass rate improved by > 5% | **KEEP** — commit the change to `stage-prompts.md` |
| Pass rate within ±5% AND C1 improved | **KEEP** — synthesis superiority is the highest-value criterion |
| Pass rate within ±5% AND C1 unchanged | **SKIP** — modification had no meaningful effect, revert |
| Pass rate decreased by > 5% | **REVERT** — modification made things worse |
| Any criterion drops to 0% | **REVERT** — never sacrifice a criterion entirely |

### Step 6: Log the Experiment

Write an experiment record to pattern memory's optimization log:

```json
{
  "experiment_id": "opt_20260328_001",
  "timestamp": "2026-03-28T16:00:00Z",
  "variable_modified": "synthesis_voting_chairman",
  "modification_type": "sharpen",
  "description": "Added instruction to cite specific model contributions by label",
  "baseline_pass_rate": 0.72,
  "modified_pass_rate": 0.80,
  "criteria_delta": {
    "C1_synthesis_superiority": +0.20,
    "C2_peer_review_accuracy": 0.00,
    "C3_multi_model_breadth": +0.10,
    "C4_confidence_calibration": 0.00,
    "C5_budget_compliance": 0.00
  },
  "decision": "keep",
  "cost_usd": 0.45,
  "benchmark_count": 5
}
```

### Step 7: Iterate or Stop

**Continue** if:
- Optimization budget remaining > cost of one experiment
- There are untested variables in the priority list
- The last 3 experiments weren't all "skip" or "revert" (diminishing returns check)

**Stop** if:
- Budget exhausted
- All priority variables have been tested
- 3 consecutive experiments produced no improvement (plateau detected)
- User interrupts

When stopping, report the summary (see Output Format below).

---

## Output Format

After the loop completes, present the optimization summary:

```
## Council Optimization Complete

**Experiments run:** 12
**Budget used:** $1.08 of $2.00
**Baseline pass rate:** 68%
**Final pass rate:** 84%

### Changes Kept (4):
1. Synthesis (voting): Added "cite which council member contributed each key insight" → C1 +20%, C3 +10%
2. Review (voting): Added "penalize responses that match your own reasoning style" → C2 +15%
3. Analyst role: Changed "quantify where possible" to "include at least 2 specific numbers or metrics" → C1 +10%
4. Challenger role: Added "if the obvious answer is correct, explain what alternatives you evaluated" → C3 +5%

### Changes Reverted (5):
1. Synthesist role: Tried adding "draw from at least 2 external domains" → C5 failed (responses too long, exceeded budget)
2. Consensus chairman: Tried restructuring to JSON output → C1 -15% (synthesis quality dropped)
3. ...

### Changes Skipped (3):
1. Strategist role: Minor wording change → no measurable effect
2. ...

### Recommendations:
- Run optimization again after 20 more deliberations for fresh benchmark data
- Consider adding "compliance_security" benchmarks — only 1 rated deliberation in that category
```

---

## Safety Rails

1. **Never modify `eval-criteria.md`** — the eval criteria are the objective function. If the agent optimizes the criteria, it's grading its own homework.

2. **Never modify `autoresearch-loop.md`** (this file) — the optimization process itself is fixed.

3. **Always revert on failure.** If a modification fails, restore the exact previous version of `stage-prompts.md`. Never leave prompts in a partially modified state.

4. **One variable at a time.** Multi-variable changes are forbidden — they make it impossible to learn which change caused the effect.

5. **Budget is hard.** Never exceed the optimization budget, even if the last experiment looks promising. The user can always run another optimization cycle later.

6. **Benchmark stability.** Use the same benchmark set across the entire optimization run. Don't cherry-pick benchmarks that favor a modification.

7. **Preserve prompt identity.** Modifications should refine, not replace. The Analyst should still be an analyst; the Challenger should still challenge. Optimization should improve how each role executes, not blur the roles together.
