---
description: Convert a file or folder to Markdown — mirrored tree, frontmatter, manifest, optional OCR
allowed-tools: Bash, Read, AskUserQuestion
argument-hint: [input-path] [--out <dir>] [--formats pdf,docx,...] [--use-llm] [--force] [--no-recursive] [--timeout <secs>]
---

Convert documents to Markdown via the markitdown driver. Single file or a whole folder.

Read the document-analysis skill for context. If `markitdown` isn't importable yet, run `/markitdown-setup` first (or do the install inline).

## Step 1: Resolve input and output paths

`$ARGUMENTS` carries the input path and flags. Resolve real **sandbox** paths — never assume `/mnt/...`:

- **Input.** If the user names a folder or file, resolve its sandbox mount (`ls -d /sessions/*/mnt/...`). Uploaded files are under the session `uploads/` mount.
- **Output.** Default target is the document-analysis repo's `sources-md/` tree:
  ```bash
  DA="$(ls -d /sessions/*/mnt/GitHub/document-analysis 2>/dev/null | head -1)"
  OUT="$DA/sources-md"
  ```
  If `--out <dir>` is given, use that instead. If the document-analysis mount isn't found, tell the user to add the GitHub folder in Cowork → Folders (or pass `--out`), and stop.

Confirm the resolved input and output paths with the user in one line before a large batch.

## Step 2: Decide LLM/OCR

- `--use-llm` present → enable image descriptions + OCR. Resolve the OpenRouter key file:
  ```bash
  KEY_FILE="$(ls -d /sessions/*/mnt/MoxyWolf\ Vault 2>/dev/null | head -1)/_Shared Knowledge/Agents and Plugins/openrouter.env"
  ```
  Pass it via `--openrouter-env "$KEY_FILE"`.
- Not present → text-only (faster, no API cost). If the input looks scanned/image-heavy (PDFs of scans, slide decks), mention once that `--use-llm` would extract more, but don't force it.

## Step 3: Run the driver

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/convert.py" \
  --input "<resolved-input>" \
  --out "<resolved-out>" \
  [--formats <list>] [--use-llm --openrouter-env "$KEY_FILE"] [--force] [--no-recursive] [--timeout <secs>]
```

For a large folder with `--use-llm` (many vision calls can run long), launch it with the Bash tool's `run_in_background` and tell the user to check back; otherwise run in the foreground. Each file has a `--timeout` (default 300s; `0` disables) so a single hung document or stalled vision call fails that file and the batch keeps going.

## Step 4: Report

Relay the driver's CONVERSION REPORT: converted / skipped / failed counts, the output path, and any per-file failures with their reasons. If files failed, offer next steps (e.g. `--use-llm` for a scanned PDF that produced empty output, or noting an unsupported format).

## Notes

- The driver is **idempotent** — re-running skips a file only when its source hash *and* its conversion settings (`ocr`/`llm_model`/`converter_version`) are unchanged. So re-running with `--use-llm` re-OCRs files that were previously text-only; a markitdown upgrade re-converts everything. Use `--force` to re-convert regardless.
- Output is **not committed**. Converted Markdown lands in `document-analysis/sources-md/`; committing it to the repo is a separate, human-driven step.
- This command converts only. Analysis of the resulting Markdown is downstream (document-analysis pipeline), not here.
