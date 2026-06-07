#!/usr/bin/env python3
"""
markitdown plugin — batch document → Markdown driver.

Wraps Microsoft MarkItDown with the workflow MoxyWolf needs around it:
  - single file OR recursive folder conversion, mirroring the input tree
  - YAML frontmatter on every output (provenance for Obsidian / research-pipeline)
  - a hash-based manifest so unchanged sources are skipped on re-run (idempotent)
  - per-file error isolation (one bad file never kills the batch)
  - optional LLM image descriptions + embedded-image OCR via an OpenAI-compatible
    client (the team OpenRouter key), when --use-llm is passed

Paths are explicit absolute paths. The calling command resolves the correct
sandbox mount for the input and output before invoking this script, so the
driver itself stays portable and never hardcodes a session path.

Exit code is 0 if every file converted or was skipped, 1 if any file failed.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import traceback

# Extension -> source_type. Document set + native text formats.
SUPPORTED = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".html": "html",
    ".htm": "html",
    ".csv": "csv",
    ".tsv": "tsv",
    ".json": "json",
    ".xml": "xml",
    ".txt": "text",
    ".md": "markdown",
    ".epub": "epub",
}

MANIFEST_NAME = ".markitdown-manifest.json"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_pt_iso():
    # Best-effort Pacific stamp; falls back to local if zoneinfo is unavailable.
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds")
    except Exception:
        return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def yaml_escape(value):
    s = str(value)
    if any(c in s for c in ':#"\'\n') or s != s.strip():
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


def build_frontmatter(meta):
    lines = ["---"]
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {yaml_escape(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def discover_inputs(input_path, recursive):
    if os.path.isfile(input_path):
        return [input_path], os.path.dirname(input_path) or "."
    files = []
    if recursive:
        for root, _dirs, names in os.walk(input_path):
            for n in names:
                if os.path.splitext(n)[1].lower() in SUPPORTED:
                    files.append(os.path.join(root, n))
    else:
        for n in sorted(os.listdir(input_path)):
            p = os.path.join(input_path, n)
            if os.path.isfile(p) and os.path.splitext(n)[1].lower() in SUPPORTED:
                files.append(p)
    return sorted(files), input_path


def resolve_openrouter_key(env_file):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    if env_file and os.path.isfile(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.replace("export", "").strip() == "OPENROUTER_API_KEY":
                    return v.strip().strip('"').strip("'")
    return ""


def make_markitdown(use_llm, llm_model, openrouter_env):
    from markitdown import MarkItDown
    if not use_llm:
        return MarkItDown(enable_plugins=False), False, None
    key = resolve_openrouter_key(openrouter_env)
    if not key:
        sys.stderr.write(
            "WARN: --use-llm requested but no OpenRouter key found "
            "(OPENROUTER_API_KEY env or --openrouter-env file). "
            "Falling back to text-only conversion.\n"
        )
        return MarkItDown(enable_plugins=False), False, None
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    # enable_plugins=True activates markitdown-ocr (if installed) for embedded-image OCR.
    md = MarkItDown(enable_plugins=True, llm_client=client, llm_model=llm_model)
    return md, True, llm_model


def main():
    ap = argparse.ArgumentParser(description="Batch document -> Markdown via MarkItDown.")
    ap.add_argument("--input", required=True, help="Absolute path to a file or folder.")
    ap.add_argument("--out", required=True, help="Absolute path to the output folder.")
    ap.add_argument("--no-recursive", action="store_true", help="Do not descend into subfolders.")
    ap.add_argument("--formats", default="", help="Comma list of source_types to include (e.g. pdf,docx). Default: all supported.")
    ap.add_argument("--use-llm", action="store_true", help="Enable LLM image descriptions + embedded-image OCR.")
    ap.add_argument("--llm-model", default=os.environ.get("MARKITDOWN_LLM_MODEL", "openai/gpt-4o"), help="OpenRouter vision model slug.")
    ap.add_argument("--openrouter-env", default="", help="Path to openrouter.env if OPENROUTER_API_KEY isn't already exported.")
    ap.add_argument("--force", action="store_true", help="Re-convert even if the source hash is unchanged.")
    args = ap.parse_args()

    input_path = os.path.abspath(args.input)
    out_dir = os.path.abspath(args.out)
    if not os.path.exists(input_path):
        sys.stderr.write(f"ERROR: input not found: {input_path}\n")
        return 2
    os.makedirs(out_dir, exist_ok=True)

    fmt_filter = {f.strip().lower() for f in args.formats.split(",") if f.strip()}
    files, base = discover_inputs(input_path, recursive=not args.no_recursive)
    if fmt_filter:
        files = [f for f in files if SUPPORTED.get(os.path.splitext(f)[1].lower()) in fmt_filter]
    if not files:
        sys.stderr.write("Nothing to convert — no supported files matched the input/filter.\n")
        return 0

    manifest_path = os.path.join(out_dir, MANIFEST_NAME)
    manifest = {}
    if os.path.isfile(manifest_path):
        try:
            manifest = json.load(open(manifest_path))
        except Exception:
            manifest = {}

    md, ocr_on, model_used = make_markitdown(args.use_llm, args.llm_model, args.openrouter_env or None)

    converted, skipped, failed = [], [], []

    for src in files:
        rel = os.path.relpath(src, base) if os.path.isdir(input_path) else os.path.basename(src)
        out_path = os.path.join(out_dir, rel + ".md")
        src_type = SUPPORTED.get(os.path.splitext(src)[1].lower(), "unknown")
        try:
            digest = sha256_of(src)
            prior = manifest.get(rel)
            if (not args.force and prior and prior.get("sha256") == digest
                    and prior.get("status") == "ok" and os.path.isfile(out_path)):
                skipped.append(rel)
                continue

            result = md.convert(src)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            fm = build_frontmatter({
                "source_file": rel,
                "source_type": src_type,
                "sha256": digest,
                "bytes": os.path.getsize(src),
                "converted_at": now_pt_iso(),
                "converter": "markitdown",
                "converter_version": _mid_version(),
                "ocr": ocr_on,
                "llm_model": model_used,
                "title": os.path.splitext(os.path.basename(src))[0],
            })
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(fm)
                f.write(result.text_content or "")
            manifest[rel] = {"source": src, "sha256": digest, "out": out_path,
                             "converted_at": now_pt_iso(), "status": "ok",
                             "ocr": ocr_on, "source_type": src_type}
            converted.append(rel)
        except Exception as e:  # per-file isolation
            manifest[rel] = {"source": src, "status": "error",
                             "error": f"{type(e).__name__}: {e}", "source_type": src_type}
            failed.append((rel, f"{type(e).__name__}: {e}"))
            sys.stderr.write(f"FAILED {rel}: {type(e).__name__}: {e}\n")
            sys.stderr.write(traceback.format_exc(limit=1))

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print("CONVERSION REPORT")
    print("=================")
    print(f"Input:   {input_path}")
    print(f"Output:  {out_dir}")
    print(f"Engine:  markitdown {_mid_version()}  |  LLM/OCR: {'on (' + str(model_used) + ')' if ocr_on else 'off'}")
    print(f"Converted: {len(converted)}   Skipped (unchanged): {len(skipped)}   Failed: {len(failed)}")
    if failed:
        print("\nFailures:")
        for rel, err in failed:
            print(f"  - {rel}: {err}")
    print(f"\nManifest: {manifest_path}")
    return 1 if failed else 0


def _mid_version():
    try:
        import importlib.metadata as m
        return m.version("markitdown")
    except Exception:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
