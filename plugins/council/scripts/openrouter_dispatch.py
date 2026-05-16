#!/usr/bin/env python3
"""
Parallel OpenRouter dispatcher for Council deliberation.

Calls N OpenRouter chat completions concurrently and writes each response as a
JSON file to an output directory, so the calling skill can read them back.

Usage:
    python3 openrouter_dispatch.py \\
        --jobs jobs.json \\
        --out /path/to/output-dir \\
        [--timeout 180]

`jobs.json` shape:
    [
        {
            "id": "round1-deepseek",
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": "..."}],
            "temperature": 0.7,
            "max_tokens": 4096
        },
        ...
    ]

Output: one file per job at `{out}/{id}.json`, each containing either:
    {"id": "...", "ok": true,  "response": <openrouter response>}
or
    {"id": "...", "ok": false, "error": "<message>"}

Reads OPENROUTER_API_KEY from the environment. Fails fast if unset.

Designed to be called from inside Cowork via `mcp__workspace__bash`. Pure-stdlib
to avoid pip install steps in the sandbox; uses urllib for HTTPS.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_openrouter(job: dict, api_key: str, timeout: int) -> dict:
    """Single OpenRouter call. Returns a result dict; never raises."""
    payload = {
        "model": job["model"],
        "messages": job["messages"],
    }
    for k in ("temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"):
        if k in job:
            payload[k] = job[k]

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/MoxyWolfLLC/moxywolf-plugins",
            "X-Title": "MoxyWolf Council",
        },
    )

    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
        return {
            "id": job["id"],
            "ok": True,
            "model": job["model"],
            "elapsed_sec": round(time.time() - started, 2),
            "response": data,
        }
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        return {
            "id": job["id"],
            "ok": False,
            "model": job["model"],
            "elapsed_sec": round(time.time() - started, 2),
            "error": f"HTTP {e.code}: {err_body[:500]}",
        }
    except Exception as e:
        return {
            "id": job["id"],
            "ok": False,
            "model": job["model"],
            "elapsed_sec": round(time.time() - started, 2),
            "error": f"{type(e).__name__}: {e}",
        }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jobs", required=True, help="Path to jobs.json")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--timeout", type=int, default=180, help="Per-call timeout in seconds (default: 180)")
    p.add_argument("--max-workers", type=int, default=6, help="Max parallel calls (default: 6)")
    args = p.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "ERROR: OPENROUTER_API_KEY not set in environment.\n"
            "Add to ~/.zshrc:  export OPENROUTER_API_KEY='sk-or-v1-...'\n"
            "Then source the rc and restart Cowork.",
            file=sys.stderr,
        )
        return 2

    jobs_path = Path(args.jobs)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = json.loads(jobs_path.read_text())
    if not isinstance(jobs, list) or not jobs:
        print(f"ERROR: {jobs_path} must contain a non-empty JSON array.", file=sys.stderr)
        return 2

    started = time.time()
    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futs = {ex.submit(call_openrouter, j, api_key, args.timeout): j for j in jobs}
        for fut in cf.as_completed(futs):
            r = fut.result()
            results.append(r)
            (out_dir / f"{r['id']}.json").write_text(json.dumps(r, indent=2))

    summary = {
        "total": len(jobs),
        "ok": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "wall_sec": round(time.time() - started, 2),
        "per_job": [
            {"id": r["id"], "model": r["model"], "ok": r["ok"], "elapsed_sec": r["elapsed_sec"]}
            for r in results
        ],
    }
    (out_dir / "_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
