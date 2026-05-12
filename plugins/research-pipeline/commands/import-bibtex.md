---
description: Import a BibTeX file into the research pipeline
argument-hint: [library-name]
---

Load the import-bibtex skill and run the full import pipeline.

If a file is attached or was recently uploaded, use it as the BibTeX source.
If "$ARGUMENTS" is provided, use it as the library name.

Steps:
1. Read the BibTeX file (uploaded or from path)
2. Create a new research library (or select existing if name matches)
3. Parse all BibTeX entries and deduplicate
4. Enrich missing abstracts via CrossRef API + LLM generation
5. Insert all citations into Supabase
6. Upload annotated bibliography to Google Drive
7. Present summary with next-step recommendations
