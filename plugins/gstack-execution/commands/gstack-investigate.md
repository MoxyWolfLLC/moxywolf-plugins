---
description: Root cause debugging with hypothesis testing
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, Agent
argument-hint: [bug-description-or-error-message]
---

Systematic debugging with root cause investigation. Adapted from gstack's `/investigate` methodology. Iron Law: no fixes without root cause.

Read the gstack-execution skill for context.

## The Bug

$ARGUMENTS

If no arguments provided, ask the user to describe the bug: what they expected, what happened instead, and any error messages.

## Phase 1: Root Cause Investigation

1. **Collect symptoms.** What error messages, stack traces, or unexpected behavior? Read relevant log files or error outputs.
2. **Read affected code paths.** Use Grep and Read to trace the code from the entry point (route handler, event listener, function call) through to where the bug manifests.
3. **Check recent changes.** Run `git log --oneline -20` and `git log --oneline --all -- {affected files}` to see what changed recently in the area.
4. **Attempt reproduction.** Describe the exact steps to reproduce. If the codebase has tests, check if any existing tests cover this path.

## Phase 2: Pattern Analysis

Match the bug against common patterns:
- **Race condition** — concurrent state mutation, missing locks, async timing
- **Nil/null propagation** — unchecked return values, optional chaining gaps
- **State corruption** — shared mutable state, stale cache, event ordering
- **Integration failure** — API contract change, schema mismatch, auth expiry
- **Configuration drift** — env var mismatch, feature flag state, dependency version
- **Stale cache** — CDN cache, browser cache, server-side cache invalidation

Check if similar bugs were fixed before: `git log --all --grep="fix" -- {affected files}`

## Phase 3: Hypothesis Testing

For each hypothesis:
1. State the hypothesis clearly: "The bug occurs because X happens when Y."
2. Identify what evidence would CONFIRM or REFUTE the hypothesis.
3. Check for that evidence (read code, check logs, trace data flow).
4. Score confidence: confirmed / refuted / inconclusive.

**3-Strike Rule:** After three failed hypotheses, STOP and escalate. Say: "I've tested three hypotheses and none explain the root cause. Here's what I've ruled out and what I'd investigate next with more context."

## Phase 4: Implementation (only after root cause confirmed)

1. Fix root cause only. Minimal diff.
2. Write a regression test that fails without the fix and passes with it.
3. Run any existing test suite to verify no regressions.
4. Commit atomically: one commit for the fix, one for the test.

## Phase 5: Verification & Report

```
DEBUG REPORT
════════════
Symptom: {what the user saw}
Root Cause: {what actually went wrong}
Fix: {what was changed and why}
Evidence: {how we confirmed the root cause}
Regression Test: {test file and what it covers}
Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
```

If status is BLOCKED or NEEDS_CONTEXT, explain exactly what's missing and what the user should do next.
