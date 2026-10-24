"""SM-008: no plugin home sends team rules, gate decisions or design mirrors to Taskade.

The team rules left `Taskade/_Shared Files/_shared-memory/` (SM-007) and the gate log left
`Taskade/_Shared Files/_gate-log/` (SM-008), both for `GitHub/Projects/`. Design mirrors go to the
project's workspace from its instructions, never to a hardcoded `Taskade/<project>/06`.

Every tracked text file is examined except the records of what was: DESIGN.md, the conformance
plan, docs/evidence, plugin.json and marketplace.json changelogs, and the tests that name the
strings on purpose. Zero examined fails (EV-001).

ponytail: `git ls-files` plus a substring scan. No AST, no config.
"""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD_PATHS = ["Taskade/_Shared Files/_shared-memory", "Taskade/_Shared Files/_gate-log"]
MIRROR = "Taskade/<project>/06"
GSTACK = "plugins/gstack-execution/"
EXEMPT_FILES = {"DESIGN.md", "PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md", ".claude-plugin/marketplace.json",
                "plugins/project-init/tests/test_taskade_paths.py",
                "plugins/project-init/tests/test_shared_memory_home.py"}
EXEMPT_PREFIXES = ("docs/evidence/",)
TEXT = {".md", ".py", ".mjs", ".js", ".json", ".html", ".sh", ".txt", ".yml", ".yaml", ".toml"}


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for rel in out.splitlines():
        if rel in EXEMPT_FILES or rel.startswith(EXEMPT_PREFIXES) or rel.endswith("plugin.json"):
            continue
        if Path(rel).suffix in TEXT and (ROOT / rel).is_file():
            yield rel


def hits_in(rel, text):
    found = [s for s in OLD_PATHS if s in text]
    if rel.startswith(GSTACK) and MIRROR in text:
        found.append(MIRROR)
    return found


class TaskadePaths(unittest.TestCase):
    def test_no_home_names_an_old_taskade_path(self):
        files = list(tracked())
        hits = []
        for rel in files:
            for n, line in enumerate((ROOT / rel).read_text(errors="replace").splitlines(), 1):
                for s in hits_in(rel, line):
                    hits.append(f"{rel}:{n}: {s}")
        print(f"examined {len(files)} files, {len(hits)} old Taskade path references")
        self.assertGreater(len(files), 0, "examined nothing")
        self.assertEqual(hits, [])

    def test_the_check_catches_each_string(self):
        for s in OLD_PATHS:
            self.assertEqual(hits_in("README.md", f"run `python3 \"{s}/x.py\"`"), [s])
        self.assertEqual(hits_in(GSTACK + "README.md", f"mirror at `{MIRROR} – Engineering/`"), [MIRROR])
        self.assertEqual(hits_in("plugins/project-init/README.md", f"`{MIRROR}`"), [])


if __name__ == "__main__":
    unittest.main()
