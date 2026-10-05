"""GO-007.6: goal_new.py with stub drafters. No model is called."""
import contextlib
import hashlib
import io
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import goal_new as gn  # noqa: E402

BRIEF = """## Goal tests
- tests/test_tool.py::Tool.test_prints (outcome)
- tests/test_tool.py::Tool.test_never_leaks (invariant)
"""
PLAN = "1. Build the tool\n   - it prints\n"
TESTS = """=====FILE tests/test_tool.py=====
```python
# drafted-by: claude/someone-else
import unittest
class Tool(unittest.TestCase):
    def test_prints(self):
        \"\"\"Scenario: x\"\"\"
    def test_never_leaks(self):
        \"\"\"Scenario: y\"\"\"
```
"""
HOLDOUT = "import unittest\nclass Holdout(unittest.TestCase):\n    def test_secret_case_7f3a(self):\n        pass\n"


class GoalNew(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name) / "repo"
        self.g = self.root / "goals" / "g1"
        self.g.mkdir(parents=True)
        (self.g / "GOAL.md").write_text(BRIEF)
        (self.g / "PLAN.md").write_text(PLAN)
        self.home = Path(t.name) / "holdouts"
        os.environ["GSTACK_GOAL_HOLDOUTS"] = str(self.home)
        self.addCleanup(os.environ.pop, "GSTACK_GOAL_HOLDOUTS", None)

    def run_cmd(self, fn, *args, **kw):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = fn(str(self.g), *args, **kw)
        return rc, out.getvalue()

    def write_tests(self):
        self.run_cmd(gn.cmd_tests, ask=lambda p, cwd: TESTS)

    def test_tests_are_written_with_the_drafters_family(self):
        rc, out = self.run_cmd(gn.cmd_tests, ask=lambda p, cwd: TESTS)
        src = (self.g / "tests/test_tool.py").read_text()
        self.assertEqual(rc, 0)
        self.assertTrue(src.startswith(f"# drafted-by: gpt/{gn.DRAFTER[1]}\nimport unittest"), src[:80])
        self.assertNotIn("claude/someone-else", src)
        self.assertNotIn("```", src)
        self.assertIn("examined 2 goal tests in 1 files", out)

    def test_tests_missing_a_named_file_are_refused_and_nothing_is_written(self):
        with self.assertRaises(gn.Refused):
            self.run_cmd(gn.cmd_tests, ask=lambda p, cwd: TESTS.replace("test_tool.py", "test_other.py"))
        self.assertFalse((self.g / "tests").exists())

    def test_a_brief_with_no_goal_tests_is_refused(self):
        (self.g / "GOAL.md").write_text("## Outcome\nx\n")
        with self.assertRaises(gn.Refused):
            self.run_cmd(gn.cmd_tests, ask=lambda p, cwd: TESTS)

    def test_the_holdout_lands_outside_the_repo_private_and_hashed_and_is_never_printed(self):
        rc, out = self.run_cmd(gn.cmd_holdout, ask=lambda p, cwd: "```python\n" + HOLDOUT + "```")
        path = self.home / "g1.py"
        self.assertEqual(rc, 0)
        self.assertEqual(path.read_text(), HOLDOUT)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.home.stat().st_mode), 0o700)
        self.assertEqual((self.g / "holdout.sha256").read_text().strip(), hashlib.sha256(HOLDOUT.encode()).hexdigest())
        self.assertNotIn("secret_case_7f3a", out)
        self.assertIn('"secret": "GOAL_G1_HOLDOUT"', out)
        self.assertEqual([p.name for p in self.root.rglob("*") if p.is_file()].count("g1.py"), 0)

    def test_a_holdout_folder_inside_the_repo_is_refused(self):
        os.environ["GSTACK_GOAL_HOLDOUTS"] = str(self.root / "hold")
        with self.assertRaises(gn.Refused):
            self.run_cmd(gn.cmd_holdout, ask=lambda p, cwd: HOLDOUT)
        self.assertFalse((self.g / "holdout.sha256").exists())

    def test_a_holdout_that_does_not_parse_or_has_no_class_is_refused(self):
        for bad in ("class Holdout(:\n", "import unittest\n"):
            with self.assertRaises(gn.Refused):
                self.run_cmd(gn.cmd_holdout, ask=lambda p, cwd: bad)
        self.assertFalse((self.g / "holdout.sha256").exists())

    def test_the_reading_covers_every_test_and_names_its_reader(self):
        self.write_tests()
        text = "`tests/test_tool.py::Tool.test_prints` checks a. `tests/test_tool.py::Tool.test_never_leaks` checks b."
        rc, out = self.run_cmd(gn.cmd_read, post=lambda p: (text, "google/gemini-3.1-pro-preview"))
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("## Plain-English reading\n"))
        self.assertTrue(out.rstrip().endswith("Read by: gemini/gemini-3.1-pro-preview"))

    def test_a_reading_that_misses_a_test_or_runs_below_the_floor_is_refused(self):
        self.write_tests()
        with self.assertRaises(gn.Refused):
            self.run_cmd(gn.cmd_read, post=lambda p: ("`tests/test_tool.py::Tool.test_prints` only", "google/gemini-3.1-pro-preview"))
        full = "`tests/test_tool.py::Tool.test_prints` `tests/test_tool.py::Tool.test_never_leaks`"
        with self.assertRaises(gn.Refused):
            self.run_cmd(gn.cmd_read, post=lambda p: (full, "google/gemini-2.0-flash"))

    def test_the_reader_must_be_another_family_than_the_drafter(self):
        self.write_tests()
        p = self.g / "tests/test_tool.py"
        p.write_text(p.read_text().replace("# drafted-by: gpt/", "# drafted-by: gemini/"))
        full = "`tests/test_tool.py::Tool.test_prints` `tests/test_tool.py::Tool.test_never_leaks`"
        with self.assertRaises(gn.Refused):
            self.run_cmd(gn.cmd_read, post=lambda p: (full, "google/gemini-3.1-pro-preview"))


if __name__ == "__main__":
    unittest.main()
