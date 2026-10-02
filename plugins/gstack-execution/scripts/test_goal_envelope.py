import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_envelope as ge  # noqa: E402

CO = "/.github/ @dorianatmoxywolf\n/goals/ @dorianatmoxywolf\n/goal-runs/ @dorianatmoxywolf\n"
BRIEF = "## Serves\nX\n\n## Allowed paths\n- `src/**`\n- `docs/notes.md`\n"


class Envelope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t"); self.git("config", "user.name", "t")
        self.write(".github/CODEOWNERS", CO)
        self.write("goals/g1/GOAL.md", BRIEF)
        self.write("src/a.py", "a = 1\n")
        self.commit("main")
        self.git("switch", "-q", "-c", "goal/g1")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()

    def write(self, path, text):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, msg, files=None):
        for path, text in (files or {}).items():
            self.write(path, text)
        self.git("add", "-A"); self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def check(self, head="HEAD"):
        return ge.check(self.repo, "g1", self.git("rev-parse", head), base="main")

    def test_files_inside_allowed_paths_pass_and_are_counted(self):
        self.commit("item 1", {"src/b": "b\n"})
        self.commit("item 2", {"docs/notes.md": "n\n"})
        self.assertEqual(self.check(), ([], 2))

    def test_a_file_outside_allowed_paths_is_named(self):
        sha = self.commit("item", {"lib/x": "x\n"})
        e, n = self.check()
        self.assertEqual(n, 1)
        self.assertEqual(e, [f"{sha[:12]} changes lib/x, outside Allowed paths"])

    def test_a_codeowners_path_is_refused_even_inside_allowed_paths(self):
        self.write("goals/g1/GOAL.md", BRIEF.replace("`src/**`", "`**`"))   # widened on the branch
        self.commit("widen", {".github/workflows/x.yml": "on: push\n"})
        e, _ = self.check()
        self.assertTrue(any(".github/workflows/x.yml, a CODEOWNERS path" in x for x in e), e)
        self.assertTrue(any("goals/g1/GOAL.md, a CODEOWNERS path" in x for x in e), e)

    def test_a_brief_edited_on_the_branch_is_ignored(self):
        self.write("goals/g1/GOAL.md", BRIEF.replace("`src/**`", "`**`"))
        self.commit("widen")
        self.commit("item", {"lib/x": "x\n"})
        e, _ = self.check()
        self.assertTrue(any("lib/x, outside Allowed paths" in x for x in e), e)

    def test_main_moving_in_a_codeowners_path_syncs_but_the_same_change_authored_fails(self):
        self.commit("item", {"src/b": "b\n"})
        self.git("switch", "-q", "main")
        self.commit("owner change on main", {".github/CODEOWNERS": CO + "/ops/ @dorianatmoxywolf\n"})
        main_tip = self.git("rev-parse", "HEAD")
        self.assertEqual(self.check(main_tip), ([], 0))                     # the sync PR's head is main
        self.git("switch", "-q", "goal/g1")
        self.git("merge", "-q", "--no-edit", "main")
        self.assertEqual(self.check(), ([], 2))   # the item and a clean merge; main's commit isn't the goal's
        self.git("switch", "-q", "-c", "item2", "main")
        self.commit("authored", {".github/CODEOWNERS": CO + "/ops2/ @dorianatmoxywolf\n"})
        e, _ = self.check()
        self.assertTrue(any(".github/CODEOWNERS, a CODEOWNERS path" in x for x in e), e)

    def test_a_change_hidden_in_a_merge_resolution_is_seen(self):
        self.commit("item", {"src/b": "b\n"})
        self.git("switch", "-q", "main")
        self.commit("main moves", {"src/c": "c\n"})
        self.git("switch", "-q", "goal/g1")
        self.git("merge", "-q", "--no-commit", "main")
        self.write("lib/sneak.py", "x\n"); self.git("add", "-A"); self.git("commit", "-q", "-m", "merge main")
        e, _ = self.check()
        self.assertTrue(any("lib/sneak.py, outside Allowed paths" in x for x in e), e)

    def test_a_merge_that_discards_a_main_change_is_seen(self):  # review F1
        self.commit("item", {"src/b": "b\n"})
        self.git("switch", "-q", "main")
        self.commit("owner change on main", {".github/CODEOWNERS": CO + "/ops/ @dorianatmoxywolf\n"})
        self.git("switch", "-q", "goal/g1")
        self.git("merge", "-q", "--no-edit", "-s", "ours", "main")       # keeps the old CODEOWNERS
        e, _ = self.check()
        self.assertTrue(any(".github/CODEOWNERS, a CODEOWNERS path" in x for x in e), e)

    def test_a_changed_path_is_literal_never_a_pattern(self):  # review F2
        for name in ("docs/*.md", "docs/?otes.md", "docs/[n]otes.md"):
            with self.subTest(name=name):
                self.git("switch", "-q", "-C", "goal/g1", "main")
                self.commit("item", {name: "x\n"})
                e, _ = self.check()
                self.assertTrue(any(f"{name}, outside Allowed paths" in x for x in e), e)
        self.git("switch", "-q", "-C", "goal/g1", "main")
        self.commit("item", {"src/[x]*.py": "x\n"})                      # literal, under src/**
        self.assertEqual(self.check()[0], [])

    def test_the_run_record_is_allowed_only_alone(self):
        self.commit("item", {"src/b": "b\n"})
        self.commit("finalize", {"goal-runs/g1/RESULT.md": "complete\n"})
        self.assertEqual(self.check(), ([], 2))
        self.commit("record and more", {"goal-runs/g1/RESULT.md": "again\n", "src/c": "c\n"})
        e, _ = self.check()
        self.assertTrue(any("goal-runs/g1/RESULT.md, a CODEOWNERS path" in x for x in e), e)

    def test_another_goals_run_record_is_refused(self):
        self.commit("finalize", {"goal-runs/g2/RESULT.md": "complete\n"})
        e, _ = self.check()
        self.assertTrue(any("goal-runs/g2/RESULT.md, a CODEOWNERS path" in x for x in e), e)

    def test_a_goal_not_on_main_has_no_envelope(self):
        self.commit("item", {"src/b": "b\n"})
        e, n = ge.check(self.repo, "g9", self.git("rev-parse", "HEAD"), base="main")
        self.assertEqual(n, 0)
        self.assertIn("not on main", e[0])

    def test_only_a_clean_read_continues(self):  # a crash exits 1, so 1 can never mean continue
        self.git("switch", "-q", "main")
        self.commit("halt", {"goals/g1/HALT": "stop\n"})
        self.assertEqual(ge.main(["halted", "g1", "--base", "main"], self.repo), 1)

    def test_halt_is_read_from_main_only(self):
        self.assertFalse(ge.halted(self.repo, "g1", "main"))
        self.commit("halt on the branch", {"goals/g1/HALT": ""})
        self.assertFalse(ge.halted(self.repo, "g1", "main"))
        self.git("switch", "-q", "main")
        self.commit("halt", {"goals/g1/HALT": "stop\n"})
        self.assertTrue(ge.halted(self.repo, "g1", "main"))

    def test_revert_is_a_pull_request_never_a_reset(self):  # review F3
        import json, shlex
        cmd = ge.revert_commands("a" * 40)
        self.assertIn("git revert -m 1 --no-edit " + "a" * 40, cmd)
        self.assertNotIn("reset", cmd)
        self.assertNotIn("#", cmd)
        words = shlex.split(cmd)
        self.assertIn("revert/aaaaaaaaaaaa", words)
        self.assertEqual(words[words.index("POST") + 1], "/repos/MoxyWolfLLC/moxywolf-plugins/pulls")
        pr = json.loads(words[words.index("--data") + 1])
        self.assertEqual((pr["head"], pr["base"]), ("revert/aaaaaaaaaaaa", "main"))
        with self.assertRaises(SystemExit):
            ge.revert_commands("abc123")

    def test_an_unreadable_main_is_a_stop_not_a_continue(self):  # review F4
        self.assertEqual(ge.main(["halted", "g1", "--base", "main"], self.repo), 0)   # read, no HALT: continue
        self.assertEqual(ge.main(["halted", "g1", "--base", "origin/main"], self.repo), 3)   # never fetched
        with self.assertRaises(SystemExit):
            ge.check(self.repo, "g1", self.git("rev-parse", "HEAD"), base="no-such-ref")

    def test_cli_passes_a_sync_and_fails_a_breach(self):
        self.assertEqual(ge.main(["check", "g1", "--head", self.git("rev-parse", "main"), "--base", "main"], self.repo), 0)
        self.commit("item", {"lib/x": "x\n"})
        self.assertEqual(ge.main(["check", "g1", "--head", self.git("rev-parse", "HEAD"), "--base", "main"], self.repo), 1)
        self.assertEqual(ge.main(["check", "g1", "--base", "main"], self.repo), 2)   # --head required


if __name__ == "__main__":
    unittest.main()
