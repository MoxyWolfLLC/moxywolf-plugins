#!/usr/bin/env python3
"""Validate that every marketplace plugin declares its federated context contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PLANE_REQUIREMENTS = {"required", "optional", "none"}
ALLOWED_OUTPUTS = {
    "working-artifact",
    "product-decision",
    "code-change",
    "knowledge-candidate",
    "derived-vault-artifact",
    "operational-task",
}
ALLOWED_MEMORY_SCOPES = {"project-moc", "recent-decisions", "shared-operating-norms", "derived-graphs"}


def _valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return False
    planes = payload.get("planes")
    outputs = payload.get("outputs")
    scopes = payload.get("memory_scopes")
    return (
        isinstance(planes, dict)
        and set(planes) == {"project_workspace", "company_memory", "repositories"}
        and all(value in ALLOWED_PLANE_REQUIREMENTS for value in planes.values())
        and isinstance(outputs, list)
        and all(value in ALLOWED_OUTPUTS for value in outputs)
        and isinstance(scopes, list)
        and all(value in ALLOWED_MEMORY_SCOPES for value in scopes)
    )


def validate() -> dict[str, Any]:
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    missing: list[str] = []
    invalid: list[str] = []
    for plugin in marketplace["plugins"]:
        plugin_root = (ROOT / plugin["source"]).resolve()
        declaration = plugin_root / "vault-context.json"
        if not declaration.exists():
            missing.append(plugin["name"])
            continue
        try:
            payload = json.loads(declaration.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            invalid.append(plugin["name"])
            continue
        if not _valid(payload):
            invalid.append(plugin["name"])
    return {
        "validated_plugins": len(marketplace["plugins"]) - len(missing) - len(invalid),
        "missing": sorted(missing),
        "invalid": sorted(invalid),
    }


def main() -> int:
    report = validate()
    print(json.dumps(report, indent=2))
    return 1 if report["missing"] or report["invalid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
