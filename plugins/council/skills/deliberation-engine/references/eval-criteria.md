# Evaluation Criteria for Prompt Optimization

**STATUS: LOCKED** — This file defines the binary pass/fail criteria used to evaluate prompt modifications during the autoresearch optimization loop. It should only be changed deliberately after analyzing optimization outcomes, never by the optimization agent itself.

## Design Constraint

Exactly **5 binary (pass/fail) criteria**. Research across self-improving agent systems shows:
- Fewer than 3 → optimization agent finds loopholes
- More than 6 → agent games the checklist instead of genuinely improving
- Binary pass/fail outperforms scalar rubrics (1-5 ratings) for autoresearch loops

Each criterion is a yes/no question. A prompt modification passes if it scores >= 4/5 on a benchmark query set. If it scores 3/5 it's borderline (keep with low confidence). Below 3/5 → revert.

---

## The 5 Criteria

### C1: Synthesis Superiority
**Question:** Did the chairman's synthesis contain at least one substantive insight that does not appear in any individual Stage 1 response?

**How to evaluate:** Compare the synthesis against each individual response. Look for novel connections, integrated reasoning, or resolution of disagreements that no single model produced alone. A synthesis that merely summarizes or reorganizes existing points fails.

**Pass:** Synthesis contains identifiable novel insight(s)
**Fail:** Synthesis is a reorganized summary of existing responses

### C2: Peer Review Accuracy
**Question:** Did the peer review stage correctly identify the strongest individual response (as validated by the synthesis using it most heavily)?

**How to evaluate:** After synthesis, check which individual response the chairman drew from most. Compare that to the #1-ranked response from peer review. If they match (or the #1-ranked response is in the top 2 most-cited), it passes.

**Pass:** Peer review's top pick aligns with synthesis reliance
**Fail:** Peer review's top pick was not the primary synthesis source

### C3: Multi-Model Breadth
**Question:** Did the synthesis incorporate substantive content from at least 3 of the 4 (or N-1 of N) council models?

**How to evaluate:** For each model's Stage 1 response, check whether at least one of its key points appears in the synthesis (paraphrased or directly). A synthesis that only draws from 1-2 models fails — the whole point of the council is diverse perspectives.

**Pass:** 3+ models contributed identifiable content to the synthesis
**Fail:** Synthesis relies on fewer than 3 models

### C4: Confidence Calibration
**Question:** Was the confidence score directionally correct — high confidence when models agreed, low confidence when they diverged?

**How to evaluate:** Check the ranking spread from Stage 2. If models largely agreed on rankings (low std_dev) and the confidence score is >= 0.7, pass. If models strongly disagreed (high std_dev) and the confidence score is <= 0.5, pass. If confidence contradicts the actual agreement level, fail.

**Pass:** Confidence direction matches model agreement level
**Fail:** Confidence contradicts actual consensus/divergence

### C5: Budget Compliance
**Question:** Did the deliberation complete within the user's configured cost budget?

**How to evaluate:** Sum all API call costs. Compare against the `--budget` value (or default $0.15). Include all stages — collect, deep round if applicable, CI round if applicable, peer review, synthesis.

**Pass:** Total cost <= budget
**Fail:** Total cost > budget

---

## Scoring a Prompt Modification

During the optimization loop:

1. Run the modified prompts against 3-5 benchmark queries from pattern memory (queries where we have known outcomes and user ratings)
2. Score each benchmark against all 5 criteria
3. Compute the pass rate: passes / (5 criteria × N benchmarks)
4. Compare against the baseline pass rate from the current (unmodified) prompts

**Decision thresholds:**
- Pass rate improved by > 5% → **KEEP** the modification
- Pass rate within ±5% → **KEEP** only if C1 (synthesis superiority) improved (this is the highest-value criterion)
- Pass rate decreased by > 5% → **REVERT** the modification
- Any criterion drops to 0% pass rate across all benchmarks → **REVERT** regardless of overall improvement (no criterion should be completely sacrificed)

---

## Benchmark Query Selection

The optimization loop selects benchmark queries from pattern memory based on:

1. **Must have user_rating** — only queries where we know the user's assessment
2. **Diversity** — at least one query from each of the top 3 categories in the user's history
3. **Mix of outcomes** — include at least one "positive" and one "negative" rated deliberation so the optimization can learn from both successes and failures
4. **Stability** — use the same benchmark set across all experiments in a single optimization run (don't re-select mid-run)
5. **Minimum 3 queries** — if fewer than 3 rated deliberations exist, the optimization cannot run. Inform the user: "Need at least 3 rated deliberations to optimize. Rate your next few results with feedback."

---

## Changelog

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-28 | Initial criteria set — 5 binary criteria | Based on autoresearch research: binary outperforms scalar, 3-6 criteria is the sweet spot |
