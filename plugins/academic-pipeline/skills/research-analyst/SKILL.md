---
name: research-analyst
description: Analyze research sources, design a section-by-section document structure, select key citations per section, and prepare a complete handoff for the writer. Stage 5 of the academic-pipeline. Use when sources need analyzing and a paper structure needs planning before drafting.
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

### Step 2 — Analyze the research landscape

For each `sub_theme` in `perspective.json`: identify the most relevant BibTeX entries, note methodological approaches, separate foundational from cutting-edge work, and flag gaps or tensions in the literature. Write this up as a 1000–2000 word `research_analysis_combined` — this is the writer's map, so make it substantive and opinionated.

### Step 3 — Design the structure

Build a section-by-section outline aligned with the **perspective** (e.g. innovation-focused → recent developments lead), the **audience** (e.g. industry → practical implications), the **sub-themes** (each gets coverage), the **voice context** (mark where the author's experience and opinions belong), and the **formatting requirements** (Academia.edu section structure and register).

Baseline article shape: Introduction → one section per sub-theme → integration/synthesis → Conclusion. Adjust by content type — literature review: thematic sections + critical synthesis; white paper: Problem → Solution → Implementation.

Mark **voice integration points**: which sections carry the author's lived experience, where strong opinions belong, where MoxyWolf frameworks apply.

### Step 4 — Select key sources

For each planned section choose 3–8 BibTeX keys that support it. Prefer sources aligned with the perspective lens; mix foundational and recent. As a default balance, ~40% recent (last 3 years), ~30% established, ~30% foundational — skew toward recent for an innovation lens, toward foundational for a theoretical one.

### Step 5 — Define citation rules

Set explicit in-text rules for the chosen style (Vancouver: numbered `[1]` after punctuation; APA: `(Author, Year)`; etc.) and a per-section citation count target (2–5).

### Step 6 — Present the structure for approval (HITL)

This is the pipeline's third and final interactive checkpoint. Show the user the proposed structure — section list, word targets, and the key sources mapped to each section — and use the **AskUserQuestion tool** to ask whether to **approve as-is**, **modify** (collect the changes as free text, revise, re-show), or **reject** (return to Step 3). Do not write a HITL request file or block; just ask. If the orchestrator front-loaded approval, skip the prompt.

### Step 7 — Write the handoff

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
  "research_analysis_combined": "<the full 1000-2000 word landscape analysis>",
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

## Notes

- The `research_analysis_combined` field is the most important output — spend real effort there.
- Be opinionated about structure; the perspective earns a point of view.
- `section_source_mapping` tells the writer exactly what to cite where.
- Target ~600–800 words per section for a 4000-word article.
