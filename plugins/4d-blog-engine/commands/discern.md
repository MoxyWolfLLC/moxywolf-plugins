---
description: Phase 3 — Discernment. 30-day discourse sweep, draft, two-tier anti-AI-slop pass with second-pass audit.
argument-hint: [<piece-slug>]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, WebSearch]
---

# /4d-blog-engine:discern — Phase 3 only

Invoke the `4d-blog-engine` orchestrator skill and run **only Phase 3** against an existing Phase-2 artifact.

Phase 3 answers: *Did the draft survive a real check — including a 30-day reality check from the world outside our heads?*

**Argument:** `<piece-slug>` — the per-piece directory. If omitted, the orchestrator picks the most-recently-modified piece at `current_phase: 02`.

Refuses to run on stale or absent Phase 2 (see `describe.md` gate logic).

It does, in order:

1. **30-day discourse sweep** — hand off to the `discourse-sweep` skill. Fires platform-targeted queries across reddit, X, Hacker News, Substack, dev.to, github, linkedin.com/pulse, Facebook, Quora, podcasts (Apify), and academic (research-pipeline/literature-discovery). Ranks via `scripts/discourse_sweep.py rank`. Outputs `<piece>/03-discernment/discourse.md`.
2. **Council synthesis pass** — `/council:deliberate` on the harvest to separate consensus from noise, identify contradictions, surface themes. Outputs `<piece>/03-discernment/discourse-themed.md`.
3. **Bibliography build** — `bibtex-builder/bibtex-from-urls` on the Tier 1-3 sources. Each entry gets an AI-generated 50-150-word abstract and a `quality_tier` field. Outputs `<piece>/03-discernment/bibliography.bib`.
4. **Citation verification** — `research-pipeline/citation-verifier` runs the 4-layer check. Tags each datum `[V]`/`[S]`/`[F]`. Outputs `<piece>/03-discernment/sources-verification.md`. `[F]` data is forbidden in body.
5. **Draft** — `research-pipeline/content-writer` runs with the voice profile, the DOB arc, the outline, and the verified bibliography. Every cited statistic must carry the FLOW evidence triple. Outputs `<piece>/03-discernment/draft.md`.
6. **Layer-1 slop pass (deterministic)** — `scripts/prose_lint.py --report <piece>/03-discernment/draft.md`. Writes `slop-findings.md` and emits a letter grade.
7. **Layer-2 slop pass (LLM)** — sub-agent scans the draft against `references/ai-anti-patterns.md` Tier-2 structural patterns (question-H2 ratio, three-clause rhythm, "Here" clustering, hedge stacking, paragraph-shape flatness). Findings appended to `slop-findings.md`.
8. **Rewrite against findings.** Edit the draft to address every Major and Medium finding.
9. **Second-pass audit (mandatory).** Re-run Layer 1 + Layer 2 on the rewrite. Any surviving Tier-2-Major means the rewrite was cosmetic — redo the whole composition step, not patch. Outputs `slop-findings-pass2.md`.
10. **Letter grade** — A or B advances to Phase 4. C forces re-rewrite. D or F aborts the phase and demands a structural rethink.

Surfaces the slop grade and findings to the user before declaring Phase 3 complete.

Read `skills/4d-blog-engine/SKILL.md` §"Phase 3 — Discernment" and `skills/discourse-sweep/SKILL.md` for the full workflow.
