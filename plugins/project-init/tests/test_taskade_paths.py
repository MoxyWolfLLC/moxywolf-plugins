"""SM-008: no plugin home sends team rules, gate decisions or design mirrors to Taskade.

The team rules left `Taskade/_Shared Files/_shared-memory/` (SM-007) and the gate log left
`Taskade/_Shared Files/_gate-log/` (SM-008), both for `GitHub/Projects/`. Design mirrors go to the
project's workspace from its instructions, never to a hardcoded `Taskade/<project>/06`.

Every tracked file whose bytes decode as text is examined, whatever its extension. Exempt are the
records of what was, scoped as narrowly as criterion 2 allows: in DESIGN.md only the SM-007 and
SM-008 sections and the Amendments log; in plugin.json and marketplace.json only `description`
values, which carry the changelogs; the conformance plan and docs/evidence as whole dated records;
and this test and SM-007's, which name the strings on purpose. Zero examined fails (EV-001).

ponytail: `git ls-files` plus a substring scan. No AST, no config.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD_PATHS = ["Taskade/_Shared Files/_shared-memory", "Taskade/_Shared Files/_gate-log"]
MIRROR = "Taskade/<project>/06"
GSTACK = "plugins/gstack-execution/"
SELF = {"plugins/project-init/tests/test_taskade_paths.py", "plugins/project-init/tests/test_shared_memory_home.py"}
WHOLE_RECORDS = {"PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md"}
RECORD_PREFIXES = ("docs/evidence/",)
DESIGN_HISTORY = ("### SM-007", "### SM-008")


def text_of(path):
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def without_descriptions(node):
    if isinstance(node, dict):
        return {k: without_descriptions(v) for k, v in node.items() if k != "description"}
    if isinstance(node, list):
        return [without_descriptions(v) for v in node]
    return node


def scannable_lines(rel, text):
    """(line number, line) pairs subject to the check, after the history exemptions."""
    if rel.endswith("plugin.json") or rel.endswith("marketplace.json"):
        stripped = json.dumps(without_descriptions(json.loads(text)), indent=1, ensure_ascii=False)
        return list(enumerate(stripped.splitlines(), 1))
    if rel == "DESIGN.md":
        out, exempt = [], False
        for n, line in enumerate(text.splitlines(), 1):
            if line.startswith("## "):
                exempt = line.startswith("## Amendments log")
            elif line.startswith("### "):
                exempt = line.startswith(DESIGN_HISTORY)
            if not exempt:
                out.append((n, line))
        return out
    return list(enumerate(text.splitlines(), 1))


def hits_in(rel, line):
    found = [s for s in OLD_PATHS if s in line]
    if rel.startswith(GSTACK) and MIRROR in line:
        found.append(MIRROR)
    return found


def scan(root):
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout
    examined, hits = 0, []
    for rel in out.splitlines():
        if rel in SELF or rel in WHOLE_RECORDS or rel.startswith(RECORD_PREFIXES):
            continue
        p = root / rel
        if not p.is_file():
            continue
        text = text_of(p)
        if text is None:
            continue
        examined += 1
        for n, line in scannable_lines(rel, text):
            hits += [f"{rel}:{n}: {s}" for s in hits_in(rel, line)]
    return examined, hits


class TaskadePaths(unittest.TestCase):
    def test_no_home_names_an_old_taskade_path(self):
        examined, hits = scan(ROOT)
        print(f"examined {examined} files, {len(hits)} old Taskade path references")
        self.assertGreater(examined, 0, "examined nothing")
        self.assertEqual(hits, [])

    def test_the_check_catches_each_string(self):
        for s in OLD_PATHS:
            self.assertEqual(hits_in("README.md", f"run `python3 \"{s}/x.py\"`"), [s])
        self.assertEqual(hits_in(GSTACK + "README.md", f"mirror at `{MIRROR} – Engineering/`"), [MIRROR])
        self.assertEqual(hits_in("plugins/project-init/README.md", f"`{MIRROR}`"), [])

    def test_discovery_reaches_any_text_file_and_only_history_is_exempt(self):
        old = OLD_PATHS[1]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            files = {
                "Makefile": f"log: {old}\n",                                   # no extension
                "notes.rst": f"see {old}\n",                                   # unlisted extension
                "plugins/x/.claude-plugin/plugin.json": json.dumps({"description": old, "homepage": old}),
                "DESIGN.md": f"## Items\n### SM-008 x\n{old}\n### XX-001 y\n{old}\n## Amendments log\n- {old}\n",
                "docs/evidence/e.md": old,
                "blob.bin": "\0" + old,
            }
            for rel, body in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(body)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            examined, hits = scan(root)
        self.assertEqual(examined, 4)
        self.assertEqual(sorted(h.split(":")[0] for h in hits),
                         ["DESIGN.md", "Makefile", "notes.rst", "plugins/x/.claude-plugin/plugin.json"])
        self.assertIn("DESIGN.md:5:", " ".join(hits))


if __name__ == "__main__":
    unittest.main()
