---
description: Add abstracts to an existing BibTeX file
argument-hint: [path-to-bib-file]
allowed-tools: Read, Write, Edit, Bash, WebFetch, AskUserQuestion, TodoWrite, Glob
---

Enrich an existing BibTeX file by generating abstracts for entries that lack them.

Load the bibtex-builder skill by reading `${CLAUDE_PLUGIN_ROOT}/skills/bibtex-builder/SKILL.md`, then follow these steps:

1. **Locate the .bib file**: If $ARGUMENTS contains a file path, use it. If an uploaded .bib file exists in the uploads directory, use that. Otherwise, ask the user to provide or upload their .bib file.

2. **Parse the file**: Use the Python parser from `${CLAUDE_PLUGIN_ROOT}/skills/bibtex-builder/references/bibtex-parser.md` via Bash to parse all entries. Report: total entries found, how many already have abstracts, how many need enrichment.

3. **Ask output location**: Use AskUserQuestion to ask where to save the enriched file. Default suggestion: same filename with `-enriched` appended, or overwrite the original.

4. **Enrich entries missing abstracts**:
   - For entries WITH a `url` field: fetch the URL with WebFetch, generate a 2–4 sentence abstract
   - For entries WITHOUT a `url` field: generate a best-effort abstract from the title, author, journal, and year fields. Add a note comment above the entry: `% Abstract generated from metadata only — no URL available`
   - For entries that ALREADY have an abstract: preserve it unchanged

5. **Reassemble**: Rebuild the complete .bib file with all entries. Follow the formatting rules in `${CLAUDE_PLUGIN_ROOT}/skills/bibtex-builder/references/bibtex-format.md`. Preserve all original fields.

6. **Save and report**: Save the enriched file. Present a summary: total entries, abstracts preserved, abstracts generated from URL, abstracts generated from metadata, any fetch failures.
