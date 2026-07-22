---
name: research-analyst
description: Analyze research sources, design a section-by-section document structure, select key citations per section, and prepare a complete handoff for the writer. Stage 5 of the academic-pipeline. Runs a four-pass analysis (map the landscape, deep-dive three levels, challenge everything, decision briefing) before structure is designed, so the writer inherits a point of view instead of a source list. Use when sources need analyzing and a paper structure needs planning before drafting.
license: Proprietary - MoxyWolf LLC
---

# Research Analyst — Stage 5

Turn a pile of sources plus a defined perspective into an approved, section-by-section plan the writer can execute without guessing.

## Role in the pipeline

Fifth stage of the `academic-pipeline`. Consumes the outputs of Stages 1–4; produces `handoff_for_writer.json`, the single contract Stage 6 (`research-writer`) writes from.

## Inputs

All read from the run folder's `pipeline/` subfolder unless noted:

- `perspective.json` (Stage 2) — lens, audience, sub-themes
- `voice_context.json` (Stage 3) — the author's angle, evidence, contrarian take
- `formatting_requirements.json` (Stage 4) — Academia.edu structure + MoxyWolf anti-AI rules
- `theme_analysis.json` + `mermaid_diagram.md` (Stage 1) — themes for reference
- The **BibTeX file** — path recorded in `theme_analysis.json` (`bibtex_source_path`). Read it directly.

Optional: content type (article / literature review / white paper — default article), target length (default 3000–5000 words), citation style (default Vancouver to match Academia.edu; APA/Chicago/MLA also supported).

## Process

### Step 1 — Load context

Read all five inputs and the `.bib`. Hold the perspective, voice, and formatting requirements in mind for every decision below.

### Step 2 — Map the landscape

For each `sub_theme` in `perspective.json`, before drawing any conclusions, map what the bibliography actually contains:

1. The 5 most load-bearing things the writer needs to understand about this sub-theme, drawn from the sourced literature.
2. Questions the perspective's target audience should be asking that the bibliography doesn't yet answer.
3. What the most-cited or most-repeated sources get wrong, oversimplify, or state as settled when it isn't.
4. What separates foundational-source knowledge from what only the newest or most specialized sources in the bibliography know.

This is a scratch map, not prose — hold it for Step 3 and Step 5. Don't write up findings as conclusions yet.

### Step 3 — Deep-dive the load-bearing finding

For the single most important finding surfaced in Step 2 per sub-theme (the one that most shapes the sub-theme's argument), go three levels deep against the actual BibTeX evidence:

- **Level 1** — what the foundational, frequently-cited sources establish. Common knowledge in the field.
- **Level 2** — what the specialized or mid-tier sources add on top of that. Informed-reader knowledge.
- **Level 3** — what only the newest or most specialized sources in the bibliography reveal. The non-obvious insight that should change how the reader thinks about the sub-theme.

Write Level 3 out explicitly per sub-theme — this is the sharpest material for `research_analysis_combined` and the part most likely to be the sub-theme's actual thesis, not just its summary.

### Step 4 — Challenge everything

Before the analysis is allowed to harden into structure, run an adversarial pass against the Step 2–3 findings. Per sub-theme:

1. What's presented as settled fact by the majority of sources but is actually contested, thinly evidenced, or unresolved?
2. What would a credible skeptic — or the strongest opposing/outlier source in the bibliography — say about the conclusions reached so far?
3. What counterargument or disconfirming source hasn't been weighed yet?
4. What would change the sub-theme's structure or argument entirely if it turned out to be true?

Do not defend the Step 2–3 findings here — attack them. Where the bibliography genuinely can't settle a contested point, say so; that becomes a `contested_points` entry rather than a forced conclusion.

### Step 5 — Decision briefing

Synthesize Steps 2–4 into a one-page decision briefing per sub-theme (or one combined briefing for the whole piece, whichever the content type calls for):

- **Known with confidence** — what the bibliography establishes solidly enough to state as fact in the paper.
- **Uncertain or contested** — where sources disagree, evidence is thin, or a Step 4 challenge is unresolved.
- **Top insights** — the load-bearing findings that should drive the argument (usually the Level 3 findings from Step 3).
- **Structural implication** — what Step 6 should do about each contested point: hedge the language, give it its own "tensions in the literature" subsection, or exclude it rather than state it as settled.
- **Open question** — what the bibliography still can't answer; worth flagging as a limitation or explicit reader-facing caveat rather than papering over.

This briefing is not optional scaffolding — it is shown to the user alongside the structure at Step 9's approval gate, and it directly constrains Step 6.

### Step 6 — Design the structure

Build a section-by-section outline aligned with the **perspective** (e.g. innovation-focused → recent developments lead), the **audience** (e.g. industry → practical implications), the **sub-themes** (each gets coverage), the **voice context** (mark where the author's experience and opinions belong), the **formatting requirements** (Academia.edu section structure and register), and the **Step 5 decision briefing** — confident findings get stated plainly; contested points get hedged framing or their own tensions subsection, never silently upgraded to fact.

Baseline article shape: Introduction → one section per sub-theme → integration/synthesis → Conclusion. Adjust by content type — literature review: thematic sections + critical synthesis; white paper: Problem → Solution → Implementation.

Mark **voice integration points**: which sections carry the author's lived experience, where strong opinions belong, where MoxyWolf frameworks apply.

### Step 7 — Select key sources

For each planned section choose 3–8 BibTeX keys that support it. Prefer sources aligned with the perspective lens; mix foundational and recent. As a default balance, ~40% recent (last 3 years), ~30% established, ~30% foundational — skew toward recent for an innovation lens, toward foundational for a theoretical one.

### Step 8 — Define citation rules

Set explicit in-text rules for the chosen style (Vancouver: numbered `[1]` after punctuation; APA: `(Author, Year)`; etc.) and a per-section citation count target (2–5).

### Step 9 — Present the structure for approval (HITL)

This is the pipeline's third and final interactive checkpoint. Show the user the proposed structure — section list, word targets, key sources mapped to each section — **and the Step 5 decision briefing** (confident findings, contested points, top insights, open question), then use the **AskUserQuestion tool** to ask whether to **approve as-is**, **modify** (collect the changes as free text, revise, re-show), or **reject** (return to Step 6, or to Step 4 if the challenge itself needs revisiting). Do not write a HITL request file or block; just ask. If the orchestrator front-loaded approval, skip the prompt.

### Step 10 — Write the handoff

Once approved, write **`<run folder>/pipeline/handoff_for_writer.json`**:

```json
{
  "section_title": "<TARGET_TITLE>",
  "content_type": "article",
  "target_length_words": 4000,
  "citation_style": "Vancouver",
  "approved": true,
  "structure_plan": [
    "Introduction: <framing>",
    "<Sub-theme 1 section>",
    "<Sub-theme 2 section>",
    "<Integration / synthesis>",
    "Conclusion: <forward look>"
  ],
  "section_word_targets": { "Introduction: <framing>": 500 },
  "key_sources_planned": ["author2024key", "org2025key"],
  "section_source_mapping": {
    "<Sub-theme 1 section>": ["author2024key", "org2025key"]
  },
  "perspective_focus": [
    "<lens> perspective: <what it emphasizes>",
    "Audience: <target market>",
    "Emphasize: <priorities>"
  ],
  "voice_integration": {
    "author_perspectives": ["Section N: <lived experience to weave in>"],
    "frameworks": ["<MoxyWolf framework that applies>"],
    "writing_patterns": ["Active voice, concrete examples", "No AI tells — see formatting_requirements.json"]
  },
  "in_text_citation_rules": "<explicit rule for the chosen style; 2-5 citations per section>",
  "research_analysis_combined": "<the full 1000-2000 word landscape analysis, incorporating the Step 3 Level 3 deep-dives>",
  "decision_briefing": {
    "confident": ["<finding the bibliography establishes solidly>"],
    "uncertain_or_contested": ["<contested point> — <why, and which sources disagree>"],
    "top_insights": ["<the Level 3 finding most likely to be the paper's actual thesis>"],
    "structural_implications": "<which sections hedge, which get a tensions subsection>",
    "open_question": "<the one thing the bibliography still can't answer>"
  },
  "bibtex_source_path": "<absolute path>",
  "mermaid_diagram_reference": "<complete Mermaid markdown>",
  "created_at": "<ISO 8601 timestamp>"
}
```

## Return to the orchestrator

```json
{
  "status": "complete",
  "sections_planned": 6,
  "sources_selected": 8,
  "contested_points_flagged": 2,
  "estimated_length": "4000-4500 words",
  "approved": true,
  "output_file": "<run folder>/pipeline/handoff_for_writer.json"
}
```

## Error handling

If a sub-theme has too few sources, warn rather than fail:

```json
{ "status": "warning",
  "message": "Only 2 sources support sub-theme 'X'. Consider merging it or broadening scope.",
  "affected_sections": ["<section>"] }
```

If Step 4's challenge pass surfaces a contested point with no clear resolution, don't fail — carry it into `decision_briefing.uncertain_or_contested` and let Step 6 hedge the structure. Only warn if a contested point is load-bearing enough that the whole section built on it needs the user's explicit call before Step 9.

## Notes

- The `research_analysis_combined` field is the most important output — spend real effort there, and let the Step 3 Level 3 deep-dives be its spine rather than a source-by-source summary.
- Be opinionated about structure; the perspective earns a point of view. Step 4's challenge pass exists so that opinion is pressure-tested, not just asserted.
- Steps 2–5 (map, deep-dive, challenge, briefing) happen before structure is designed — resist the urge to jump straight to an outline from Step 1's raw sources.
- `section_source_mapping` tells the writer exactly what to cite where.
- `decision_briefing.uncertain_or_contested` tells the writer where to hedge language instead of asserting a contested claim as fact — treat it as a writer-facing brief, not just an approval artifact.
- Target ~600–800 words per section for a 4000-word article.
