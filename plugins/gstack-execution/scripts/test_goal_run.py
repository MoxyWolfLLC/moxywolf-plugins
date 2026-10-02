"""GO-003: the runner, with stub builds. Every 'item' here is a commit made by the test; the runner
only sees heads, the goal folder on main and its own ledger, as it would in a real run."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_run as gr  # noqa: E402

BRIEF = """## Goal tests
- `tests/test_g.py::G.test_done` (outcome)
- `tests/test_g.py::G.test_safe` (invariant)

## Spend cap
$5

## Provider budgets
- openrouter: $3

## Max calls
10

## Max items
3

## Max review rounds per item
2
"""
PLAN = "1. scaffold\n   - a\n2. make it done\n   - b\n3. polish\n   - c\n"
TESTS = '''# drafted-by: gpt/gpt-6
import unittest


def candidate(expr):
    """Run the candidate as its own program and return what it prints for expr. Goal tests never
    import the candidate: its code runs in a separate process, so it can't reach this one."""
    import os, subprocess, sys
    r = subprocess.run([sys.executable, "-c", "import goalmod; print(repr(%s))" % expr],
                       cwd=os.environ["GOAL_CANDIDATE"], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


class G(unittest.TestCase):
    def test_done(self):
        """Scenario: x"""
        self.assertEqual(candidate("goalmod.done"), "True")

    def test_safe(self):
        """Scenario: y"""
        self.assertEqual(candidate("goalmod.safe"), "True")
'''


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name, "repo")
        self.repo.mkdir()
        self.saved = os.environ.get("GSTACK_GOAL_RUN_DIR")
        os.environ["GSTACK_GOAL_RUN_DIR"] = str(Path(self.tmp.name, "runs"))
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t"); self.git("config", "user.name", "t")
        self.commit("goal approved", {"goals/g1/GOAL.md": BRIEF, "goals/g1/PLAN.md": PLAN,
                                      "goals/g1/tests/test_g.py": TESTS, "goals/g1/holdout.sha256": "a" * 64 + "\n",
                                      "goalmod.py": "done = False\nsafe = True\n"})
        self.tree = self.git("rev-parse", "main:goals/g1")
        self.branches = []

    def tearDown(self):
        os.environ.pop("GSTACK_GOAL_RUN_DIR", None) if self.saved is None else os.environ.__setitem__("GSTACK_GOAL_RUN_DIR", self.saved)
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, msg, files):
        for path, text in files.items():
            p = self.repo / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        self.git("add", "-A"); self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def verify(self, errors=(), drafted=("gpt",), reader="gemini"):
        return lambda g, p, n: ({"head": "h" * 40, "tree": self.tree, "review_id": 4242, "drafted_by": list(drafted),
                                 "read_by": reader}, list(errors))

    def merged_pr(self, **over):
        st = gr.load("g1")
        pr = {"base": {"ref": "main"}, "head": {"ref": "goal/g1", "sha": st["results"][-1]["head"]},
              "merged": True, "merge_commit_sha": "f" * 40}
        for k, v in over.items():
            if isinstance(v, dict):
                pr[k] = dict(pr[k], **v)
            else:
                pr[k] = v
        return lambda path: pr

    def create(self, ref, sha):
        self.branches.append((ref, sha))
        self.git("branch", ref, sha)

    def start(self, builder="claude/claude-opus", granted=None, **kw):
        return gr.start(self.repo, "g1", 7, builder, kw.get("verify") or self.verify(),
                        granted or {"contents": "write", "pull_requests": "write"}, self.create, base="main")

    def item(self, goalmod, msg="item"):
        self.git("switch", "-q", "goal/g1")
        sha = self.commit(msg, {"goalmod.py": goalmod})
        self.git("switch", "-q", "main")
        return sha

    def next(self):
        return gr.next_step(self.repo, "g1", base="main")

    def test_a_plan_runs_in_order_to_complete(self):
        st = self.start()
        self.assertEqual(self.branches, [("goal/g1", self.git("rev-parse", "main"))])
        self.assertEqual((st["max_items"], st["max_rounds"]), (3, 2))
        ok, step = self.next()
        self.assertEqual((ok, step["step"], step["item"]["n"], step["item"]["title"]), (True, "build", 1, "scaffold"))
        self.assertEqual(step["base_branch"], "goal/g1")
        out = gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\nx = 1\n"), 1)
        self.assertEqual(out["results"], {"tests/test_g.py::G.test_done": "failed", "tests/test_g.py::G.test_safe": "passed"})
        self.assertEqual(self.next()[1]["item"]["n"], 2)
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 2)
        self.assertEqual(self.next(), (True, self.next()[1]))
        self.assertEqual(self.next()[1]["step"], "finish")
        self.assertEqual(gr.complete("g1", 9, "f" * 40, self.merged_pr())["outcome"], "complete")
        rec = gr.record("g1")
        self.assertIn("- Outcome: complete", rec)
        self.assertIn("by review 4242", rec)                                 # review F3
        self.assertIn("drafted by gpt, read by gemini", rec)
        self.assertIn("git revert -m 1 --no-edit " + "f" * 40, rec)
        self.assertIn("3. polish - not built", rec)

    def test_dependent_items_on_their_own_branches_build_on_each_other(self):  # review F5
        self.start()
        step = self.next()[1]
        self.assertEqual((step["branch_from"], step["base_branch"]), ("origin/goal/g1", "goal/g1"))

        def item_branch(name, files):
            self.git("switch", "-q", "-c", name, "goal/g1")          # branched from the goal head, not main
            self.commit(name, files)
            self.git("switch", "-q", "goal/g1")
            self.git("merge", "-q", "--no-ff", "--no-edit", name)    # the item PR merges into goal/g1
            head = self.git("rev-parse", "HEAD")
            self.git("switch", "-q", "main")
            return head

        gr.merged(self.repo, "g1", item_branch("build/item-1", {"helper.py": "value = True\n"}), 1)
        self.assertEqual(self.next()[1]["item"]["n"], 2)
        out = gr.merged(self.repo, "g1", item_branch("build/item-2", {
            "goalmod.py": "import helper\ndone = helper.value\nsafe = True\n"}), 2)
        self.assertEqual(out["results"]["tests/test_g.py::G.test_done"], "passed")   # item 2 used item 1's module
        self.assertEqual(self.next()[1]["step"], "finish")

    def test_an_item_that_ends_without_a_merge_stops_the_run(self):  # review 2 F1
        self.start()
        self.assertEqual(self.next()[1]["item"]["n"], 1)
        out = gr.failed("g1", 1, "rounds_exhausted after 2 rounds")
        self.assertEqual(out["outcome"], "stopped")
        self.assertIn("item 1 ended without a merge: rounds_exhausted", out["reason"])
        self.assertEqual(self.next(), (False, out))                       # stays ended
        self.assertIn("- Outcome: stopped", gr.record("g1"))
        with self.assertRaisesRegex(gr.Refused, "already ended"):
            gr.failed("g1", 1, "again")

    def test_one_merge_advances_one_item(self):  # review 2 F2
        self.start()
        head = self.item("done = False\nsafe = True\nx = 1\n")
        gr.merged(self.repo, "g1", head, 1)
        with self.assertRaisesRegex(gr.Refused, "already recorded"):
            gr.merged(self.repo, "g1", head, 2)
        with self.assertRaisesRegex(gr.Refused, "isn't the item in progress"):
            gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\nx = 2\n"), 3)
        self.assertEqual(gr.load("g1")["done"], [1])
        self.assertEqual(self.next()[1]["item"]["n"], 2)

    def test_a_regressed_outcome_stops_the_run(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 1)
        out = gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n"), 2)
        self.assertEqual(out["outcome"], "stopped")
        self.assertIn("passed before and is now failed", out["reason"])
        self.assertEqual(self.next(), (False, out))

    def test_a_failing_invariant_stops_the_run(self):
        self.start()
        out = gr.merged(self.repo, "g1", self.item("done = False\nsafe = False\n"), 1)
        self.assertEqual(out["outcome"], "stopped")
        self.assertIn("invariant tests/test_g.py::G.test_safe failed", out["reason"])

    def test_a_plan_that_runs_out_is_exhausted(self):
        self.start()
        for i in range(3):
            self.assertTrue(self.next()[0])
            gr.merged(self.repo, "g1", self.item(f"done = False\nsafe = True\nn = {i}\n"), i + 1)
        ok, out = self.next()
        self.assertEqual((ok, out["outcome"]), (False, "exhausted"))
        self.assertIn("test_done", out["reason"])

    def test_a_goal_changed_on_main_mid_run_stops(self):
        self.start()
        self.commit("edit the goal", {"goals/g1/PLAN.md": PLAN + "4. more\n   - d\n"})
        ok, out = self.next()
        self.assertEqual((ok, out["outcome"]), (False, "stopped"))
        self.assertIn("changed on main mid-run", out["reason"])

    def test_halt_on_main_stops(self):
        self.start()
        self.commit("halt", {"goals/g1/HALT": "stop\n"})
        self.assertIn("HALT is on main", self.next()[1]["reason"])

    def test_spend_at_eighty_percent_stops(self):
        self.start()
        ledger = Path(os.environ["GSTACK_GOAL_RUN_DIR"], "g1", "spend.jsonl")
        ledger.write_text(json.dumps({"provider": "openrouter", "cost": "2.40", "transport": "openrouter"}) + "\n")
        ok, out = self.next()
        self.assertEqual((ok, out["outcome"]), (False, "stopped"))
        self.assertIn("openrouter spent $2.40 of its $3 budget", out["reason"])

    def test_a_builder_from_the_drafting_or_reading_family_is_refused(self):
        with self.assertRaisesRegex(gr.Refused, "drafted or read"):
            self.start(builder="gpt/gpt-6")
        with self.assertRaisesRegex(gr.Refused, "drafted or read"):
            self.start(builder="gemini/gemini-3")
        self.assertEqual(self.branches, [])

    def test_a_token_that_reaches_secrets_or_workflows_is_refused(self):
        for extra in ({"secrets": "read"}, {"workflows": "write"}):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(gr.Refused, "contents and pull_requests only"):
                    self.start(granted=dict({"contents": "write"}, **extra))
        self.assertEqual(self.branches, [])

    def test_cli_start_needs_a_goal_run_token(self):  # GO-003.5
        saved = {k: os.environ.pop(k, None) for k in ("GITHUB_TOKEN", "GSTACK_GOAL_RUN_TOKEN")}
        os.environ["GITHUB_TOKEN"] = "x"
        try:
            self.assertEqual(gr.main(["start", "g1", "--pr", "7", "--builder", "claude/x"], self.repo), 1)
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.assertEqual(self.branches, [])

    def test_an_unverified_goal_is_refused(self):
        with self.assertRaisesRegex(gr.Refused, "verify refused"):
            self.start(verify=self.verify(errors=["no standing APPROVED review"]))

    def test_a_tree_on_main_that_isnt_the_approved_one_is_refused(self):
        self.tree = "0" * 40
        with self.assertRaisesRegex(gr.Refused, "isn't the tree Dorian approved"):
            self.start()

    def test_one_run_at_a_time_and_complete_needs_every_test(self):
        self.start()
        with self.assertRaisesRegex(gr.Refused, "already has a run"):
            self.start()
        with self.assertRaisesRegex(gr.Refused, "every goal test passing"):
            gr.complete("g1", 9, "f" * 40, lambda path: {})

    def test_complete_needs_githubs_word_that_the_goal_merged(self):  # review F2
        self.start()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 1)
        for over, msg in [({"merged": False}, "is not merged"), ({"base": {"ref": "goal/g1"}}, "not main"),
                          ({"head": {"ref": "build/x"}}, "not goal/g1"), ({"merge_commit_sha": "e" * 40}, "not ffffffffffff"),
                          ({"head": {"sha": "d" * 40}}, "where the goal tests passed")]:
            with self.subTest(over=over):
                with self.assertRaisesRegex(gr.Refused, msg):
                    gr.complete("g1", 9, "f" * 40, self.merged_pr(**over))
                self.assertIsNone(gr.load("g1")["outcome"])
        self.assertEqual(gr.complete("g1", 9, "f" * 40, self.merged_pr())["outcome"], "complete")

    def test_an_installed_plugin_copy_refuses_to_run(self):  # review F1
        import shutil
        copy = Path(self.tmp.name, "plugin", "scripts")
        shutil.copytree(Path(gr.__file__).parent, copy, ignore=shutil.ignore_patterns("__pycache__"))
        r = subprocess.run([sys.executable, str(copy / "goal_run.py"), "next", "g1"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("runs from a checkout of the repository", r.stderr)

    def test_no_run_folder_no_run(self):
        os.environ.pop("GSTACK_GOAL_RUN_DIR")
        with self.assertRaisesRegex(gr.Refused, "GSTACK_GOAL_RUN_DIR"):
            self.start()

    def test_cli_next_exits_zero_only_to_continue(self):
        self.start()
        self.assertEqual(gr.main(["next", "g1"], self.repo), 1)   # origin/main doesn't exist here: stop
        self.assertEqual(gr.load("g1")["outcome"], "stopped")


if __name__ == "__main__":
    unittest.main()
