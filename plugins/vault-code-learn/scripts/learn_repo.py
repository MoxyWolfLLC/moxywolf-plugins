#!/usr/bin/env python3
"""
learn_repo.py — Helper for the vault-code-learn skill.

Given a repo path, produces a JSON payload that the SKILL.md narrative wraps into
Markdown. Stays mechanical: file discovery, manifest parsing, naming-convention
sampling, import frequency. The skill itself does the human-readable synthesis.

Usage:
    learn_repo.py <repo_path> [--since <iso-timestamp>] [--cap 300]

Output: JSON to stdout. Never writes files. Never modifies the repo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_DIRS = {
    "node_modules", "dist", "build", ".next", "vendor", "__pycache__",
    ".venv", "venv", ".git", ".turbo", ".cache", "target",
}
EXCLUDE_EXACT = {
    "package-lock.json", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock",
    "yarn.lock", "uv.lock",
}
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".woff", ".woff2", ".ttf",
    ".mp4", ".mov", ".webm", ".mp3", ".wav", ".pt", ".bin", ".onnx",
}


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True, stderr=subprocess.DEVNULL).strip()


def head_sha(repo: Path) -> str:
    try:
        return run(["git", "rev-parse", "HEAD"], repo)
    except Exception:
        return ""


def tracked_files(repo: Path) -> list[Path]:
    try:
        out = run(["git", "ls-files"], repo)
    except Exception:
        return []
    files = []
    for line in out.splitlines():
        p = repo / line
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.name in EXCLUDE_EXACT:
            continue
        if p.suffix.lower() in BINARY_EXTS:
            continue
        files.append(p)
    return files


def mtime_since(repo: Path, files: list[Path], since_epoch: float | None) -> list[Path]:
    if since_epoch is None:
        return files
    keep = []
    for f in files:
        try:
            ct = float(run(["git", "log", "-1", "--format=%ct", "--", str(f.relative_to(repo))], repo))
            if ct >= since_epoch:
                keep.append(f)
        except Exception:
            continue
    return keep


def parse_manifests(repo: Path) -> dict:
    out: dict = {"language": [], "package_manager": None, "frameworks": [], "scripts": {}}
    pkg = repo / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            out["language"].append("javascript/typescript")
            if (repo / "pnpm-lock.yaml").exists():
                out["package_manager"] = "pnpm"
            elif (repo / "yarn.lock").exists():
                out["package_manager"] = "yarn"
            else:
                out["package_manager"] = "npm"
            out["scripts"] = data.get("scripts", {})
            deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
            for marker, fw in [("next", "Next.js"), ("react", "React"), ("vue", "Vue"),
                               ("svelte", "Svelte"), ("astro", "Astro"), ("vite", "Vite"),
                               ("vitest", "Vitest"), ("jest", "Jest"), ("playwright", "Playwright")]:
                if marker in deps:
                    out["frameworks"].append(fw)
        except Exception:
            pass
    pyproj = repo / "pyproject.toml"
    if pyproj.exists():
        out["language"].append("python")
        body = pyproj.read_text()
        if "[tool.poetry]" in body:
            out["package_manager"] = "poetry"
        elif "[tool.uv]" in body or "uv.lock" in [p.name for p in repo.iterdir() if p.is_file()]:
            out["package_manager"] = "uv"
        else:
            out["package_manager"] = out["package_manager"] or "pip"
        for marker, fw in [("fastapi", "FastAPI"), ("django", "Django"), ("flask", "Flask"),
                           ("pydantic", "Pydantic"), ("pytest", "pytest"), ("ruff", "Ruff"),
                           ("mypy", "mypy")]:
            if marker in body.lower():
                out["frameworks"].append(fw)
    if (repo / "Cargo.toml").exists():
        out["language"].append("rust")
        out["package_manager"] = "cargo"
    if (repo / "go.mod").exists():
        out["language"].append("go")
        out["package_manager"] = "go-modules"
    return out


IMPORT_RE = {
    ".js": re.compile(r"""(?:^|\n)\s*(?:import\s+[^"']*from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\))"""),
    ".ts": re.compile(r"""(?:^|\n)\s*(?:import\s+[^"']*from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\))"""),
    ".tsx": re.compile(r"""(?:^|\n)\s*(?:import\s+[^"']*from\s+['"]([^'"]+)['"])"""),
    ".jsx": re.compile(r"""(?:^|\n)\s*(?:import\s+[^"']*from\s+['"]([^'"]+)['"])"""),
    ".py": re.compile(r"""(?:^|\n)\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))"""),
}


def import_frequency(files: list[Path], repo: Path) -> tuple[Counter, Counter]:
    internal = Counter()
    third_party = Counter()
    for f in files:
        ext = f.suffix.lower()
        rgx = IMPORT_RE.get(ext)
        if rgx is None:
            continue
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        for m in rgx.finditer(text):
            name = next((g for g in m.groups() if g), "")
            if not name:
                continue
            if name.startswith(".") or name.startswith("@/") or name.startswith("~/"):
                internal[name] += 1
            else:
                third_party[name.split("/")[0] if name.startswith("@") else name.split(".")[0]] += 1
    return internal, third_party


def naming_sample(files: list[Path]) -> dict:
    samples = {"file_names": [], "directories": []}
    for f in files[:50]:
        samples["file_names"].append(f.name)
        if f.parent != f.parent.parent:
            samples["directories"].append(f.parent.name)
    return samples


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--since", default=None, help="ISO 8601; only files modified since this time")
    ap.add_argument("--cap", type=int, default=300)
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        print(json.dumps({"error": f"not a git repo: {repo}"}))
        return 1

    since_epoch = None
    if args.since:
        try:
            since_epoch = datetime.fromisoformat(args.since.replace("Z", "+00:00")).timestamp()
        except Exception:
            pass

    files = tracked_files(repo)
    files = mtime_since(repo, files, since_epoch)
    truncated = False
    if len(files) > args.cap:
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        files = files[: args.cap]
        truncated = True

    manifests = parse_manifests(repo)
    internal, third_party = import_frequency(files, repo)
    samples = naming_sample(files)

    out = {
        "repo": repo.name,
        "repo_path": str(repo),
        "head_sha": head_sha(repo),
        "now_utc": datetime.now(timezone.utc).isoformat(),
        "files_in_scope": len(files),
        "files_truncated": truncated,
        "manifests": manifests,
        "top_internal_imports": internal.most_common(10),
        "top_third_party_imports": third_party.most_common(10),
        "naming_sample": samples,
        "top_level_dirs": sorted({p.relative_to(repo).parts[0] for p in files if len(p.relative_to(repo).parts) > 1}),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
