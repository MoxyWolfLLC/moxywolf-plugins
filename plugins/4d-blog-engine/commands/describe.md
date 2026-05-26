---
description: Phase 2 — Description. Voice interview, structure, outline, At-a-Glance block.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Glob, Grep, Bash, AskUserQuestion]
---

# /4d-blog-engine:describe — Phase 2 only

Invoke the `4d-blog-engine` orchestrator skill and run **only Phase 2** against an existing Phase-1 artifact.

Phase 2 answers: *Have we told the AI the goal and constraints precisely enough that it can behave usefully?*

**Argument:** `<piece-slug>` — the per-piece directory under `<active-project>/12 – MARCOM/Posts/`. If omitted, the orchestrator picks the most-recently-modified piece that's at `current_phase: 01` (i.e. ready for Phase 2).

Refuses to run if:
- `01-delegation.md` doesn't exist for the piece.
- `01-delegation.md`'s `_status` is not `passed`.
- `01-delegation.md`'s `_timestamp` is more than 24 hours old (re-run Phase 1 first).

It does:

1. Re-load the writer's voice profile (`<blog-project-dir>/<author-slug>-voice.md`, created by `/4d-blog-engine:blog-voice`) and report what was loaded.
2. Run the 8-question per-post voice interview from `research-pipeline/content-writer` — one question per message, push back on vague answers. (This is the per-post interview that captures this specific post's Trigger / Evidence / Contrarian Take / etc. — it's distinct from the one-time `/blog-voice` interview that builds the standing voice profile.)
3. Pick the narrative structure (Sorkin DOB default).
4. Build the outline — H2-by-H2, 60-70% question-phrased H2s, per-section word budget, per-section evidence needs (which sources the 30-day sweep will need to find).
5. Draft the 60-90 word "At a Glance" block per `references/aeo-checklist.md`.
6. Pre-load `references/ai-anti-patterns.md` and state which Tier-2-Major patterns to guard against in this piece.
7. Write `<piece>/02-description.md` and gate-check with the user (max 2 revision rounds).

Read `skills/4d-blog-engine/SKILL.md` §"Phase 2 — Description" for the full workflow.
