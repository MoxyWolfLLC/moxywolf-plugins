"""0.45.1: the GitHub root is the shared drive. No skill or command names the old local root.

The root moved ~/Documents/GitHub -> ~/GitHub (D4) -> Shared drives/GitHub (D5). A stale root in a
skill gets copied into every project's instructions by /init-project, so the check guards the source.

ponytail: substring scan of skills/ and commands/. README history is left alone on purpose.
"""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
OLD = re.compile(r"(/Users/doriancougias|~)/GitHub[`/]")


def hits_in(text):
    return [m.group(0) for m in OLD.finditer(text)]


class GitHubRoot(unittest.TestCase):
    def test_no_skill_or_command_names_the_old_root(self):
        files = [p for d in ("skills", "commands") for p in (PLUGIN / d).rglob("*.md")]
        self.assertGreater(len(files), 0, "examined nothing")
        hits = [f"{p.relative_to(PLUGIN)}: {h}" for p in files for h in hits_in(p.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])

    def test_the_check_catches_the_old_root_and_passes_the_new(self):
        self.assertTrue(hits_in("2. **GitHub** — `/Users/doriancougias/GitHub`"))
        self.assertTrue(hits_in("cd ~/GitHub/Projects"))
        self.assertEqual(hits_in("`/Users/doriancougias/Library/CloudStorage/GoogleDrive-x/Shared drives/GitHub/Projects`"), [])


if __name__ == "__main__":
    unittest.main()
