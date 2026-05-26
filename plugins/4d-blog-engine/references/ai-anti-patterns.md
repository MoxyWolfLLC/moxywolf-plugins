---
read_when: "Phase 2 (Description) loads this in full before any prose is generated; phase 3 (Discernment) runs the Layer-2 LLM scan against it; scripts/prose_lint.py implements Layer 1 from this file's vocabulary lists."
status: canonical
maintenance: "If a pattern keeps slipping past the linter, extend scripts/prose_lint.py with a deterministic rule. Never add rules that ask Claude to remember."
---

# AI anti-patterns — two-tier slop catalog

> **Read this when:** writing prose (Phase 2 internalizes it before composition; Phase 3 audits against it).

Aspirational rules ("write naturally") fail. This file is the catalog that the deterministic linter (`scripts/prose_lint.py`) and the LLM structural reviewer scan against. Pair vocabulary (Tier 1) with structure (Tier 2) — vocabulary tells survive vocabulary swaps, so the structural scan is mandatory.

The full MoxyWolf voice profile lives at `MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md`. This file is the **enforceable subset** — patterns measurable by script or scannable by an LLM scoped specifically to detection.

## Tier 1 — vocabulary blocklist

`scripts/prose_lint.py` flags any case-insensitive match below. Each flag is a finding; severity is graded by hit count and clustering.

### Banned words (single-word AI tells)

```
delve, leverage (as verb), utilize, robust, seamless, seamlessly,
tapestry, multifaceted, testament, pivotal, paradigm, holistic,
synergize, synergy, foster (as verb), comprehensive, cutting-edge,
revolutionize, harness (as verb), unlock (metaphorical), thrilled,
landscape (metaphorical), navigate (metaphorical), crucial, vital,
game-changer, game-changing, transformative, journey (metaphorical),
empower, ecosystem (metaphorical), pillar (metaphorical),
ascertain, commence, disseminate, facilitate (vague),
ever-evolving, ever-changing, dynamic (vague), innovative (vague)
```

### Banned phrases (regex patterns)

```
in today's (fast-paced|digital|modern|ever-evolving|rapidly changing) (world|landscape|era|environment)
in the (era|age) of
it's (worth|important) (noting|noting that|to (note|understand|consider))
it (is|'s) (worth|important) (noting|to note)
needless to say
that being said
let's (dive|delve|jump|explore|unpack|talk about|take a (closer|deeper) look)
buckle up
the catch\?
here's the (thing|kicker|deal)
sound familiar\?
in conclusion
to wrap (up|things up)
moving forward
in order to
the fact that
as we (all )?know
welcome to (this|the) (issue|edition|post|article)
in this (post|article|blog|piece)( ,)? (we'?(ll| will)|i'?(ll| will))
i'?m (thrilled|excited|delighted) to (share|announce)
without further ado
i'?m (excited|happy) to (announce|share)
```

### Banned transitions (sentence-initial)

```
Furthermore,  Additionally,  Moreover,  Nevertheless,
In conclusion,  However it should be noted,  That being said,
With that said,  All in all,  To summarize,
```

### Typographic rules (auto-fixed where possible)

- Em-dash `—` → spaced en-dash ` – ` (sparingly). Auto-replace in `prose_lint.py --fix`.
- Straight quotes `"..."` `'...'` → typographer's quotes `"..."` `'...'`. Auto-replace.
- Three or more consecutive em-dashes anywhere → fail.
- No semicolons in body prose (MoxyWolf convention; flag only).

## Tier 1 — measurable structural metrics (numeric, scriptable)

`scripts/prose_lint.py` computes these. Thresholds derived from agricidaniel/claude-blog and lifegenieai/copy-editor.

| Metric | Formula | Pass threshold | Fail at |
|---|---|---|---|
| Burstiness | `stdev(sentence_lengths) / mean(sentence_lengths)` | > 0.5 (natural variation) | < 0.3 (AI-uniform) |
| Type-Token Ratio | `unique_words / total_words` | > 0.5 | < 0.4 |
| Passive voice rate | passive sentences / total sentences | < 10% | > 20% |
| Mean sentence length | total words / sentence count | 12-22 words | < 10 or > 26 |
| Paragraph length SD | stdev of paragraph word counts | > 25 | < 25 (AI-uniform) |
| List-item word-count SD | stdev across bullet lengths | > 5 | < 5 (symmetric-bloat) |
| Em-dash count | regex `—` count | 0 | > 0 |

Output: `slop-findings.md` per piece, structured as `[SEVERITY] Metric / Value / Threshold / Locations`.

## Tier 2 — structural patterns (LLM-scanned, survive vocabulary rewrites)

These are the tics that don't show up in vocab lists but read as AI on the page. The LLM sub-agent in Phase 3 scans for each. From agricidaniel/claude-blog's two-tier detector and heymitch/ai-pattern-hunter.

### Major (auto-fail if 2+; F-grade trigger)

- **Contrast framing.** "It's not X, it's Y." "Not X. Y." Three+ across a post = manufactured drama. Flag every instance.
- **Robotic transitions.** "Here's the thing:" / "At the end of the day" / "Here's what nobody tells you:" / "The truth is:"
- **The three-beat reveal.** Three staccato fragments leading to a punchline — "Not a config issue. Not a code bug. Not a regression." (getsentry/skills calls this out by name.)
- **Question H2 saturation.** More than 70% of H2s are questions. (60-70% is the AEO sweet spot; >70% reads as AI scaffolding.)
- **"Here" paragraph-starter clustering.** 3+ paragraphs in the post starting with "Here is" / "Here's" / "Here are".
- **Three-clause-sentence rhythm.** More than 50% of sentences match `[clause], [clause], [clause].` — the AI cadence.

### Medium (auto-fail if 4+ total mediums; D-grade contribution)

- **Hedge stacking.** ≥2 hedges in a 20-word window. "These data may potentially suggest the possibility of an association…"
- **Bumper-sticker aphorisms.** Short standalone sentences that sound like a slide title rather than a thought. "Speed is a feature." "The fundamentals matter."
- **Smug simplicity.** "That's it. That's all you need." "Simple as that."
- **Parallel-structure ad copy.** Three+ consecutive sentences with identical syntactic structure for rhetorical effect ("Built fast. Shipped clean. Loved it.").
- **Personality only in the bookends.** First and last paragraphs read as a person; the middle 80% reads as clinical. Voice must persist throughout.
- **"Most people don't realize…" / "Nobody tells you…" / "Here's what they're missing…"** — AI's go-to false-insight openers.
- **Rhetorical questions at paragraph transitions.** "But what does this mean for you?" / "So why does this matter?"

### Minor (cumulative; A→B→C threshold)

- **Symmetric-list-bloat.** Every list has exactly 3 items, or every list has items of identical word count.
- **Capsule H2 transitions.** "First," "Next," "Additionally," "Finally," as H2 openers — schoolbook scaffolding.
- **"Let's" openers.** "Let's explore…" / "Let's dive in…" / "Let's take a closer look…" (also vocab Tier 1.)
- **False-balance framing.** "While X, also Y." used as a soft consensus device.
- **Self-answering fragment questions.** "What does this mean? It means…" "Why now? Because…"

## Letter grade (output of Phase 3)

Sum the findings, weighted by severity tier (Major=3, Medium=2, Minor=1):

- **A** — total score < 4. Ship.
- **B** — 4-7. Minor cleanup only.
- **C** — 8-12. Phase 3 must re-rewrite the flagged sections, then run a second-pass audit.
- **D** — 13-19, or 2+ Majors. Phase 4 (Diligence) is blocked. Phase 3 redo from draft step.
- **F** — 20+, or 3+ Majors, or 6+ total findings of any severity. Discard the draft. Rerun Phase 3 from outline.

## Second-pass audit (mandatory)

After the rewrite against findings, the sub-agent re-reads the rewrite against this same catalog. Survivors are flagged in `slop-findings-pass2.md`. If any Tier-2-Major survives, the rewrite was cosmetic (lifegenieai's "transformation is cosmetic, not structural" verdict). Redo the entire composition phase, not just patch.

## What this catalog is NOT

- It is not a writing style guide. The voice guide is `MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md`.
- It is not a hedge against bad writing in general. It targets *AI-specific* tells. Bad human writing usually has different problems (under-edited rambling, jargon dumps, unclear thesis); this catalog won't catch those.
- It is not exhaustive. As new AI tells appear, extend `scripts/prose_lint.py` and add a section here. **Never** ask Claude to remember a new rule that isn't in this file.
