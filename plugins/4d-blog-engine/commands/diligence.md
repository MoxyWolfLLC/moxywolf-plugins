---
description: Phase 4 — Diligence. The Release Owner Gate. Nonce-bound 5-stage contract with a 100-point BLOCKING reviewer.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:diligence — Phase 4 only

Invoke the `4d-blog-engine` orchestrator skill and run **only Phase 4** against an existing Phase-3 artifact.

Phase 4 answers: *Will a named human put their signature on this before it ships?*

**Argument:** `<piece-slug>` — the per-piece directory. If omitted, picks the most-recently-modified piece at `current_phase: 03`.

Refuses to run if Phase 3 didn't pass (grade ≤ C) or is more than 24 hours stale.

Hands off **entirely** to the `release-owner-gate` skill. That skill:

1. Stages the draft from `<piece>/03-discernment/draft.md` to `<piece>/04-diligence/blog.md`.
2. Generates the hero image via `frontier-founder/blog-post`'s fixed brand style spec — shown for approval before generation, saved as `og-hero.png` with an `og-hero-prompt.md` AI-transparency artifact.
3. Rotates the CSPRNG nonce in `<piece>/.review-nonce`.
4. Dispatches the BLOCKING reviewer subagent (Read, Write, Glob, Grep only — **no Bash, no Edit**) with `references/release-owner-rubric.md` and the rubric's exact output contract. The reviewer must echo the nonce verbatim and end with `BLOCKING: true|false (reason)`.
5. Runs `scripts/preflight.py` to validate format, hero presence, nonce match, score parsing, and asset integrity.
6. On `BLOCKING: false` and score ≥ 90: surfaces the gate result and the three highest-leverage claims to the Release Owner for the whitepaper's three hand-questions:
   - Is every claim grounded?
   - Does it sound like us?
   - Would you send this with your own name on it?
7. On signature (`Verified — <initials>, <YYYY-MM-DD>` appended to `<piece>/changelog.md` by the Release Owner): updates state and hands off to the `linkedin-deriver` skill.
8. On failure: iterates (up to 3 rounds) revising the staged blog against the findings. Round 4+ escalates.

**The plugin never auto-signs.** The signature is the whole point of the framework.

Read `skills/release-owner-gate/SKILL.md` and `references/release-owner-rubric.md` for the full workflow.
