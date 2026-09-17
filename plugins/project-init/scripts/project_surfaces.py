#!/usr/bin/env python3
"""Resolve a MoxyWolf project's Taskade, Vault, and Git repository surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


class SurfaceError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SurfaceError(f"Cannot read project surface manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SurfaceError(f"Project surface manifest must contain an object: {path}")
    return payload


def _discover_manifests(taskade_root: Path, vault_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    manifests: list[tuple[Path, dict[str, Any]]] = []
    if taskade_root.exists():
        for path in taskade_root.glob("*/00 *Project Hub/project-surfaces.json"):
            manifests.append((path, _load_json(path)))
    projects = vault_root / "Projects"
    if projects.exists():
        for path in projects.glob("*/00-Hub/project-surfaces.json"):
            manifests.append((path, _load_json(path)))
    return manifests


def _validate_manifest(payload: dict[str, Any], source: Path) -> None:
    required = {"schema_version", "project_id", "display_name", "workspace", "memory", "repositories"}
    missing = sorted(required - payload.keys())
    if missing:
        raise SurfaceError(f"Invalid project surface manifest {source}: missing {', '.join(missing)}")
    if payload["schema_version"] != 1:
        raise SurfaceError(f"Invalid project surface manifest {source}: unsupported schema_version")
    if not isinstance(payload.get("aliases", []), list) or not isinstance(payload["repositories"], list):
        raise SurfaceError(f"Invalid project surface manifest {source}: aliases and repositories must be lists")
    if not isinstance(payload.get("related_workspaces", []), list):
        raise SurfaceError(f"Invalid project surface manifest {source}: related_workspaces must be a list")
    workspace = payload["workspace"]
    if not isinstance(workspace, dict) or workspace.get("type") not in {"taskade", "vault-only"}:
        raise SurfaceError(f"Invalid project surface manifest {source}: workspace type must be taskade or vault-only")
    memory = payload["memory"]
    if not isinstance(memory, dict) or not memory.get("path") or not memory.get("moc"):
        raise SurfaceError(f"Invalid project surface manifest {source}: memory path and MOC are required")


def _safe_relative(value: str, prefix: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts or pure.parts[0] != prefix:
        raise SurfaceError(f"Path {value!r} is outside the approved roots")
    return Path(*pure.parts[1:])


def _resolve_declared_path(value: str, *, expected_prefix: str, root: Path, field: str) -> Path:
    prefix = PurePosixPath(value).parts[0] if PurePosixPath(value).parts else ""
    if prefix != expected_prefix:
        raise SurfaceError(f"{field} must use the {expected_prefix}/ root: {value!r}")
    candidate = root / _safe_relative(value, expected_prefix)
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise SurfaceError(f"{field} path escapes the {expected_prefix}/ root: {value!r}") from exc
    return resolved_candidate


def _resolve_moc(memory_path: Path, value: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise SurfaceError(f"MOC path must remain beneath company memory: {value!r}")
    memory_root = memory_path.resolve(strict=False)
    candidate = (memory_root / Path(*pure.parts)).resolve(strict=False)
    try:
        candidate.relative_to(memory_root)
    except ValueError as exc:
        raise SurfaceError(f"MOC path escapes company memory: {value!r}") from exc
    return candidate


def resolve_project(project: str, taskade_root: Path, vault_root: Path, github_root: Path) -> dict[str, Any]:
    manifests = _discover_manifests(taskade_root, vault_root)
    query = project.casefold()
    matches: list[tuple[Path, dict[str, Any]]] = []
    for source, payload in manifests:
        _validate_manifest(payload, source)
        names = [payload["project_id"], payload["display_name"], *payload.get("aliases", [])]
        if any(str(name).casefold() == query for name in names):
            matches.append((source, payload))
    if len(matches) > 1:
        raise SurfaceError(f"Ambiguous project name or alias {project!r}; matched {len(matches)} manifests")
    if not matches:
        legacy = list(taskade_root.glob(f"{project}/00 *Project Hub/cowork-project-instructions.md"))
        suffix = "; project exists but has no project-surfaces.json" if legacy else ""
        raise SurfaceError(f"No project-surfaces.json manifest found for {project!r}{suffix}")

    source, payload = matches[0]
    workspace_value = payload["workspace"]["path"]
    workspace_prefix = "Taskade" if payload["workspace"]["type"] == "taskade" else "MoxyWolf Vault"
    workspace_root = taskade_root if workspace_prefix == "Taskade" else vault_root
    workspace_path = _resolve_declared_path(
        workspace_value, expected_prefix=workspace_prefix, root=workspace_root, field="Workspace"
    )
    memory_path = _resolve_declared_path(
        payload["memory"]["path"], expected_prefix="MoxyWolf Vault", root=vault_root, field="Company memory"
    )
    moc_path = _resolve_moc(memory_path, payload["memory"]["moc"])
    warnings: list[str] = []
    if not workspace_path.exists():
        warnings.append(f"Declared project workspace is missing: {workspace_path}")
    if not memory_path.exists():
        warnings.append(f"Declared company-memory folder is missing: {memory_path}")

    repositories: list[dict[str, Any]] = []
    for repository in payload["repositories"]:
        if not isinstance(repository, dict) or repository.get("access") not in {"read-only", "read-write"}:
            raise SurfaceError(f"Invalid repository declaration in {source}")
        repo_path = _resolve_declared_path(
            repository.get("path", ""), expected_prefix="GitHub", root=github_root, field="Repository"
        )
        available = repo_path.exists()
        if not available:
            warnings.append(f"Declared repository is missing: {repo_path}")
        repositories.append(
            {
                "path": str(repo_path),
                "declared_path": repository["path"],
                "access": repository["access"],
                "role": repository.get("role", ""),
                "available": available,
            }
        )

    related_workspaces: list[dict[str, Any]] = []
    for related in payload.get("related_workspaces", []):
        if not isinstance(related, dict) or related.get("access") not in {"read-only", "read-write"}:
            raise SurfaceError(f"Invalid related workspace declaration in {source}")
        related_path = _resolve_declared_path(
            related.get("path", ""), expected_prefix="Taskade", root=taskade_root, field="Related workspace"
        )
        available = related_path.exists()
        if not available:
            warnings.append(f"Declared related workspace is missing: {related_path}")
        related_workspaces.append(
            {
                "path": str(related_path),
                "declared_path": related["path"],
                "access": related["access"],
                "role": related.get("role", ""),
                "available": available,
            }
        )

    return {
        "schema_version": 1,
        "project_id": payload["project_id"],
        "display_name": payload["display_name"],
        "aliases": payload.get("aliases", []),
        "manifest_path": str(source),
        "workspace": {
            "type": payload["workspace"]["type"],
            "plane": "project-workspace",
            "path": str(workspace_path),
            "available": workspace_path.exists(),
        },
        "memory": {
            "plane": "company-memory",
            "path": str(memory_path),
            "moc": str(moc_path),
            "available": memory_path.exists(),
        },
        "repositories": repositories,
        "related_workspaces": related_workspaces,
        "task_tags": payload.get("task_tags", []),
        "warnings": warnings,
    }


def route_output(packet: dict[str, Any], output_type: str, repository: str | None) -> dict[str, Any]:
    if output_type == "working-artifact":
        return {"plane": "project-workspace", "path": packet["workspace"]["path"], "write_authorized": False}
    if output_type == "durable-knowledge":
        return {
            "plane": "company-memory",
            "path": packet["memory"]["path"],
            "action": "propose-via-obsidian-update",
            "write_authorized": False,
        }
    if output_type == "code-change":
        if not repository:
            raise SurfaceError("A declared repository is required for a code change")
        matches = [repo for repo in packet["repositories"] if Path(repo["path"]).name.casefold() == repository.casefold()]
        if len(matches) != 1:
            raise SurfaceError(f"Repository {repository!r} is not declared for this project")
        target = matches[0]
        if target["access"] != "read-write":
            raise SurfaceError(f"Repository {repository!r} is read-only")
        return {
            "plane": "code-workspace",
            "path": target["path"],
            "access": target["access"],
            "write_authorized": False,
        }
    raise SurfaceError(f"Unknown output type: {output_type}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("resolve", "route"):
        command = subparsers.add_parser(name)
        command.add_argument("--project", required=True)
        command.add_argument("--taskade-root", type=Path, required=True)
        command.add_argument("--vault-root", type=Path, required=True)
        command.add_argument("--github-root", type=Path, required=True)
        if name == "route":
            command.add_argument("--output-type", required=True)
            command.add_argument("--repository")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        packet = resolve_project(args.project, args.taskade_root, args.vault_root, args.github_root)
        if args.command == "route":
            packet = route_output(packet, args.output_type, args.repository)
    except SurfaceError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
