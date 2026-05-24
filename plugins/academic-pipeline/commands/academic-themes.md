---
description: Map a BibTeX bibliography into a Mermaid theme tree and a suggested article title (Stage 1 only)
argument-hint: [path to .bib file]
---

Run **Stage 1** of the academic pipeline standalone, using the **`bibtex-theme-analyzer`** skill.

1. Identify the BibTeX input — the path in `$ARGUMENTS`, an uploaded file, or pasted text.
2. Analyze the abstracts, extract the recurring themes, and build a Mermaid theme tree.
3. Propose 2–3 candidate titles and confirm `TARGET_TITLE` with the user via AskUserQuestion.
4. Write `theme_analysis.json` and `mermaid_diagram.md` to the run folder.

If fewer than three entries have usable abstracts, recommend running `/enrich-bibtex` first.

This is the entry point to the full pipeline — once the theme map looks right, offer to continue with `/academic-pipeline`.
