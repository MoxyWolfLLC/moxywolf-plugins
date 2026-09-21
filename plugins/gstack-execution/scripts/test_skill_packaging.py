#!/usr/bin/env python3
"""CI-001: this repository's own catalog, checked by the gate that ships it.

`skill_packaging.py --selftest` proves the CHECK works. This proves the CATALOG
is clean, which is the thing the compatibility assessment found broken under a
green build. Without this file the gate would run the check's fixtures and never
point it at the 150 packages the repository actually ships.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_packaging import FAIL, run  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]

results = run(ROOT)

# EV-001: a catalog that was never found is not a clean catalog.
assert results, f"examined 0 packages under {ROOT}; a check that examined nothing cannot pass"

failed = [r for r in results if r["status"] == FAIL]
assert not failed, "packages a loader cannot read:\n" + "\n".join(
    f"  {r['package']}: {r['detail']}" for r in failed)

print(f"skill packaging: {len(results)} packages examined, all loadable")
