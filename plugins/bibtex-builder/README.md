# BibTeX Builder

Build and enrich BibTeX bibliographies with AI-generated abstracts from web content.

## What It Does

This plugin creates properly formatted BibTeX files with high-quality abstracts. It works in three modes:

- **From URLs**: Give it one or more URLs and it produces a complete .bib file with metadata and abstracts extracted from each page.
- **Enrich existing .bib**: Upload a BibTeX file and it fills in missing abstracts by fetching the URLs in each entry.
- **Conversational**: Just mention building a bibliography or adding abstracts and the skill activates.

## Components

| Component | Name | Purpose |
|-----------|------|---------|
| Skill | `bibtex-builder` | Core knowledge: abstract generation rules, BibTeX formatting, workflow logic |
| Command | `/bibtex-from-urls` | Build a .bib file from a URL or list of URLs |
| Command | `/bibtex-enrich` | Add abstracts to an existing .bib file |

## Usage

### Build from URLs

```
/bibtex-from-urls https://example.com/article1, https://example.com/article2
```

Or just say: "Build me a BibTeX file from these URLs" and paste them.

### Enrich an existing file

```
/bibtex-enrich /path/to/my/bibliography.bib
```

Or upload a .bib file and say: "Add abstracts to this bibliography."

## Abstract Quality

Generated abstracts follow academic standards:

1. State the central aim or problem
2. Synthesize main arguments, methods, and findings
3. Highlight implications or broader significance
4. Written in clear, accessible academic language

## Requirements

- **WebFetch tool**: Used to retrieve page content (built into Cowork)
- No external API keys or MCP servers required

## Output

- Properly formatted .bib files ready for import into Zotero, Mendeley, JabRef, or any reference manager
- Files include a header comment with generation date and entry count
- Entries sorted alphabetically by citation key
