"""BP-001 criteria 7 and 8: the skills ship, the writer never pushes, and wired targets say how.

ponytail: reads the files as text; the scripts' behaviour is in test_ship.py and test_hub_term.py.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted(ROOT.glob("skills/*/SKILL.md")) + sorted(ROOT.glob("commands/*.md"))


def text(rel):
    return (ROOT / rel).read_text()


class NoManualPush(unittest.TestCase):
    def test_found_the_docs(self):
        self.assertGreater(len(DOCS), 10)

    def test_no_push_origin_anywhere(self):
        hits = [str(p.relative_to(ROOT)) for p in DOCS if "Push origin" in p.read_text()]
        self.assertEqual(hits, [])


class NamesItsScripts(unittest.TestCase):
    def test_blog_publish_ships_and_pins(self):
        s = text("skills/blog-publish/SKILL.md")
        for needle in ("ship.py\" push", "ship.py\" merge", "ship.py\" verify-live", "hub_term.py\" pin"):
            self.assertIn(needle, s)

    def test_term_registration_runs_the_script(self):
        for rel in ("skills/4d-blog-engine/SKILL.md", "commands/blog-pillar.md", "commands/blog-term.md"):
            self.assertIn("hub_term.py\" register", text(rel), rel)
            self.assertNotIn("rebuild + tag", text(rel), rel)


class WiredTargets(unittest.TestCase):
    def test_wired_targets_carry_the_shipping_fields(self):
        fms = {p.name: m.group(1) for p in sorted((ROOT / "targets").glob("*.md"))
               if (m := re.match(r"---\n(.*?)\n---", p.read_text(), re.S))}
        wired = [n for n, fm in fms.items() if re.search(r"^status: wired\b", fm, re.M)]
        self.assertGreaterEqual(len(wired), 2)
        for name in wired:
            fm = fms[name]
            for field in ("default_branch_protected:", "required_checks:", "auto_linker_file:"):
                self.assertIn(field, fm, f"{name} lacks {field}")


if __name__ == "__main__":
    unittest.main()
