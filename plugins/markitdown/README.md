# markitdown Plugin

**Version:** 0.1.1
**Author:** MoxyWolf LLC
**Wraps:** [MarkItDown](https://github.com/microsoft/markitdown) by Microsoft (MIT License)
**Requires:** Python 3.10+ (Cowork sandbox has it). Optional: team OpenRouter key for LLM image descriptions + OCR.

## Overview

The ingestion front-end of the **document-analysis** pipeline. Raw documents in, clean Markdown with provenance out — ready for downstream chunking, synthesis, and analysis.

MarkItDown converts PDF, Word, PowerPoint, Excel, HTML, CSV/JSON/XML, and EPub into LLM-friendly Markdown, preserving structure (headings, lists, tables, links) rather than visual layout. This plugin adds the workflow MoxyWolf needs around it: batch folder conversion, YAML frontmatter, a hash-based manifest for idempotent re-runs, per-file error isolation, and optional OCR.

## Commands

| Command | Description |
|---------|-------------|
| `/markitdown-setup` | Install MarkItDown + document-set extras + `markitdown-ocr` + `openai`; verify the toolchain; resolve the OpenRouter key. Run once per session. |
| `/markitdown-convert` | Convert a file or folder → mirrored Markdown tree with frontmatter + manifest. Flags: `--out`, `--formats`, `--use-llm`, `--force`, `--no-recursive`. |

## What makes it more than a CLI wrapper

- **Batch + tree mirroring** — point it at a folder; get a parallel `sources-md/` tree of `.md`.
- **Provenance frontmatter** — `source_file`, `sha256`, `converted_at`, `converter`, `source_type`, `ocr`, `llm_model` on every output. See `references/frontmatter-schema.md`.
- **Idempotent manifest** — re-runs skip a file only when its source hash *and* conversion settings (`ocr`/`llm_model`/`converter_version`) are unchanged, so a later `--use-llm` run re-OCRs previously text-only files instead of silently skipping them (`--force` overrides). Cheap to re-run on a growing corpus.
- **Per-file timeout** — `--timeout` (default 300s) stops one hung document or stalled vision call from freezing the whole batch.
- **Per-file error isolation** — a corrupt file is logged in the manifest and the batch continues; the report lists every failure.
- **LLM image descriptions + OCR** — `--use-llm` routes an OpenAI-compatible client at OpenRouter (team key) for image descriptions and `markitdown-ocr` embedded-image OCR, so scanned PDFs and image-heavy decks produce real text.

## Default output

`~/Documents/GitHub/document-analysis/sources-md/` (mirrored input tree), with `.markitdown-manifest.json` in the output root. Override with `--out`.

## Supported formats

Document set by default: PDF, `.docx`, `.pptx`, `.xlsx`/`.xls`, HTML, CSV/TSV, JSON, XML, text, Markdown, EPub. Audio / YouTube / Outlook are opt-in extras. Full map in `references/formats-and-extras.md`.

## Reference files

| File | Purpose |
|------|---------|
| `formats-and-extras.md` | Format ↔ dependency-group map; OCR and Azure DI options; sandbox notes. |
| `frontmatter-schema.md` | Output frontmatter fields + the manifest format. |

## Pipeline position

```
documents  →  [markitdown]  →  sources-md/*.md (+ frontmatter, manifest)  →  document-analysis pipeline
```

This plugin converts and hands off. It does not analyze content, and it does not commit output to git — that's a separate, human-driven step.

## Attribution

Wraps [MarkItDown](https://github.com/microsoft/markitdown) by Microsoft, MIT License. The MarkItDown project also ships `markitdown-mcp` (a single-tool MCP server); this plugin deliberately uses the CLI/Python API instead so it can add batch conversion, provenance, idempotency, and output routing, and so it runs natively in the Cowork sandbox.

## Version History

- **0.1.1** — Settings-aware idempotency: the skip check now compares `ocr` / `llm_model` / `converter_version` alongside the source hash, so a later `--use-llm` run re-OCRs files that were converted text-only (closes a silent-skip trap) and a markitdown upgrade re-converts. Added a per-file `--timeout` (default 300s) so a hung document or stalled vision call fails that file instead of freezing the batch. Single timestamp per file (frontmatter and manifest now agree).
- **0.1.0** — Initial release. `/markitdown-setup`, `/markitdown-convert`, the `convert.py` driver (batch, frontmatter, manifest, error isolation, OpenRouter LLM/OCR), and the formats + frontmatter references.
