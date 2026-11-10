"""0.45.1: the GitHub root is the shared drive. No plugin's skills, commands, scripts or manifest name the old root.

The root moved ~/Documents/GitHub -> ~/GitHub (D4) -> Shared drives/GitHub (D5). A stale root in a
skill gets copied into every project's instructions by /init-project, so the check guards the source.

ponytail: regex scan of every plugin's skills/, commands/, scripts/ and plugin.json, plus the root README.
README version histories are left alone on purpose: they record where the root used to be.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD = re.compile(r"(/Users/doriancougias|~)/GitHub[`/]")


def hits_in(text):
    return [m.group(0) for m in OLD.finditer(text)]


class GitHubRoot(unittest.TestCase):
    def test_no_plugin_names_the_old_root(self):
        files = [ROOT / "README.md", *(ROOT / "plugins").glob("*/.claude-plugin/plugin.json")]
        for d in ("skills", "commands", "scripts"):
            files += [p for p in (ROOT / "plugins").glob(f"*/{d}/**/*") if p.suffix in (".md", ".py", ".sh", ".mjs", ".js", ".json")]
        self.assertGreater(len(files), 50, "examined too little")
        hits = [f"{p.relative_to(ROOT)}: {h}" for p in files for h in hits_in(p.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])

    def test_the_check_catches_the_old_root_and_passes_the_new(self):
        self.assertTrue(hits_in("2. **GitHub** — `/Users/doriancougias/GitHub`"))
        self.assertTrue(hits_in("cd ~/GitHub/Projects"))
        self.assertEqual(hits_in("`/Users/doriancougias/Library/CloudStorage/GoogleDrive-x/Shared drives/GitHub/Projects`"), [])


if __name__ == "__main__":
    unittest.main()
