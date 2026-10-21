#!/usr/bin/env python3
"""SM-007: decide which of a project's authoritative files need re-mirroring into its claude.ai Project. Stdlib only.

Disk is the only author. The Project is a read-only mirror. This script never touches the Project: it reads the
declared files under the Taskade root, compares each sha256 to the sidecar (`00 – Project Hub/.project-mirror.json`),
and prints the decision as JSON. The caller does the `project_write`, then calls `record` so the sidecar catches up.

  plan   --surfaces <project-surfaces.json> --taskade <root>
  record --surfaces <project-surfaces.json> --taskade <root> --path <rel> --sha <hex>

ponytail: a sidecar hash instead of reading the Project copy back; disk wins, so a hand edit in the Project is
overwritten on the next changed write and never read.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HUB = "00 – Project Hub"
SIDECAR = ".project-mirror.json"
SHARED_INDEX = "_Shared Files/_shared-memory/INDEX.md"


def load(surfaces: Path) -> tuple[str, list[str]]:
    """(project subfolder, declared docs). `project_docs` absent → the default four (criterion 1)."""
    s = json.loads(surfaces.read_text(encoding="utf-8"))
    ws = s.get("workspace", {}).get("path", "")
    project = ws.split("/", 1)[1] if ws.startswith("Taskade/") else ws
    if not project:
        sys.exit("project-surfaces.json has no workspace.path")
    docs = s.get("project_docs") or [
        f"{project}/{HUB}/cowork-project-instructions.md",
        f"{project}/{HUB}/project-surfaces.json",
        f"{project}/{HUB}/cowork-session-handoff.md",
        SHARED_INDEX,
    ]
    return project, docs


def sidecar_path(taskade: Path, project: str) -> Path:
    return taskade / project / HUB / SIDECAR


def read_sidecar(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def inside(root: Path, rel: str) -> Path | None:
    full = (root / rel).resolve()
    return full if full.is_relative_to(root.resolve()) else None


def plan(taskade: Path, project: str, docs: list[str]) -> dict:
    side = read_sidecar(sidecar_path(taskade, project))
    out = {"write": [], "unchanged": [], "missing": [], "sidecar": str(sidecar_path(taskade, project))}
    for rel in docs:
        full = inside(taskade, rel)
        if full is None:
            out["missing"].append({"path": rel, "reason": "outside the Taskade root"})
            continue
        try:
            data = full.read_bytes()
        except FileNotFoundError:
            out["missing"].append({"path": rel, "reason": "not on disk"})
            continue
        except OSError as e:  # EDEADLK on a Drive-locked file lands here
            out["missing"].append({"path": rel, "reason": f"read failed: {e.strerror or e}"})
            continue
        sha = hashlib.sha256(data).hexdigest()
        entry = {"path": rel, "sha256": sha, "bytes": len(data)}
        prev = side.get(rel, {})
        if prev.get("sha256") == sha:
            entry["mirrored_at"] = prev.get("mirrored_at")
            out["unchanged"].append(entry)
        else:
            out["write"].append(entry)
    return out


def record(taskade: Path, project: str, rel: str, sha: str) -> dict:
    p = sidecar_path(taskade, project)
    side = read_sidecar(p)
    side[rel] = {"sha256": sha, "mirrored_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(side, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"recorded": rel, "sidecar": str(p)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "record"):
        sp = sub.add_parser(name)
        sp.add_argument("--surfaces", required=True, type=Path)
        sp.add_argument("--taskade", required=True, type=Path)
        if name == "record":
            sp.add_argument("--path", required=True)
            sp.add_argument("--sha", required=True)
    a = ap.parse_args(argv)
    project, docs = load(a.surfaces)
    result = plan(a.taskade, project, docs) if a.cmd == "plan" else record(a.taskade, project, a.path, a.sha)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
