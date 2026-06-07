---
description: Install MarkItDown + document-set extras + OCR in the sandbox and verify readiness
allowed-tools: Bash, Read
argument-hint: [--with-audio | --all]
---

Prepare the Cowork sandbox to convert documents. Run this once per session before `/markitdown-convert`.

Read the markitdown skill for context.

## Step 1: Install

Default install is the document set plus OCR and an OpenAI-compatible client:

```bash
pip install 'markitdown[pdf,docx,pptx,xlsx]' markitdown-ocr openai --break-system-packages -q 2>&1 | tail -3
```

Parse `$ARGUMENTS`:
- `--with-audio` → also `pip install 'markitdown[audio-transcription]'`.
- `--all` → install `'markitdown[all]'` instead (audio, YouTube, Outlook, everything). Heavier.

## Step 2: Verify the toolchain

```bash
python3 -c "import markitdown, importlib.metadata as m; print('markitdown', m.version('markitdown'))"
python3 -c "import markitdown_ocr; print('markitdown-ocr present')" 2>/dev/null || echo "markitdown-ocr NOT installed (OCR will be skipped)"
which ffmpeg >/dev/null && echo "ffmpeg: present" || echo "ffmpeg: absent (audio only)"
which exiftool >/dev/null && echo "exiftool: present" || echo "exiftool: absent (image EXIF only — fine for documents)"
```

## Step 3: Resolve the OpenRouter key (for --use-llm conversions)

The team key lives at `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/openrouter.env`. Resolve the mount and report status without echoing the key:

```bash
KEY_FILE="$(ls -d /sessions/*/mnt/MoxyWolf\ Vault 2>/dev/null | head -1)/_Shared Knowledge/Agents and Plugins/openrouter.env"
if [ -f "$KEY_FILE" ] && grep -qE 'OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*["'\'']?sk-or-v1-' "$KEY_FILE"; then
  echo "OpenRouter key: resolved (LLM/OCR available)"
else
  echo "OpenRouter key: not resolved — --use-llm will fall back to text-only"
fi
```

## Step 4: Report

Print a short readiness summary: markitdown version, OCR plugin present?, ffmpeg/exiftool, OpenRouter key resolved?. State whether `/markitdown-convert --use-llm` is available or will fall back to text-only. Do not print the key value.
