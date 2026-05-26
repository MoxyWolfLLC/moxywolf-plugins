---
read_when: "Phase 4 (Diligence) loads this in full when the BLOCKING reviewer agent scores the draft. scripts/preflight.py parses the reviewer's output against this rubric."
status: canonical
based_on: "agricidaniel/claude-blog 5-gate Blog Delivery Contract (100-point rubric); SMOrchestra-ai/smorch-dev 8-dimension content rubric with threshold actions; getsentry/skills 10 Non-Negotiables; the Release Owner Gate spec from MoxyWolf's Beyond the Prompt whitepaper §7."
---

# Release Owner Rubric — the 100-point Diligence scorecard

> **Read this when:** invoking `/4d-blog-engine:diligence`. The BLOCKING reviewer scores the draft against this rubric, then `scripts/preflight.py` parses the verdict against the gate logic.

This is the rubric the Release Owner Gate uses. The whitepaper's gate description is precise:

> *"The Release Owner opens the raw output, takes the three highest-leverage claims or numbers in it, and traces each one back to a source or an explicit policy. Then three questions. Is every claim grounded? Does it sound like us? Would I send this with my own name on it?"*

The rubric below operationalizes the *first* of those — the BLOCKING reviewer agent runs a 100-point check. The Release Owner still answers the three questions by hand before signing the changelog. **The rubric is necessary but not sufficient.**

## Five categories, 100 points total

| Category | Points | Sub-rubric below |
|---|---|---|
| Content quality | 30 | §1 |
| SEO + AEO | 25 | §2 |
| E-E-A-T | 15 | §3 |
| Voice match | 15 | §4 |
| AI-citation readiness | 15 | §5 |

**Pass threshold: 90/100.** Anything below 90 iterates (max 3 rounds) then escalates.

## §1 — Content quality (30 points)

| Criterion | Max | Score guidance |
|---|---|---|
| Clear thesis, stated in the opener | 5 | 5 = appears in first 40-60 words. 3 = appears in first 200. 0 = buried/missing. |
| Earned secret present and prose-anchored | 5 | 5 = at least one passage anchored in author's direct experience (not training-data). 0 = no detectable lived-experience signal. |
| Information density (every sentence earns its place) | 5 | 5 = no transitional filler, no sentences that could apply to any topic. 3 = some filler. 0 = padded. |
| Specificity (named companies/people/numbers/dates) | 5 | 5 = ≥ 5 specifics per 1000 words. 3 = 2-4. 0 = abstract throughout. |
| Argument structure (claim, evidence, mechanism, implication) | 5 | 5 = every H2 follows the pattern. 3 = most. 0 = scattered. |
| Conclusion delivers a "what you do Monday" — concrete action | 5 | 5 = one specific action, named, with success criteria. 3 = vague action. 0 = pure summary. |

## §2 — SEO + AEO (25 points)

Verified against `aeo-checklist.md`.

| Criterion | Max | Score guidance |
|---|---|---|
| Title 50-60 chars, primary keyword in first 30 chars | 3 | Binary on each constraint. |
| Direct-answer opener (40-60 words, contains target keyword) | 3 | Pass/fail. |
| "At a Glance" block present, 60-90 words, self-contained | 4 | 4 = ideal length + standalone. 2 = present but weak. 0 = missing. |
| TL;DR / Key Takeaways block (120-160 words) | 3 | Binary on length + completeness. |
| 60-70% of H2s are questions; one idea per H2 | 3 | 3 = both. 2 = one. 0 = neither. |
| Citation capsule (40-60 words) after each H2 with sourced statistic | 3 | Per H2 average. |
| FAQ section (4-6 Qs in natural-prompt language) | 3 | Pass/fail. |
| Meta description 150-160 chars, keyword-included, ends with CTA verb | 3 | Pass/fail. |

## §3 — E-E-A-T (15 points)

Experience / Expertise / Authority / Trust signals. From schwepps/skills, amplitude/builder-skills.

| Criterion | Max | Score guidance |
|---|---|---|
| Named author + byline | 3 | Required. |
| First-hand experience markers ("we tested", "I measured", "in our case") | 3 | 3 = ≥ 2 markers. 1 = 1 marker. 0 = none. |
| External authoritative sources cited (Tier 1-2, FLOW triple) | 3 | 3 = ≥ 3 Tier 1-2 sources cited correctly. 0 = none. |
| Acknowledged limitations / counter-evidence | 3 | 3 = explicit limitation section or counter-argument paragraph. 0 = no caveats. |
| Visible publish + last-updated dates in frontmatter and prose | 3 | Pass/fail. |

## §4 — Voice match (15 points)

Verified against `MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md`.

| Criterion | Max | Score guidance |
|---|---|---|
| Contraction rate ≥ 80% of opportunities | 3 | Measure via `prose_lint.py`. |
| Sentence length burstiness > 0.5 | 3 | Measure via `prose_lint.py`. |
| Zero em-dashes; typographer's quotes; spaced en-dash sparingly | 3 | Binary. |
| Zero phrases from Tier-1 vocabulary blocklist | 3 | Binary; any hit = 0. |
| Zero Tier-2-Major structural patterns | 3 | Per `ai-anti-patterns.md` Tier-2-Major. Any hit = 0. |

## §5 — AI-citation readiness (15 points)

From the AEO checklist's Princeton GEO method ranking, applied to the actual draft.

| Criterion | Max | Score guidance |
|---|---|---|
| Inline `[Publisher](url)` citations (not bracketed numbers) | 3 | Pass/fail; bracketed numbers anywhere = 0. |
| Statistics include year + publisher + retrieval date (FLOW triple) | 3 | Per stat. 3 = all stats compliant. 0 = ≥ 1 stat missing the triple. |
| Schema.org JSON-LD present (BlogPosting; FAQPage if FAQ) | 3 | Binary. |
| Self-contained citation capsules (no "as discussed above") | 3 | Per H2. |
| Freshness signal: dateModified ≤ 30 days; visible "last updated" line | 3 | Binary. |

## Reviewer output contract — the verbatim format scripts/preflight.py expects

The BLOCKING reviewer **must** output its scorecard in this exact structure. Anything else is a structural failure and the gate rejects without scoring.

```markdown
# Release Owner Review — {{ slug }} — Round {{ N }} of 3

NONCE: {{ exact 32-char hex string from .review-nonce, verbatim }}

## Scores

| Category | Earned | Max |
|---|---:|---:|
| Content quality | {{ x }} | 30 |
| SEO + AEO | {{ x }} | 25 |
| E-E-A-T | {{ x }} | 15 |
| Voice match | {{ x }} | 15 |
| AI-citation readiness | {{ x }} | 15 |
| **Total** | **{{ sum }}** | **100** |

## Findings (numbered)

1. [Category § criterion] [SEVERITY: Major/Medium/Minor] [Quote: "exact text"] [Issue: one sentence] [Fix: specific change]
2. ...

## Three highest-leverage claims to verify by hand

1. Claim: "{{ verbatim quote }}" — Source: {{ url or "[CITATION NEEDED]" }}
2. ...
3. ...

## Verdict

BLOCKING: {{ true | false }} ({{ one-line reason }})
```

### Verdict rules — what `BLOCKING: true | false` means

- **`BLOCKING: false`** is allowed if AND ONLY IF: total ≥ 90, no `[F]` data in body, no Tier-2-Major patterns, nonce echoed verbatim, three highest-leverage claims listed with sources, zero `[CITATION NEEDED]` placeholders in body.
- **`BLOCKING: true`** otherwise. The one-line reason must name the specific failing criterion ("Total 87/100, voice match 9/15 — em-dashes detected").

### Nonce verification

`scripts/preflight.py` reads `.review-nonce` (CSPRNG, 32 hex chars, regenerated per round) and the reviewer's output. If `NONCE:` in the review doesn't match the file verbatim, the gate **rejects the review entirely** and asks the reviewer to re-run. This prevents any process from faking `BLOCKING: false` by reproducing the format without doing the work.

### Iteration cap

- Round 1: review the original draft. If `BLOCKING: false` and score ≥ 90, gate passes.
- Round 2: writer addresses the round-1 findings, regenerates the draft, re-runs the reviewer.
- Round 3: same.
- Round 4+: gate halts and escalates to the human. The reviewer cannot fix everything; the writer needs a different angle, more research, or a manual rewrite.

## What the Release Owner does by hand (after the rubric passes)

The rubric is necessary but not sufficient. After `BLOCKING: false`, the Release Owner — a named human, rotating weekly through the three most senior people who already know the domain — performs the whitepaper's three checks:

1. **Is every claim grounded?** Take the three highest-leverage claims (from the reviewer's "Three highest-leverage claims" block) and trace each one back to its source or to an explicit policy. If any can't be traced, gate fails.
2. **Does it sound like us?** Read the first 200 words and the last 200 words aloud. If the voice drifts in the middle 80%, gate fails. The whitepaper specifically calls out "personality only in the bookends" as the most common drift pattern.
3. **Would I send this with my own name on it?** If no, gate fails. No verbal override.

If all three answers hold, the Release Owner writes the sign-off line into `changelog.md`:

```
Verified — {{ initials }}, {{ YYYY-MM-DD }}
```

**The plugin never auto-signs.** That signature is the whole point of the framework.

## What this rubric does not score

- **Whether the post should exist.** That's Phase 1 (Delegation) — the capability triage. If it shouldn't, it doesn't reach Phase 4.
- **Whether the angle is right.** Phase 1 again.
- **Whether the research was thorough enough.** Phase 3 grades research quality (`[V]/[S]/[F]` tags + Tier ladder) before drafting begins.
- **Whether the post will perform on LinkedIn.** That's the 3-axis LinkedIn scorecard (`linkedin-scorecards.md`) Phase 4 generates separately AFTER the blog passes.

This rubric scores only: does the draft pass quality, AEO, E-E-A-T, voice, and citation-readiness gates well enough that a Release Owner can put their name on it.
