---
description: Generate AI abstracts for BibTeX entries that lack them (Stage 0 — bibliography prep)
argument-hint: [path to .bib file]
---

Run **Stage 0** of the academic pipeline standalone, using the **`bibtex-abstract-generator`** skill.

1. Identify the BibTeX file — the path in `$ARGUMENTS` or an uploaded `.bib`.
2. For every entry **missing** an `abstract` field, fetch the source via its `url` or `doi` (using `mcp__workspace__web_fetch`) and write a faithful 2–4 sentence abstract. Skip entries that already have an abstract — never overwrite one. Never fabricate abstract text; if a source cannot be fetched, leave that entry's abstract empty.
3. Output a complete, valid `.bib` file with the new abstracts added and all original fields and formatting preserved.

Stage 1 (`bibtex-theme-analyzer`) needs abstracts to map themes, so run this whenever the input bibliography is thin on abstracts. When this feeds a pipeline run, save the enriched file as `enriched.bib` in the run folder's `pipeline/` subfolder and hand that path to `/academic-pipeline`.
