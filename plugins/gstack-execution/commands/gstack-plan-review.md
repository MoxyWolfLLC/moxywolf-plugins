---
description: Pre-code plan-hardening loop — a bounded cross-model argument over PLAN.md before any code exists; real Codex when available, Claude adversarial fallback
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent, AskUserQuestion
argument-hint: [rounds=N] [plan=<path>] [task description ...]
---

Run an **iterative adversarial review of an implementation plan** before a single line of code is written. Where `/gstack-codex-review` challenges the commit you just made, this command challenges the plan you're *about* to build — the cheapest point in the whole pipeline to catch a wrong approach.

It is the front half of the DR-004 gate pair: `/gstack-plan-review` hardens the plan before build; `/gstack-verify` checks the implementation against the plan after. Both are read-only reporters against the artifact under review — they inform, they never gate.

Read the gstack-execution skill for context, then `references/plan-review-protocol.md` for the full loop protocol — both engines use it as the single source of truth.

Raw slash-command arguments: `$ARGUMENTS`

## Core constraints

- **No code during the loop.** The plan is the only file that changes, and only Claude changes it. Code is written only after the human approves the converged (or deadlocked-and-arbitrated) plan.
- **The critic never edits.** Real Codex runs read-only every round; the Claude-fallback critic is a fresh-context subagent with no Write access to the repo.
- **Bounded always.** The loop terminates at `MAX_ROUNDS` no matter what. A flagged deadlock is a legitimate outcome — surface the unresolved disagreement rather than manufacturing an approval.

## Step 0: Resolve inputs

Parse `$ARGUMENTS`:

- `rounds=N` → `MAX_ROUNDS` (default **5**).
- `plan=<path>` → `PLAN_FILE` (default `PLAN.md` at the repo root). If the file already exists, treat it as the draft to harden; skip drafting in Step 1.
- Remaining text is the task being planned. No task and no existing plan → ask one question to get the task, then proceed.

`LOG_FILE` is `PLAN-REVIEW-LOG.md` next to the plan. Echo the resolved values in one line before starting.

## Step 1: Claude drafts the plan (builder role)

Do real planning: read the relevant code, surface the decisions and tradeoffs. Write `PLAN_FILE` with these sections — the contestable choices named explicitly so the critic has something to bite:

```markdown
# Plan: <task>
_Round 0 — initial draft_

## Goal
## Approach            (numbered, concrete steps)
## Key decisions & tradeoffs
## Risks / open questions
## Out of scope
```

Initialize `LOG_FILE` with the task, the engine (from Step 2), and `MAX_ROUNDS`. Show the user the plan and say it's going to adversarial review.

## Step 2: Detect the engine

Same detection as `/gstack-codex-review`:

```bash
command -v codex >/dev/null 2>&1 && codex login status >/dev/null 2>&1 && echo "codex-ready" || echo "claude-fallback"
```

- **codex-ready** → real cross-model review. Follow the real-Codex mechanics in `references/plan-review-protocol.md` exactly (read-only sandbox flags, explicit thread id, stdin EOF redirect, timeout ceiling) — they are load-bearing, not ceremony.
- **claude-fallback** → the expected path in the Cowork sandbox. Each round's critic is a **fresh-context subagent** (Agent tool) given only `PLAN_FILE`, `LOG_FILE`, and read access to the repo — never this session's conversation. The builder must not grade its own work.

State the engine to the user before Round 1.

## Step 3: The loop

For `ROUND` in `1..MAX_ROUNDS`, per the protocol reference:

1. Send the plan to the critic with the round's review prompt. The critic reports **every finding it has, each tagged with severity** — material (would change the build) or minor (worth noting) — and ends with exactly one verdict line: `VERDICT: APPROVED` or `VERDICT: REVISE`.
2. Append the critique verbatim to `LOG_FILE` under `## Round <n> — critic`.
3. On `APPROVED` → Step 4 (converged).
4. On `REVISE` → Claude arbitrates: incorporate the critiques that hold, reject the ones that don't **with a logged reason for each rejection**. Revise `PLAN_FILE`. Append `### Builder response — what changed, what was rejected and why` to `LOG_FILE`. Continue.
5. Real-Codex path: resume the same critic session each round so it remembers its prior objections and checks only whether they're addressed. Claude-fallback path: give the fresh critic the full `LOG_FILE` so settled points aren't re-litigated.

## Step 4: Resolution (the human gate)

**Converged:** present the final plan, a three-bullet summary of what the argument improved, and the round count. Ask whether to implement now, revise further, or stop. Code only on a yes.

**Deadlocked (cap hit without APPROVED):** do not pretend it converged. List each objection the critic still holds and the builder's counter-position, side by side, and hand the tie to the human. Their call gets recorded in `LOG_FILE` as the final entry.

Either way, `LOG_FILE` is the deliverable — the whole argument, round by round. Reference it from the eventual commit or PD/DR if the plan's decisions warrant one.

## After the build

When implementation lands, `/gstack-verify` closes the pair: it checks the built code against this same `PLAN_FILE` and flags where the implementation drifted. Mention it at handoff.

## Restraint layer (ponytail)

A plan can be over-engineered before any code exists. The critic's first lens is the YAGNI ladder from the `ponytail` skill — does each planned piece need to exist at all — before it argues about how the pieces are built. Validation, error handling, security, and accessibility are never trimmed.
