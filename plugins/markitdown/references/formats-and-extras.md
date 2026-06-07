# Formats ↔ Dependency Extras

MarkItDown splits its file-format support into optional dependency groups. This plugin installs the **document set** by default; other groups are opt-in.

## Installed by default (`/markitdown-setup`)

```
pip install 'markitdown[pdf,docx,pptx,xlsx]' markitdown-ocr openai
```

| Format | Extension(s) | Extra needed | Notes |
|--------|-------------|-------------|-------|
| PDF | `.pdf` | `[pdf]` | Text-layer extraction. Scanned PDFs need `--use-llm` (OCR) or Azure DI. |
| Word | `.docx` | `[docx]` | Headings, lists, tables, links preserved. |
| PowerPoint | `.pptx` | `[pptx]` | Slide text + speaker notes; image descriptions with `--use-llm`. |
| Excel (modern) | `.xlsx` | `[xlsx]` | Each sheet → a Markdown table. |
| Excel (legacy) | `.xls` | `[xls]` | Older binary Excel. Add `[xls]` if needed. |
| HTML | `.html`, `.htm` | none (core) | Structure-preserving. |
| CSV / TSV | `.csv`, `.tsv` | none (core) | → Markdown tables. |
| JSON / XML | `.json`, `.xml` | none (core) | Text-based formats. |
| Plain text / Markdown | `.txt`, `.md` | none (core) | Passed through / normalized. |
| EPub | `.epub` | none (core) | Chapter text. |
| ZIP | `.zip` | none (core) | Recurses over contents; output concatenated. Use deliberately. |

## Not installed by default (opt-in)

| Group | Flag | Covers |
|-------|------|--------|
| `[audio-transcription]` | `/markitdown-setup --with-audio` | `.wav` / `.mp3` speech → text (sandbox has `ffmpeg`). |
| `[youtube-transcription]` | add manually | Fetches YouTube transcript from a URL. |
| `[outlook]` | add manually | `.msg` Outlook messages. |
| `[all]` | `/markitdown-setup --all` | Everything above in one shot. Heaviest install. |

## OCR and high-fidelity options

- **`markitdown-ocr` (installed):** LLM-vision OCR of images embedded in PDF/DOCX/PPTX/XLSX. Activated by `--use-llm` (needs the OpenRouter key + `enable_plugins=True`). No extra ML/binary deps. If no LLM client resolves, OCR is silently skipped and the standard converter runs.
- **LLM image descriptions (built-in):** the same `--use-llm` path describes images in PPTX and image files.
- **Azure Document Intelligence (not wired):** MarkItDown supports `-d -e <endpoint>` / `docintel_endpoint=` for high-fidelity PDF. Out of scope for this plugin; wire it later if a corpus needs layout-faithful extraction beyond LLM-OCR.

## Sandbox notes

- Python 3.10+ required (sandbox has 3.10.12).
- `ffmpeg` present; `exiftool` absent (image EXIF only — irrelevant to documents).
- The `mammoth` console-script PATH warning on install is harmless (the driver uses the Python API).
- A benign `onnxruntime cpuid_info` warning prints on import.
