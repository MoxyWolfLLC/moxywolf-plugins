---
description: Extract glossary terms from converted Markdown into a lexicon /glossary-promote package
allowed-tools: Bash, Read
argument-hint: <markdown-file> --framework <NAME> --source-slug <slug> [--out <dir>] [--category <cat>]
---

Interactive wrapper over the `document-analysis` repo's glossary extractor. Takes a converted Markdown file (from `/markitdown-convert`'s `sources-md/` tree), locates glossary/definition sections, extracts term/definition pairs, and writes a `/glossary-promote` package that lexicon-workbench's `import-glossary.ts` ingests.

This command is a thin wrapper — the real logic lives in the `document-analysis` repo (`docanalysis/`), so the same code runs here and in GitHub Actions. See DR-001.

Read the document-analysis skill for context.

## Step 1: Resolve the repo and inputs

```bash
REPO="$(ls -d /sessions/*/mnt/GitHub/document-analysis 2>/dev/null | head -1)"
[ -z "$REPO" ] && { echo "document-analysis repo not mounted — add the GitHub folder in Cowork → Folders"; exit 1; }
```

Parse `$ARGUMENTS`: the input markdown path, `--framework`, `--source-slug`, optional `--out` (default `$REPO/packages/<source-slug>`) and `--category` (default `regulatory_compliance`). Framework + source-slug are **operator-supplied** per source (DR-001) — don't infer them from the document.

## Step 2: Ensure deps

```bash
pip install pydantic pyyaml --break-system-packages -q
```

(The deterministic table/inline extraction needs no LLM key. To enable the prose LLM lane, export `OPENROUTER_API_KEY` first — but that lane is currently a stub; see the repo README.)

## Step 3: Run the extractor

```bash
PYTHONPATH="$REPO" python3 -m docanalysis.cli \
  --input "<markdown-file>" \
  --framework "<NAME>" \
  --source-slug "<slug>" \
  --out "<out-dir>"
```

## Step 4: Report

Relay the CLI's summary: spans located, terms extracted, and the package path (`<source>--CONSOLIDATED--<date>.jsonl`, `manifest.json`, `promotion-signoff-<date>.md`). Exit-code meanings: `0` terms written; `3` a section was found but yielded no terms (prose — needs the LLM lane); `4` no glossary detected.

## Notes

- **Review before import.** The package is for human review, then `import-glossary.ts` against a Supabase **preview branch** before production (DR-001 gate). This command never writes the lexicon DB.
- **Conversion is upstream.** Run `/markitdown-convert` first to produce the Markdown; this command consumes it.
