---
name: release-owner-gate
description: |
  This skill should be used when Phase 4 (Diligence) of the 4D Blog Engine runs. It orchestrates the nonce-bound 5-stage Release Owner Gate from MoxyWolf's "Beyond the Prompt" whitepaper — Layer-1 deterministic preflight script + Layer-2 BLOCKING reviewer subagent with restricted tools + a CSPRNG nonce echo requirement + a 100-point rubric + an iteration cap + the human Release Owner sign-off. Triggers: "/4d-blog-engine:diligence", "run the release-owner gate", "score this draft", "is this ready to ship", "preflight my blog post". This is a specialist skill — invoked by the 4d-blog-engine orchestrator, not directly by the user in normal usage.
allowed-tools: [Read, Write, Edit, Bash, Glob]
user-invocable: false
---

# Release Owner Gate — Phase 4 orchestration

> **Read this when:** Phase 4 (Diligence) has been invoked. Phase 3's draft exists at `<piece>/03-discernment/draft.md`. Your job is to drive the 5-stage gate to either a clean `BLOCKING: false` (the Release Owner then signs by hand) or a documented escalation.

## STEP 0 — Load the rubric

Immediately Read `${CLAUDE_PLUGIN_ROOT}/references/release-owner-rubric.md` in full. This file defines:
- The 100-point scoring (5 categories: Content 30 / SEO+AEO 25 / E-E-A-T 15 / Voice match 15 / AI-citation 15)
- The exact reviewer output contract (NONCE line + scorecard table + Three highest-leverage claims + BLOCKING line)
- The nonce verification rule and iteration cap

Also Read `${CLAUDE_PLUGIN_ROOT}/references/ai-anti-patterns.md` since the Voice-match category scores against it.

## STEP 1 — Stage the draft into 04-diligence/

The draft from Phase 3 lives at `<piece>/03-discernment/draft.md`. Phase 4 operates on a **staged copy** at `<piece>/04-diligence/blog.md` — Phase 4 may revise this copy across iterations, but `03-discernment/draft.md` remains the canonical Phase-3 output. Copy:

```bash
mkdir -p <piece>/04-diligence
cp <piece>/03-discernment/draft.md <piece>/04-diligence/blog.md
```

If `<piece>/04-diligence/blog.md` already exists from a previous Phase-4 round, do NOT overwrite — that's the revision-in-progress.

## STEP 2 — Generate or verify the hero image

Phase 4's Stage 3 requires `<piece>/04-diligence/og-hero.png` and `<piece>/04-diligence/og-hero-prompt.md` (the AI-transparency artifact).

If the hero doesn't exist yet, invoke `frontier-founder/blog-post`'s hero-image generation flow:

1. Read the staged blog to identify its central metaphor.
2. Compose the hero prompt using FrontierFounder's fixed brand style spec (geometric/abstract, MoxyWolf palette, no text/logos/people, 16:9 ~1600x900).
3. **Show the prompt to the user via AskUserQuestion or as a markdown block, and ask for explicit approval BEFORE invoking image generation.** The whitepaper's Diligence ethos requires this transparency.
4. On approval, generate the image. Save to `<piece>/04-diligence/og-hero.png` and the prompt to `<piece>/04-diligence/og-hero-prompt.md`.

## STEP 3 — Rotate the nonce and dispatch the BLOCKING reviewer

For round 1, rotate the nonce (preflight.py auto-creates if absent; --rotate-nonce regenerates):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py \
  --piece <piece> --round 1 --rotate-nonce
```

Read the freshly-generated nonce from `<piece>/.review-nonce`. This is the 32-char hex string the reviewer subagent **must** echo verbatim in its scorecard.

Now dispatch the reviewer subagent. Use the Agent tool (or `Task` if available) with a **restricted-tools spec**: `Read, Write, Glob, Grep` only. **No Bash. No Edit.** The reviewer cannot execute or modify; only read and write its review.

The reviewer's prompt (substitute the placeholders):

```
You are the BLOCKING Release Owner reviewer for the 4D Blog Engine.

CONTEXT:
- Draft to review: <piece>/04-diligence/blog.md
- Rubric: ${CLAUDE_PLUGIN_ROOT}/references/release-owner-rubric.md
- Anti-pattern catalog: ${CLAUDE_PLUGIN_ROOT}/references/ai-anti-patterns.md
- AEO checklist: ${CLAUDE_PLUGIN_ROOT}/references/aeo-checklist.md
- Discourse sources: <piece>/03-discernment/sources-verification.md
- Phase 1 angle and earned secret: <piece>/01-delegation.md

YOUR TASK:
1. Read all four reference files in full.
2. Read the draft in full.
3. Read the sources-verification file to know which claims are [V]/[S]/[F].
4. Score the draft against the 100-point rubric. Be conservative — when uncertain, score lower.
5. List the three highest-leverage claims or numbers in the draft, each with its source URL.
6. Write your scorecard in the EXACT FORMAT in references/release-owner-rubric.md §"Reviewer output contract". Any deviation from the format causes the gate to reject the review.
7. Echo this nonce verbatim on the NONCE: line: <NONCE_HEX>
8. End with BLOCKING: true|false (reason). The verdict rules are in the rubric — pay attention to them.

Write your output to: <piece>/04-diligence/review.md
Do not write anywhere else. Do not execute anything. Read-and-write only.
```

## STEP 4 — Run preflight against the review

After the reviewer finishes, run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py \
  --piece <piece> --round <N>
```

The script reads `<piece>/04-diligence/blog.md` and `<piece>/04-diligence/review.md`, verifies the nonce echo, validates the scorecard format, parses the BLOCKING verdict and the total score, and runs Stages 1-5 of the gate. It writes `preflight-report.json` and `preflight-report.md`.

**Exit codes drive your next action:**

- **0 (pass):** The gate passed. Go to STEP 5 (Release Owner sign-off).
- **1 (retry):** A pre-review stage failed (capability / format / visual / asset_integrity), OR Stage 4 failed but round < 3. Surface the findings to the user, revise the staged blog (you may Edit `<piece>/04-diligence/blog.md` to address the findings), then go back to STEP 3 with `--round <N+1>` and `--rotate-nonce`.
- **2 (escalate):** Round 3 still failing. Stop. Tell the user: *"Release Owner Gate failed after 3 rounds. The draft needs structural rework — likely a different angle, more research, or a manual rewrite. See `<piece>/04-diligence/preflight-report.md` for the findings trail."*
- **3 (gate-pre-review):** Stage 1, 2, 3, or 5 failed and we never got to the reviewer. Fix the structural issue (missing frontmatter, em-dash, [F] data, missing hero) and re-run without dispatching the reviewer again.

## STEP 5 — Release Owner sign-off

If preflight passes, **do not auto-sign.** The plugin never auto-signs. Surface the gate result to the user with the three whitepaper questions, in this exact format:

```
Release Owner Gate passed.

Score: <total>/100
Reviewer BLOCKING verdict: false
Three highest-leverage claims to verify by hand:
  1. <claim> — Source: <url>
  2. <claim> — Source: <url>
  3. <claim> — Source: <url>

Three questions before you sign:

  1. Is every claim grounded? (Trace each of the three claims above to its source.)
  2. Does it sound like us? (Read the first 200 words and the last 200 words aloud.
     If the middle 80% drifts in voice, the gate fails — say so.)
  3. Would you send this with your own name on it?

If all three answers hold, append this line to <piece>/changelog.md:

  Verified — <your initials>, <today YYYY-MM-DD>

Then say "signed" and I'll generate the LinkedIn pair.
```

Wait for the user's explicit "signed" (or equivalent confirmation). Do not generate the LinkedIn pair before this. The signature is the whole point of the framework.

## STEP 6 — On signature: hand off to linkedin-deriver

When the user confirms the signature:

1. Verify `<piece>/changelog.md` contains a `Verified — <initials>, <date>` line dated today.
2. Update `<piece>/state.md`: `gates_passed: [01, 02, 03, 04]`, append `<ISO> — Phase 04 passed, signed by <initials>` to the process log.
3. Invoke the `linkedin-deriver` skill to produce the LinkedIn article + teaser.

## What the reviewer subagent IS allowed to do

- Read the draft, the rubric, the anti-pattern catalog, the AEO checklist, the sources file, the delegation file.
- Read any reference file in `${CLAUDE_PLUGIN_ROOT}/references/`.
- Glob/Grep within the piece directory.
- Write `<piece>/04-diligence/review.md`.

## What the reviewer subagent is NOT allowed to do

- Execute anything (no Bash).
- Edit the blog draft (no Edit).
- Write anywhere outside `<piece>/04-diligence/review.md`.
- Make network requests.
- Mark its own verdict approved without echoing the nonce verbatim.

The tool restriction is the security boundary — a reviewer that can edit can write its own pass condition. A reviewer that can shell can spoof preflight's parsed values. Hold the boundary.

## What this skill does NOT do

- It does NOT draft or rewrite content. The orchestrator's iteration loop revises the draft based on the reviewer's findings; the reviewer never does the revision.
- It does NOT decide when to publish. The Release Owner signs by hand; the plugin never auto-publishes.
- It does NOT touch the canonical Phase-3 artifact. `<piece>/03-discernment/draft.md` remains read-only after Phase 3.

## Degradation behaviors

- **Reviewer subagent unavailable** (Agent tool not loaded): fall back to having Claude itself act as reviewer with the same prompt, in the same session — but flag this in `preflight-report.md` as a degraded mode (less independent than a subagent context). Still required to echo the nonce.
- **Hero image generation fails** (frontier-founder/blog-post errors or no Banana MCP): surface the error, ask the user whether to skip the hero (preflight will fail Stage 3) or retry. Never insert a placeholder image and call the stage passed.
