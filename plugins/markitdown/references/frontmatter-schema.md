# Output Frontmatter Schema

Every Markdown file the driver writes opens with a YAML frontmatter block, then the MarkItDown body. The frontmatter is the provenance record that lets Obsidian, the research-pipeline, and the document-analysis pipeline treat converted files as first-class, traceable sources.

## Fields

```yaml
---
source_file: contracts/2026/msa-acme.pdf      # path relative to the input root (mirrored in the output tree)
source_type: pdf                              # pdf | docx | pptx | xlsx | xls | html | csv | tsv | json | xml | text | markdown | epub
sha256: 9f2c…							        # SHA-256 of the source bytes — the idempotency key
bytes: 184302                                 # source file size
converted_at: 2026-06-07T16:40:12-07:00       # ISO 8601, Pacific time
converter: markitdown
converter_version: 0.1.5                       # resolved markitdown package version
ocr: true                                     # true if LLM/OCR was active for this run
llm_model: openai/gpt-4o                       # model used when ocr is true; omitted otherwise
title: msa-acme                               # source filename without extension
---
```

## Rules

- `sha256` is the **idempotency key**, but it is *not the only* skip condition. On re-run, a source is skipped only when its hash matches the manifest entry **and** the effective conversion settings (`ocr`, `llm_model`, `converter_version`) also match **and** the output still exists. This means a later `--use-llm` run re-OCRs files that were previously converted text-only (different `ocr`/`llm_model`), and a markitdown upgrade (different `converter_version`) re-converts everything. `--force` skips the check entirely.
- `ocr` reflects whether the LLM/OCR path actually ran (not just whether `--use-llm` was requested — if no key resolved, it falls back to text-only and `ocr: false`).
- `llm_model` is only written when `ocr: true`.
- `converted_at` is Pacific per MoxyWolf convention.
- Values containing YAML-special characters are quoted/escaped by the driver.

## Manifest (separate file)

Alongside the outputs, `.markitdown-manifest.json` in the output root holds one entry per source keyed by the mirrored relative path:

```json
{
  "contracts/2026/msa-acme.pdf": {
    "source": "/abs/path/contracts/2026/msa-acme.pdf",
    "sha256": "9f2c…",
    "out": "/abs/out/contracts/2026/msa-acme.pdf.md",
    "converted_at": "2026-06-07T16:40:12-07:00",
    "status": "ok",
    "ocr": true,
    "llm_model": "openai/gpt-4o",
    "converter_version": "0.1.5",
    "source_type": "pdf"
  },
  "broken/scan.pdf": {
    "source": "/abs/path/broken/scan.pdf",
    "status": "error",
    "error": "FileConversionException: …",
    "source_type": "pdf"
  }
}
```

The manifest is the audit trail and the skip-list. Failed files carry `status: error` and the reason (including `TimeoutError` when a file exceeds `--timeout`), so a later run can retry just those — and because the skip check compares `ocr` / `llm_model` / `converter_version`, re-running a failed-or-text-only file with `--use-llm` actually re-processes it rather than skipping.
