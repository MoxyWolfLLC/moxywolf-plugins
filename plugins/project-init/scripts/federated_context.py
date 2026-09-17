#!/usr/bin/env python3
"""Build a provenance-aware context packet from project, code, and memory planes."""

from __future__ import annotations

import argparse
import heapq
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_surfaces import SurfaceError, resolve_project


IGNORED_DIRECTORIES = {".git", ".venv", "node_modules", "vendor", "dist", "build", "__pycache__"}
SOURCE_LIMIT = 200
INTENT_DOMAINS = {
    "current-work": "current-project-work",
    "code-behavior": "executable-technical-truth",
    "historical-rationale": "institutional-rationale",
    "company-knowledge": "institutional-memory",
}


def _read_declaration(plugin_root: Path) -> dict[str, Any]:
    path = plugin_root / "vault-context.json"
    try:
        declaration = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SurfaceError(f"Cannot read plugin context declaration {path}: {exc}") from exc
    if declaration.get("schema_version") != 1 or not isinstance(declaration.get("planes"), dict):
        raise SurfaceError(f"Invalid plugin context declaration: {path}")
    return declaration


def _source(path: Path, plane: str, authority: str, kind: str = "document") -> dict[str, Any]:
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_days = (datetime.now(timezone.utc) - modified).days
    return {
        "path": str(path),
        "plane": plane,
        "authority": authority,
        "kind": kind,
        "modified_at": modified.isoformat(),
        "freshness": "stale" if age_days > 30 else "current",
    }


def _collect_markdown(root: Path, plane: str, authority: str) -> tuple[list[dict[str, Any]], bool]:
    if not root.exists():
        return [], False
    sources: list[dict[str, Any]] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in IGNORED_DIRECTORIES)
        for name in sorted(files):
            if not name.casefold().endswith(".md"):
                continue
            sources.append(_source(Path(current) / name, plane, authority))
            if len(sources) >= SOURCE_LIMIT:
                return sources, True
    return sources, False


def _collect_recent_decisions(root: Path) -> tuple[list[dict[str, Any]], bool]:
    if not root.exists():
        return [], False
    newest: list[tuple[float, str]] = []
    matches = 0
    for current, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in IGNORED_DIRECTORIES)
        for name in sorted(files):
            if not name.startswith("DR-") or not name.casefold().endswith(".md"):
                continue
            path = Path(current) / name
            matches += 1
            item = (path.stat().st_mtime, str(path))
            if len(newest) < SOURCE_LIMIT:
                heapq.heappush(newest, item)
            elif item > newest[0]:
                heapq.heapreplace(newest, item)
    sources = [_source(Path(path), "company-memory", "authored") for _, path in newest]
    sources.sort(key=lambda source: source["modified_at"], reverse=True)
    return sources, matches > SOURCE_LIMIT


def build_context(
    *,
    project: str,
    intent: str,
    plugin_root: Path,
    taskade_root: Path,
    vault_root: Path,
    github_root: Path,
) -> dict[str, Any]:
    declaration = _read_declaration(plugin_root)
    surfaces = resolve_project(project, taskade_root, vault_root, github_root)
    planes = declaration["planes"]
    if planes.get("project_workspace") == "required" and not surfaces["workspace"]["available"]:
        raise SurfaceError("Required project-workspace plane is unavailable")
    if planes.get("company_memory") == "required" and not surfaces["memory"]["available"]:
        raise SurfaceError("Required company-memory plane is unavailable")
    available_repositories = [repo for repo in surfaces["repositories"] if repo["available"]]
    if planes.get("repositories") == "required" and not available_repositories:
        raise SurfaceError("Required code-workspace plane is unavailable")

    warnings = list(surfaces["warnings"])
    project_sources: list[dict[str, Any]] = []
    if planes.get("project_workspace") != "none" and surfaces["workspace"]["available"]:
        project_sources, truncated = _collect_markdown(
            Path(surfaces["workspace"]["path"]), "project-workspace", "operational"
        )
        if truncated:
            warnings.append(f"Project-workspace source limit reached: {SOURCE_LIMIT}")
    code_sources: list[dict[str, Any]] = []
    if planes.get("repositories") != "none":
        for repository in available_repositories:
            code_sources.append(
                _source(Path(repository["path"]), "code-workspace", "live-code", kind="repository-root")
            )

    memory_root = Path(surfaces["memory"]["path"])
    memory_sources: list[dict[str, Any]] = []
    scopes = set(declaration.get("memory_scopes", []))
    moc = Path(surfaces["memory"]["moc"])
    if planes.get("company_memory") != "none":
        if "project-moc" in scopes and moc.exists():
            memory_sources.append(_source(moc, "company-memory", "authored"))
        if "recent-decisions" in scopes and memory_root.exists():
            decisions, truncated = _collect_recent_decisions(memory_root)
            memory_sources.extend(decisions)
            if truncated:
                warnings.append(f"Company-memory source limit reached while finding decisions: {SOURCE_LIMIT}")
        if "shared-operating-norms" in scopes:
            norms, truncated = _collect_markdown(
                vault_root / "_Shared Knowledge" / "Operating Norms", "company-memory", "authored"
            )
            memory_sources.extend(norms)
            if truncated:
                warnings.append(f"Shared operating-norm source limit reached: {SOURCE_LIMIT}")
        if "derived-graphs" in scopes:
            graphs, truncated = _collect_markdown(
                memory_root / "06-Engineering" / "graphs", "company-memory", "derived"
            )
            memory_sources.extend(graphs)
            if truncated:
                warnings.append(f"Derived-graph source limit reached: {SOURCE_LIMIT}")

    excluded: list[dict[str, str]] = []
    credential_locations = [
        vault_root / "_Shared Knowledge" / "Agents and Plugins" / "openrouter.env",
        vault_root / "_Shared Knowledge" / "Agents and Plugins" / "github-pat.env",
    ]
    for path in credential_locations:
        if path.exists():
            excluded.append({"path": str(path), "reason": "credential-bearing files are excluded from model context"})

    if intent == "current-work":
        order = {"project-workspace": 0, "company-memory": 1, "code-workspace": 2}
    elif intent == "code-behavior":
        order = {"code-workspace": 0, "project-workspace": 1, "company-memory": 2}
    else:
        order = {"company-memory": 0, "project-workspace": 1, "code-workspace": 2}
    sources = project_sources + code_sources + memory_sources
    if intent == "historical-rationale":
        sources.sort(key=lambda item: (0 if Path(item["path"]).name.startswith("DR-") else 1, order[item["plane"]], item["path"]))
    else:
        sources.sort(key=lambda item: (order[item["plane"]], 1 if item["authority"] == "derived" else 0, item["path"]))

    stale = [source["path"] for source in sources if source["freshness"] == "stale"]
    if stale:
        warnings.append(f"Stale context sources detected: {len(stale)}")
    return {
        "schema_version": 1,
        "project_id": surfaces["project_id"],
        "intent": intent,
        "authority_domain": INTENT_DOMAINS[intent],
        "sources": sources,
        "excluded": excluded,
        "warnings": warnings,
        "outputs": declaration.get("outputs", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--plugin-root", type=Path, required=True)
    resolve.add_argument("--project", required=True)
    resolve.add_argument("--intent", choices=sorted(INTENT_DOMAINS), required=True)
    resolve.add_argument("--taskade-root", type=Path, required=True)
    resolve.add_argument("--vault-root", type=Path, required=True)
    resolve.add_argument("--github-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet = build_context(
            project=args.project,
            intent=args.intent,
            plugin_root=args.plugin_root,
            taskade_root=args.taskade_root,
            vault_root=args.vault_root,
            github_root=args.github_root,
        )
    except SurfaceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
