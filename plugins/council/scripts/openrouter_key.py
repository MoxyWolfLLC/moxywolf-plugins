#!/usr/bin/env python3
"""
Shared OpenRouter API key loader for MoxyWolf plugins.

Resolves the key in this priority order:
    1. OPENROUTER_API_KEY env var (set by the caller — wins if present)
    2. OPENROUTER_KEY_FILE env var pointing to a .env-style file
    3. MOXYWOLF_VAULT env var + "_Shared Knowledge/Agents and Plugins/openrouter.env"
    4. Glob for the vault file inside the Cowork bash sandbox:
         /sessions/*/mnt/MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/openrouter.env
    5. Glob for the vault file under a native macOS Google Drive mount:
         ~/Library/CloudStorage/GoogleDrive-*/Shared drives/MoxyWolf Shared Files/
            MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/openrouter.env

The file format is standard .env — one KEY=value per line, with `#` comments and
optional surrounding quotes. Only the OPENROUTER_API_KEY line is required.

Designed to be imported by other plugin scripts:

    from openrouter_key import load_key, KeyNotFoundError
    api_key = load_key()  # raises KeyNotFoundError with actionable message

Or run directly to print the resolved key (useful for shell sourcing):

    python3 openrouter_key.py --print            # prints just the key
    python3 openrouter_key.py --export           # prints `export OPENROUTER_API_KEY=...`
    python3 openrouter_key.py --where            # prints the file path the key came from
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from pathlib import Path

VAULT_REL_PATH = "_Shared Knowledge/Agents and Plugins/openrouter.env"

# Search globs in priority order. Each entry is a (description, glob_pattern) pair.
SANDBOX_GLOBS = [
    ("Cowork bash sandbox mount", f"/sessions/*/mnt/MoxyWolf Vault/{VAULT_REL_PATH}"),
]
HOST_GLOBS = [
    (
        "macOS Google Drive shared drive",
        str(
            Path.home()
            / "Library"
            / "CloudStorage"
            / "GoogleDrive-*"
            / "Shared drives"
            / "MoxyWolf Shared Files"
            / "MoxyWolf Vault"
            / VAULT_REL_PATH
        ),
    ),
]


class KeyNotFoundError(RuntimeError):
    """Raised when no usable OpenRouter key can be located."""


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a simple .env file. Skips blanks and `#` comments."""
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        env[key] = val
    return env


def _candidate_files() -> list[tuple[str, Path]]:
    """Return ordered list of (source-label, path) pairs to try."""
    candidates: list[tuple[str, Path]] = []

    explicit = os.environ.get("OPENROUTER_KEY_FILE")
    if explicit:
        candidates.append(("OPENROUTER_KEY_FILE env var", Path(explicit)))

    vault = os.environ.get("MOXYWOLF_VAULT")
    if vault:
        candidates.append(
            ("MOXYWOLF_VAULT env var + vault relpath", Path(vault) / VAULT_REL_PATH)
        )

    for label, pattern in SANDBOX_GLOBS + HOST_GLOBS:
        for match in sorted(glob.glob(pattern)):
            candidates.append((label, Path(match)))

    return candidates


def load_key(*, return_source: bool = False) -> str | tuple[str, str]:
    """
    Resolve the OpenRouter API key.

    Returns the key string. If return_source=True, returns (key, source_description).
    Raises KeyNotFoundError with an actionable message if no key is found.
    """
    direct = os.environ.get("OPENROUTER_API_KEY")
    if direct:
        return (direct, "OPENROUTER_API_KEY env var") if return_source else direct

    tried: list[str] = []
    for label, path in _candidate_files():
        tried.append(f"  - {label}: {path}")
        if not path.is_file():
            continue
        try:
            env = _parse_env_file(path)
        except OSError as e:
            tried.append(f"    (read error: {e})")
            continue
        key = env.get("OPENROUTER_API_KEY")
        if key:
            source = f"{label} ({path})"
            return (key, source) if return_source else key
        tried.append(f"    (file exists but no OPENROUTER_API_KEY line)")

    msg = (
        "OPENROUTER_API_KEY not found.\n\n"
        "Searched:\n"
        f"  - OPENROUTER_API_KEY env var (unset)\n"
        + ("\n".join(tried) if tried else "  (no candidate file paths)")
        + "\n\nFix: ask Dorian for the team-shared key, then add this line to\n"
        f"  MoxyWolf Vault/{VAULT_REL_PATH}\n"
        "    OPENROUTER_API_KEY=sk-or-v1-...\n"
        "Or set the OPENROUTER_API_KEY env var directly before running."
    )
    raise KeyNotFoundError(msg)


def _main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="OpenRouter key loader")
    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "--print", action="store_true", help="Print the resolved key to stdout"
    )
    g.add_argument(
        "--export",
        action="store_true",
        help="Print `export OPENROUTER_API_KEY=...` for shell eval",
    )
    g.add_argument(
        "--where",
        action="store_true",
        help="Print the source label and path the key came from",
    )
    args = p.parse_args(argv)
    if not (args.print or args.export or args.where):
        args.print = True

    try:
        key, source = load_key(return_source=True)
    except KeyNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.print:
        print(key)
    elif args.export:
        # Shell-safe single-quote escaping
        safe = key.replace("'", "'\\''")
        print(f"export OPENROUTER_API_KEY='{safe}'")
    elif args.where:
        print(source)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
