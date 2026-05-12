---
description: Build a BibTeX file with abstracts from one or more URLs
argument-hint: [url or "url1, url2, ..."]
allowed-tools: Read, Write, Edit, Bash, WebFetch, AskUserQuestion, TodoWrite, Glob
---

Build a BibTeX bibliography from the provided URLs. If $ARGUMENTS contains URLs, use those. If no arguments provided, ask the user to paste URLs.

Load the bibtex-builder skill by reading `${CLAUDE_PLUGIN_ROOT}/skills/bibtex-builder/SKILL.md`, then follow these steps:

1. **Parse input**: Extract all URLs from the arguments. Accept comma-separated, space-separated, newline-separated, or a single URL. If a file path is given instead of URLs, read the file and extract URLs from it.

2. **Ask output location**: Use AskUserQuestion to ask the user what to name the output .bib file and where to save it. Suggest a name based on the content topic.

3. **Process each URL**:
   a. Fetch the page content using WebFetch
   b. Extract bibliographic metadata (author, title, year, publication venue)
   c. Generate a 2–4 sentence abstract per the skill's abstract quality rules
   d. Create a citation key in `{author}_{word}_{year}` format
   e. Format as a proper BibTeX entry per `${CLAUDE_PLUGIN_ROOT}/skills/bibtex-builder/references/bibtex-format.md`

4. **Compile**: Combine all entries into a single .bib file with a header comment, sorted alphabetically by citation key.

5. **Save and report**: Save the file to the user's chosen location. Present a summary showing how many entries were created, any URLs that failed, and the output path.

If any URL fails to fetch, log it and continue with the remaining URLs. Include failed URLs in the final summary.
