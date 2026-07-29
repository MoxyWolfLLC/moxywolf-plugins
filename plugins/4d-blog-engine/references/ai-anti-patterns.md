---
read_when: "Phase 2 (Description) loads this in full before any prose is generated; phase 3 (Discernment) runs the Layer-2 LLM scan against it; scripts/prose_lint.py implements Layer 1 from this file's vocabulary lists and density rules."
status: canonical
maintenance: "If a pattern keeps slipping past the linter, extend scripts/prose_lint.py with a deterministic rule. Never add rules that ask Claude to remember. If a rule starts failing the writer's own published work, recalibrate it against that corpus rather than overriding it per-piece."
revised: 2026-07-29
revision_reason: "Added the long-form allowance for signature devices, replacing a raw-count fail on contrast framing and the three-beat reveal with a scored density rule calibrated against published text. Cause: three consecutive Phase 3 failures (18 → 21 → 24) on a piece the catalog was structurally unable to pass."
---

# AI anti-patterns — two-tier slop catalog

> **Read this when:** writing prose (Phase 2 internalizes it before composition; Phase 3 audits against it).

Aspirational rules ("write naturally") fail. This file is the catalog that the deterministic linter (`scripts/prose_lint.py`) and the LLM structural reviewer scan against. Pair vocabulary (Tier 1) with structure (Tier 2) — vocabulary tells survive vocabulary swaps, so the structural scan is mandatory.

The writer's full voice profile lives at `<blog-project-dir>/<author-slug>-voice.md` (created by `/4d-blog-engine:blog-voice`). This file is the **enforceable subset** — generic anti-AI-slop patterns measurable by script or scannable by an LLM scoped specifically to detection. The two work together: the voice profile says what the writer *does* sound like; this catalog says what AI prose tends to sound like *regardless of writer*.

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
| Rhetorical density | pairs of rhetorical hits < 4 sentences apart | ≤ 2 | ≥ 6 (Major); 3-5 (Medium) |
| Standalone one-liners | one-sentence paragraphs ≤ 15 words | ≤ 2 | > 2 (Medium) |
| Short-sentence balance | short sentences doing ordinary work vs delivering a line | ordinary ≥ punchline | ordinary < punchline (Medium) |

The last three are scored only on long-form pieces (over ~900 words). See *Long-form allowance for signature devices* below for why, and for the calibration behind the numbers.

Burstiness is watched in both directions. Between 0.30 and 0.50 the script emits a Minor, because stripping fragments to satisfy a Tier-2 count drives variance toward the AI-uniform floor — you pay the Layer-1 price without collecting the Layer-2 benefit.

Output: `slop-findings.md` per piece, structured as `[SEVERITY] Metric / Value / Threshold / Locations`.

## Tier 2 — structural patterns (LLM-scanned, survive vocabulary rewrites)

These are the tics that don't show up in vocab lists but read as AI on the page. The LLM sub-agent in Phase 3 scans for each. From agricidaniel/claude-blog's two-tier detector and heymitch/ai-pattern-hunter.

### Major (auto-fail if 2+; F-grade trigger)

- **Contrast framing.** "It's not X, it's Y." "Not X. Y." Three+ across a post = manufactured drama. Flag every instance. **Subject to the long-form allowance below when the writer's voice profile declares it a signature device.**
- **Robotic transitions.** "Here's the thing:" / "At the end of the day" / "Here's what nobody tells you:" / "The truth is:"
- **The three-beat reveal.** Three staccato fragments leading to a punchline — "Not a config issue. Not a code bug. Not a regression." (getsentry/skills calls this out by name.) **Subject to the long-form allowance below when the writer's voice profile declares it a signature device.**
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

## Long-form allowance for signature devices

Two of the Tier-2 Majors above are also, for some writers, the fingerprint. Contrast framing and the three-beat reveal are named as signature constructions in the Dorian Cougias voice profile, with "The execution was fine. The shape was wrong." given as the calibration example and deliberate fragments required at least once per page. One document's Major is the other document's signature.

That conflict is not theoretical. Sampled verbatim from two published, human-written posts ("I Built One of the Biggest Compliance Frameworks. I Got the Shape Wrong", "The $488K Parsing Problem"), a fifteen-sentence passage carried six contrast framings and two multi-beat reveals. Against a threshold of three per post, the catalog grades the writer's own published work F on its first page.

### The rule

For a piece **over roughly 900 words** whose voice profile declares a device as a signature move:

1. **The raw count is advisory.** `prose_lint.py` reports it; nothing fails on frequency alone. Layer 2 must not fail a piece for having the writer's voice in it.
2. **Spacing is what gets scored.** No rhetorical hit within four sentences of another. Budget of 2 such pairs; 3-5 is a Medium, 6 or more is a Major.
3. **At most two standalone one-line paragraphs** in the whole piece.
4. **Short sentences must not all be punchlines.** At least as many brief declaratives doing ordinary work as brief declaratives landing a line. This is the difference between prose that reads as speech and prose that reads as engineered.
5. **Every other Major stays blocking.** "Here" clustering, robotic transitions, question-H2 saturation, and three-clause rhythm all fire correctly and are all worth fixing. The catalog is not broken generally. It was mis-scoped for one author's two devices.

### Why length is the trigger

The same per-paragraph density that reads fine at 450 words compounds into something that reads engineered at 1,600. Short pitches carried two or three of these devices with no trouble. A 1,450-word draft at the same density produced ten triads and seven contrasts, and every individual sentence was defensible while the whole read as manufactured.

### How the numbers were calibrated

Against finished text, in both directions, on 2026-07-29:

- "I Got the Shape Wrong" (2,146 words, published, human-written, signed) carries **2** density violations. A rule that fails it is wrong, so 2 has to pass.
- The draft that failed Phase 3 three consecutive times carried **9**. That has to land in Major.

Budget 2, Medium at 3, Major at 6 satisfies both ends. Re-derive these numbers if the corpus changes; do not adjust them to make a specific draft pass.

### Two failure modes this does not excuse

Across the three failed drafts the score went 18, 21, 24. Getting worse each time is not a calibration problem, and two real craft failures hid behind the miscalibration:

- **Punctuation laundering.** Converting "Not X. Not Y. Z." into "X, Y, and Z" changes the marks, not the cadence. It is not a fix and the auditor should say so.
- **Brevity as pure performance.** When every short sentence is a punchline, the prose reads as engineered even with every count inside budget. Rule 4 exists for this.

### What the script can and cannot see

`prose_lint.py` detects the single-sentence contrast forms ("it's not X, it's Y", "X, not Y", "not X but Y", a standalone "Not X.") and runs of short fragments inside one paragraph. It deliberately measures **body prose only** — headings, bullets, block quotes, and tables are excluded, because a "Key takeaways" list is supposed to be a stack of crisp contrast lines and scoring it as body cadence produces violations nobody should fix.

It does **not** reliably catch the cross-sentence two-beat contrast ("The execution was fine. The shape was wrong."). That one stays a Layer-2 judgment. Layer 1 gives Layer 2 a number to reason about; it does not replace the read.

## Letter grade (output of Phase 3)

Sum the findings, weighted by severity tier (Major=3, Medium=2, Minor=1):

- **A** — total score < 4. Ship.
- **B** — 4-7. Minor cleanup only.
- **C** — 8-12. Phase 3 must re-rewrite the flagged sections, then run a second-pass audit.
- **D** — 13-19, or 2+ Majors. Phase 4 (Diligence) is blocked. Phase 3 redo from draft step.
- **F** — 20+, or 3+ Majors, or 6+ total findings of any severity. Discard the draft. Rerun Phase 3 from outline.

## Second-pass audit (mandatory)

After the rewrite against findings, the sub-agent re-reads the rewrite against this same catalog. Survivors are flagged in `slop-findings-pass2.md`. If any Tier-2-Major survives, the rewrite was cosmetic (lifegenieai's "transformation is cosmetic, not structural" verdict). Redo the entire composition phase, not just patch.

Two rewrites that look like fixes and are not:

- **Trading one flagged pattern for another.** Converting three-beat reveals into two-beat contrasts moves the count between columns and changes nothing on the page. If contrast framing rises while multi-beat falls, the rewrite is cosmetic.
- **Relocating a move instead of removing it.** Deleting "the part where…" signposts and replacing them with "So set the scores down and look at…" is the same stage direction in different words.

If the second-pass score is **worse** than the first, stop patching. That is the signal that the findings are being satisfied literally rather than structurally, and the composition phase needs to restart from outline.

### Overrides are legitimate only when written down

A long-form piece may legitimately ship over a Layer-2 objection on a declared signature device. That is a decision, not a skip. Record the Layer-1 grade, the Layer-2 counts, the density numbers, and the name of the person who signed. A quiet skip is not an override, and the whole point of the Release Owner Gate is that a named person signs.

## What this catalog is NOT

- It is not a writing style guide. The writer's voice guide is `<blog-project-dir>/<author-slug>-voice.md` (created by `/4d-blog-engine:blog-voice`).
- It is not a hedge against bad writing in general. It targets *AI-specific* tells. Bad human writing usually has different problems (under-edited rambling, jargon dumps, unclear thesis); this catalog won't catch those.
- It is not exhaustive. As new AI tells appear, extend `scripts/prose_lint.py` and add a section here. **Never** ask Claude to remember a new rule that isn't in this file.
