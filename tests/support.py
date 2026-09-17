from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_script(script: str, *args: object) -> subprocess.CompletedProcess[str]:
    script_path = REPO_ROOT / "scripts" / script
    if script in {"project_surfaces.py", "federated_context.py"}:
        script_path = REPO_ROOT / "plugins" / "project-init" / "scripts" / script
    return subprocess.run(
        [sys.executable, str(script_path), *(str(arg) for arg in args)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def standard_manifest(
    *,
    project_id: str = "team-plugins",
    display_name: str = "Team Plugins",
    aliases: list[str] | None = None,
    workspace_type: str = "taskade",
    workspace_path: str = "Taskade/Team Plugins",
    memory_path: str = "MoxyWolf Vault/Projects/Moxywolf Plugins",
    moc: str = "00-Hub/Moxywolf Plugins Index.md",
    repositories: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_id": project_id,
        "display_name": display_name,
        "aliases": aliases if aliases is not None else ["Moxywolf Plugins"],
        "workspace": {"type": workspace_type, "path": workspace_path},
        "memory": {"path": memory_path, "moc": moc},
        "repositories": repositories
        if repositories is not None
        else [
            {
                "path": "GitHub/moxywolf-plugins",
                "access": "read-write",
                "role": "plugin marketplace source",
            }
        ],
        "task_tags": ["#project/moxywolf-plugins"],
    }


def create_standard_project(root: Path, manifest: dict[str, object] | None = None) -> tuple[Path, Path, Path]:
    taskade = root / "Taskade"
    vault = root / "MoxyWolf Vault"
    github = root / "GitHub"
    payload = manifest or standard_manifest()
    write_json(taskade / "Team Plugins" / "00 – Project Hub" / "project-surfaces.json", payload)
    write_text(taskade / "Team Plugins" / "00 – Project Hub" / "cowork-session-handoff.md", "# Current handoff\n\nShip the context contract.\n")
    write_text(taskade / "Team Plugins" / "03 – Product & Requirements" / "current-plan.md", "# Current plan\n\nBuild the federated resolver.\n")
    write_text(vault / "Projects" / "Moxywolf Plugins" / "00-Hub" / "Moxywolf Plugins Index.md", "# Moxywolf Plugins\n\nCompany memory for the plugin fleet.\n")
    write_text(vault / "Projects" / "Moxywolf Plugins" / "06-Engineering" / "DR-014-context-contract.md", "# DR-014\n\nUse three planes.\n")
    write_text(vault / "_Shared Knowledge" / "Operating Norms" / "norm-provenance.md", "# Provenance\n\nCite sources and dates.\n")
    write_text(vault / "_Shared Knowledge" / "Agents and Plugins" / "openrouter.env", "OPENROUTER_API_KEY=do-not-read\n")
    write_text(vault / "Projects" / "Moxywolf Plugins" / "06-Engineering" / "graphs" / "vault" / "graph.md", "# Derived graph\n")
    write_text(github / "moxywolf-plugins" / "README.md", "# Plugin marketplace\n\nLive repository behavior.\n")
    write_text(github / "moxywolf-plugins" / "plugins" / "project-init" / "README.md", "# project-init\n\nResolves sessions.\n")
    return taskade, vault, github
