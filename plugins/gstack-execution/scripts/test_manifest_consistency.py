#!/usr/bin/env python3
"""A plugin's version has one home.

Observed 2026-09-17: gstack-execution's version read 0.21.0 in its manifest, 0.19.0 in
marketplace.json, and 0.5.0 in its README -- three homes, two of them wrong, and the README had
been stale for sixteen minor releases without anyone noticing. Three other plugins restated a
version in their README and three of those had drifted too.

XE-008's rule applies: where a fact can have one home, it has one. The manifest is that home.
marketplace.json must agree with it because the marketplace is generated FROM the plugins, and a
README must not restate it at all -- a number in prose has no mechanism keeping it true.

ponytail: two assertions over files that already exist. No version-bumping machinery, no release
tool. This catches the drift; keeping versions correct is still a human writing the right number in
one place.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VERSION_IN_PROSE = re.compile(r"^\*\*Version:\*\*\s*([0-9]+\.[0-9]+\.[0-9]+)", re.M)


def marketplace_entries():
    m = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    return m["plugins"]


class ManifestConsistency(unittest.TestCase):

    def test_marketplace_version_matches_each_plugin_manifest(self):
        entries = marketplace_entries()
        self.assertGreater(len(entries), 20, "marketplace listing looks empty; this check examined almost nothing")
        checked = 0
        for e in entries:
            pj = ROOT / e["source"].lstrip("./") / ".claude-plugin" / "plugin.json"
            if not pj.exists():
                continue
            with self.subTest(plugin=e["name"]):
                manifest_version = json.loads(pj.read_text()).get("version")
                self.assertEqual(e.get("version"), manifest_version,
                                 f"{e['name']}: marketplace.json says {e.get('version')}, "
                                 f"its manifest says {manifest_version}")
                checked += 1
        self.assertGreater(checked, 20, f"only {checked} plugins had a manifest to compare")

    def test_no_readme_restates_a_version(self):
        """A version in prose has nothing keeping it true. gstack-execution's README sat at 0.5.0
        while the plugin shipped 0.21.0."""
        offenders = []
        for readme in sorted(ROOT.glob("plugins/*/README.md")) + sorted(ROOT.glob("skill-bundles/*/README.md")):
            m = VERSION_IN_PROSE.search(readme.read_text(encoding="utf-8", errors="replace"))
            if m:
                offenders.append(f"{readme.relative_to(ROOT)} states {m.group(1)}")
        self.assertEqual(offenders, [],
                         "a README must not restate a version; the manifest is the one home: "
                         + "; ".join(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=1)
