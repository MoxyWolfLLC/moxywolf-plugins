#!/usr/bin/env python3
"""CI-002: the check pointed at this repository's own history, not only at fixtures.

`version_bump.py --selftest` proves the CHECK works against temporary repositories.
This proves it catches the two real misses that made the item exist, which is the
thing a fixture cannot do, per DR-102 and CI-001's precedent.

Two misses, measured before this file was written:

  * `6c9912c` changed `gstack-execution` and left it at 0.27.0.
  * `d619c06` through `2293ff6`, six consecutive merges, each left the top-level
    `marketplace.json` version at 1.57.0. The client gates on that number, so every
    plugin bumped in `d619c06` reached nobody, `github-repo-analyzer` 0.12.0 included.
    Three of the six changed a plugin and are caught. The other three changed none and
    owe no bump, which is criterion 2 read exactly rather than a check that fires on
    every commit. Both halves are asserted below, because a check that failed all six
    would be wrong in the direction nobody notices.

The criterion originally named `github-repo-analyzer` at 0.11.0 for the first miss.
It bumped there, 0.10.0 to 0.11.0. Corrected in DESIGN.md on 2026-09-22 before this
file was written, because a test written to the old wording asserts something false.

This needs real history. `actions/checkout` at its default depth of 1 has none, which
is why the workflow sets `fetch-depth: 0` (CI-002.7). A missing commit FAILS here and
says which one, rather than passing over history it never had.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from version_bump import FAIL, PASS, run, verdict  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]

UNMOVED_PLUGIN = ("6c9912c", "gstack-execution", "0.27.0")
UNMOVED_TOP = ["d619c06", "a694955", "27fd672", "47e6080", "94926c0", "2293ff6"]


def have(ref):
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", f"{ref}^{{commit}}"],
                       capture_output=True, text=True)
    return r.returncode == 0


missing = [r for r in [UNMOVED_PLUGIN[0], *UNMOVED_TOP] if not have(r) or not have(f"{r}^")]
assert not missing, (
    f"history is not present for {', '.join(missing)}. This check reads real merges, so a "
    f"shallow checkout cannot run it. Set fetch-depth: 0 on actions/checkout (CI-002.7).")

# Miss 1: a plugin whose files changed and whose version did not.
merge, plugin, stuck = UNMOVED_PLUGIN
r = run(ROOT, f"{merge}^", merge)
assert verdict(r) == FAIL, f"{merge} should not pass: {r}"
caught = {c["plugin"]: c for c in r["checks"] if c["status"] == FAIL}
assert plugin in caught, f"{merge} must catch {plugin}; caught {sorted(caught)} instead"
assert caught[plugin]["base"] == caught[plugin]["head"] == stuck, caught[plugin]
# and the plugin that DID bump in that merge is not accused of anything
gra = [c for c in r["checks"] if c["plugin"] == "github-repo-analyzer"]
assert gra and gra[0]["status"] == PASS, f"github-repo-analyzer bumped at {merge}: {gra}"

# Miss 2: six consecutive merges at an unmoved top-level version. The three that shipped a
# plugin are caught; the three that shipped none owe nothing and must pass.
caught_top, owed_nothing = [], []
for merge in UNMOVED_TOP:
    r = run(ROOT, f"{merge}^", merge)
    assert r["top_level"]["head"] == "1.57.0", f"{merge} top-level: {r['top_level']}"
    if r["examined"]:
        assert r["top_level"]["status"] == FAIL, f"{merge} changed {r['examined']} plugin(s): {r}"
        caught_top.append((merge, r["examined"]))
    else:
        assert r["top_level"]["status"] == PASS, f"{merge} changed no plugin: {r}"
        owed_nothing.append(merge)

assert len(caught_top) == 3, f"expected 3 merges caught, got {caught_top}"
assert len(owed_nothing) == 3, f"expected 3 merges owing nothing, got {owed_nothing}"

print(f"version bump over real history: {UNMOVED_PLUGIN[1]} caught at {UNMOVED_PLUGIN[2]} in "
      f"{UNMOVED_PLUGIN[0]}; {len(caught_top)} merges caught at an unmoved top-level 1.57.0 "
      f"({', '.join(m for m, _ in caught_top)}); {len(owed_nothing)} merges changed no plugin "
      f"and owed no bump ({', '.join(owed_nothing)})")
