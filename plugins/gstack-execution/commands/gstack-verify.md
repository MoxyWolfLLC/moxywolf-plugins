---
description: Post-build verification of the implementation against its plan/spec — the back half of the DR-004 gate pair; read-only, reports drift, never gates
allowed-tools: Read, Grep, Glob, Bash, AskUserQuestion
argument-hint: [plan=<path>] [--base <ref>] [focus ...]
---

Check what was **built** against what was **planned**. `/gstack-plan-review` (or `/product-analyze` on the product side) hardens the artifacts before build; this command closes the loop after: it reads the plan or spec, reads the implementation, and reports every place they disagree.

Anticipated by DR-004 as the paired follow-on to `/product-analyze` — analyze checks the artifacts against each other before build; verify checks the implementation against the spec after. Like its pair, this is a **read-only reporter**: it informs the decision to ship, fix, or amend the spec. It never blocks on its own authority.

Read the gstack-execution skill for context. Raw slash-command arguments: `$ARGUMENTS`

## Step 0: Resolve the spec and the scope

**The spec.** Parse `plan=<path>` from `$ARGUMENTS`. Default search order: `PLAN.md` at the repo root, then the most recent spec the session produced or was pointed at (a `/product-sprint` task plan, a PRD section, an engineering spec). If nothing resolves, ask one question: "verify against what?" — this command is meaningless without a reference artifact.

**The scope.** Default is the work since the plan: `--base <ref>` → `<ref>..HEAD`; otherwise infer the smallest range that contains the implementation (the branch, or the commits since `PLAN_FILE` was last modified). Any non-flag text is focus text — pass it through verbatim to sharpen the pass.

```bash
git log --oneline <RANGE>
git diff --stat <RANGE>
```

## Step 1: Build the claim table

Extract from the spec every **verifiable claim** about the implementation: each numbered step in the Approach, each named decision, each stated bound in Out of scope, each acceptance criterion. Number them (`C1..Cn`). Every claim gets checked — the table is the coverage guarantee; nothing is skipped as too small.

## Step 2: Verify each claim against the code

For each claim, read the implementation (diff first, then the files it touches) and assign one status:

| Status | Meaning |
|---|---|
| **BUILT** | Implemented as specified. Cite file:line. |
| **DRIFTED** | Implemented differently than specified. State the delta and, where discernible from the code, what the change bought — the human judges whether the drift was an improvement or an erosion. |
| **MISSING** | Specified but not implemented. |
| **EXTRA** | Implemented but nowhere in the spec (scope creep — or an undocumented necessity). |
| **UNVERIFIABLE** | Can't be established by reading code (needs a runtime check, external system, or human knowledge). Say what would verify it. |

Also run the spec's own proof, if it names one (a test command, an acceptance check): run it and record the verbatim result. A spec without a proof command gets that noted as a finding in its own right.

## Step 3: Report

```
GSTACK VERIFY
═════════════
Spec:    {path} ({claims} claims)
Range:   {RANGE}   Files: {N}   Lines: +{a} -{r}
Focus:   {focus text, or "none"}

BUILT: {n}   DRIFTED: {n}   MISSING: {n}   EXTRA: {n}   UNVERIFIABLE: {n}
Proof:  {command → pass/fail, or "spec names no proof"}
```

Then the claim table — every claim, its status, its evidence — followed by a findings section for each non-BUILT claim: what, where, why it matters, and the two honest remedies (change the code, or amend the spec in a logged decision). Severity-tag every finding; report all of them and let the reader filter — a drift that looks minor to the verifier may be the one the human cares about.

## Boundaries

- **Read-only.** No fixes, no spec edits. Route fixes to `/gstack-investigate` or a manual pass; route spec amendments to the owning artifact (PRD, sprint plan, or a PD/DR).
- **Drift is a report, not a verdict.** Implementations legitimately improve on plans. The command's job is to make every departure *visible and deliberate* instead of silent.
- **Not a code review.** Quality, security, and style live in `/gstack-review`, `/gstack-codex-review`, and `/gstack-cso`. This command answers exactly one question: is what we built what we said we'd build?
