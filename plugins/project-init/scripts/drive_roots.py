#!/usr/bin/env python3
"""SM-012: find this Mac's MoxyWolf Drive roots by their tails, never by a hardcoded path.

Google Drive for Desktop names the account folder differently from Mac to Mac, so project files store
only the tail under it. This lists ~/Library/CloudStorage/GoogleDrive-*, skips @gtempaccount.com
folders, keeps those holding both tails, and prefers the one with the team-rules INDEX.

Prints JSON: {"status": "ok", "github", "vault"} | {"status": "ambiguous", "candidates"} |
{"status": "not_found", "reason"}. Exit 0 on ok, 1 otherwise.

ponytail: a glob and two is_dir checks. Stdlib only.
"""
import json
import sys
from pathlib import Path

GITHUB = "Shared drives/GitHub"
VAULT = "Shared drives/MoxyWolf Shared Files/MoxyWolf Vault"
INDEX = "GitHub/Projects/_shared-memory/INDEX.md"
SKIP_SUFFIX = "@gtempaccount.com"


def resolve(cloud):
    cloud = Path(cloud)
    accounts = sorted(p for p in cloud.glob("GoogleDrive-*") if p.is_dir() and not p.name.endswith(SKIP_SUFFIX))
    both = [p for p in accounts if (p / GITHUB).is_dir() and (p / VAULT).is_dir()]
    if not both:
        seen = ", ".join(p.name for p in accounts) or "none"
        return {"status": "not_found", "reason": f"no Google Drive account under {cloud} holds both '{GITHUB}' and "
                f"'{VAULT}' (accounts checked: {seen}); Drive may not be signed in, or the shared drives haven't synced"}
    if len(both) > 1:
        # ponytail: none with the INDEX means we can't tell them apart either, so keep them all and ask
        both = [p for p in both if (p / "Shared drives" / INDEX).is_file()] or both
    if len(both) > 1:
        return {"status": "ambiguous", "candidates": [str(p) for p in both]}
    return {"status": "ok", "github": str(both[0] / GITHUB), "vault": str(both[0] / VAULT)}


if __name__ == "__main__":
    out = resolve(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Library" / "CloudStorage")
    print(json.dumps(out))
    sys.exit(0 if out["status"] == "ok" else 1)
