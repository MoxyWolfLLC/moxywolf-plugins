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


class G(unittest.TestCase):
    def test_done(self):
        """Scenario: x"""
        import goalmod
        self.assertTrue(goalmod.done)

    def test_safe(self):
        """Scenario: y"""
        import goalmod
        self.assertTrue(goalmod.safe)
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
        return lambda g, p, n: ({"head": "h" * 40, "tree": self.tree, "drafted_by": list(drafted), "read_by": reader}, list(errors))

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
        out = gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\nx = 1\n"))
        self.assertEqual(out["results"], {"tests/test_g.py::G.test_done": "failed", "tests/test_g.py::G.test_safe": "passed"})
        self.assertEqual(self.next()[1]["item"]["n"], 2)
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"))
        self.assertEqual(self.next(), (True, self.next()[1]))
        self.assertEqual(self.next()[1]["step"], "finish")
        self.assertEqual(gr.complete("g1", "f" * 40)["outcome"], "complete")
        rec = gr.record("g1")
        self.assertIn("- Outcome: complete", rec)
        self.assertIn("git revert -m 1 --no-edit " + "f" * 40, rec)
        self.assertIn("3. polish - not built", rec)

    def test_a_regressed_outcome_stops_the_run(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"))
        out = gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n"))
        self.assertEqual(out["outcome"], "stopped")
        self.assertIn("passed before and is now failed", out["reason"])
        self.assertEqual(self.next(), (False, out))

    def test_a_failing_invariant_stops_the_run(self):
        self.start()
        out = gr.merged(self.repo, "g1", self.item("done = False\nsafe = False\n"))
        self.assertEqual(out["outcome"], "stopped")
        self.assertIn("invariant tests/test_g.py::G.test_safe failed", out["reason"])

    def test_a_plan_that_runs_out_is_exhausted(self):
        self.start()
        for i in range(3):
            self.assertTrue(self.next()[0])
            gr.merged(self.repo, "g1", self.item(f"done = False\nsafe = True\nn = {i}\n"))
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

    def test_a_token_that_reaches_secrets_is_refused(self):
        with self.assertRaisesRegex(gr.Refused, "secrets"):
            self.start(granted={"contents": "write", "secrets": "read"})
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
            gr.complete("g1", "f" * 40)

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
