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
gr.SANDBOXED = False   # the container is test_goal_checks' to test; one test below checks merged uses it

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

## Allowed paths
- `goalmod.py`
- `helper.py`
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


HOLDOUT_SRC = "import unittest\n\n\nclass Holdout(unittest.TestCase):\n    def test_h(self):\n        pass\n"
HOLDOUT_SHA = __import__("hashlib").sha256(HOLDOUT_SRC.encode()).hexdigest()

class RunnerFixture(unittest.TestCase):
    """A goal on main, a run folder, and helpers; no tests of its own (test_goal_calls reuses it)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name, "repo")
        self.repo.mkdir()
        self.saved = os.environ.get("GSTACK_GOAL_RUN_DIR")
        os.environ["GSTACK_GOAL_RUN_DIR"] = str(Path(self.tmp.name, "runs"))
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t"); self.git("config", "user.name", "t")
        self.commit("goal approved", {"goals/g1/GOAL.md": BRIEF, "goals/g1/PLAN.md": PLAN,
                                      "goals/g1/tests/test_g.py": TESTS, "goals/g1/holdout.sha256": HOLDOUT_SHA + "\n",
                                      "goalmod.py": "done = False\nsafe = True\n",
                                      ".github/CODEOWNERS": "/.github/ @d\n/goals/ @d\n/goal-runs/ @d\n"})
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

    def as_proposed(self, final_pr=9):
        """The state finalize and propose leave, without the git and API calls (tested in the finish test)."""
        st = gr.load("g1")
        st.update(finalize_pr=8, final_pr=final_pr, finalized_head=st["results"][-1]["head"])
        gr.save(st)

    def merged_pr(self, **over):
        st = gr.load("g1")
        pr = {"base": {"ref": "main"}, "head": {"ref": "goal/g1", "sha": st.get("finalized_head") or st["results"][-1]["head"]},
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
                        granted or {"contents": "write", "pull_requests": "write"}, self.create, base="main",
                        environments=kw.get("environments", lambda: ["goal-holdout"]))

    def item(self, goalmod, msg="item"):
        self.git("switch", "-q", "goal/g1")
        sha = self.commit(msg, {"goalmod.py": goalmod})
        self.git("switch", "-q", "main")
        return sha

    def next(self):
        return gr.next_step(self.repo, "g1", base="main")

    def origin(self):
        bare = Path(self.tmp.name, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        self.git("remote", "add", "origin", str(bare))
        self.git("push", "-q", "origin", "main", "goal/g1")
        return bare

    envs = staticmethod(lambda: ["goal-holdout"])

    def rest_built(self):
        """The plan's other items, recorded as built; building every item is tested in the plan test."""
        st = gr.load("g1"); st["done"] = [i["n"] for i in st["items"]]; gr.save(st)


class Runner(RunnerFixture):
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
        step = self.next()[1]                    # GO-003.3: the tests pass, but item 3 is still built
        self.assertEqual((step["step"], step["item"]["n"]), ("build", 3))
        with self.assertRaisesRegex(gr.Refused, "every plan item built; item 3"):
            gr.finishing("g1")
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\npolished = True\n"), 3)
        self.assertEqual(self.next()[1]["step"], "finish")
        with self.assertRaisesRegex(gr.Refused, "needs the finish"):          # review F1: no skipping the record
            gr.complete("g1", 9, "f" * 40, self.merged_pr())
        self.as_proposed()
        self.assertEqual(gr.complete("g1", 9, "f" * 40, self.merged_pr())["outcome"], "complete")
        rec = gr.record("g1")
        self.assertIn("- Outcome: complete", rec)
        self.assertIn("by review 4242", rec)                                 # review F3
        self.assertIn("drafted by gpt, read by gemini", rec)
        self.assertIn("git revert -m 1 --no-edit " + "f" * 40, rec)
        self.assertIn("3. polish - merged", rec)

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
        self.assertEqual(self.next()[1]["item"]["n"], 3)

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
        self.as_proposed()
        for over, msg in [({"merged": False}, "is not merged"), ({"base": {"ref": "goal/g1"}}, "not main"),
                          ({"head": {"ref": "build/x"}}, "not goal/g1"), ({"merge_commit_sha": "e" * 40}, "not ffffffffffff"),
                          ({"head": {"sha": "d" * 40}}, "the tested head plus the run record")]:
            with self.subTest(over=over):
                with self.assertRaisesRegex(gr.Refused, msg):
                    gr.complete("g1", 9, "f" * 40, self.merged_pr(**over))
                self.assertIsNone(gr.load("g1")["outcome"])
        self.assertEqual(gr.complete("g1", 9, "f" * 40, self.merged_pr())["outcome"], "complete")

    def test_a_refused_item_pull_request_escalates_quoting_githubs_check(self):  # GO-006.2, pilot-1
        self.start()
        run = {"id": 5, "name": "goal-envelope", "status": "completed", "conclusion": "failure",
               "external_id": "pr=4;base_ref=goal/g1;base=" + "b" * 40,
               "output": {"title": "1 file(s) outside the envelope", "summary": "- d1 changes goals/g1/tests/test_g.py"}}
        def api(pr=None, runs=None):
            pr = dict({"base": {"ref": "goal/g1"}, "head": {"sha": "c" * 40}, "title": "loosen"}, **(pr or {}))
            def checks(path):            # GitHub's default view keeps only the newest run of each name
                rs = runs if runs is not None else [run]
                return {"check_runs": rs if "filter=all" in path else [max(rs, key=lambda r: r["id"])] if rs else []}
            return lambda path: pr if "/pulls/" in path else checks(path)
        for kw, msg in [({"pr": {"base": {"ref": "main"}}}, "not goal/g1"), ({"runs": []}, "no goal-envelope run"),
                        ({"runs": [dict(run, external_id="pr=3;base_ref=goal/g1;base=b")]}, "no goal-envelope run"),
                        ({"runs": [run, dict(run, id=6, conclusion="success")]}, "didn't refuse"),
                        ({"runs": [dict(run, id=6, conclusion="success"), dict(run, id=7, external_id="pr=3;base_ref=goal/g1;base=b")]},
                         "didn't refuse"),
                        ({"runs": [dict(run, status="in_progress", conclusion=None)]}, "didn't refuse")]:
            with self.subTest(kw=kw):
                with self.assertRaisesRegex(gr.Refused, msg):
                    gr.refused("g1", 4, api(**kw))
        other = dict(run, id=9, conclusion="success", external_id="pr=3;base_ref=goal/g1;base=b")   # review F1
        self.assertEqual(gr.refused("g1", 4, api(runs=[run, other])), {"refused": 4, "check": 5})
        with self.assertRaisesRegex(gr.Refused, "already in the run record"):
            gr.refused("g1", 4, api())
        rec = gr.record("g1")
        self.assertIn("escalation (outside_envelope), waiting for Dorian", rec)
        self.assertIn("refused by goal-envelope: 1 file(s) outside the envelope", rec)
        self.assertIn("- d1 changes goals/g1/tests/test_g.py", rec)
        self.assertIsNone(gr.load("g1")["outcome"])          # held, not ended
        self.assertIsNone(self.next()[0])
        gr.acknowledge("g1", 1, "seen; carry on")
        self.assertEqual(self.next()[1]["step"], "build")

    def test_the_finish_finalizes_then_proposes_then_completes(self):  # GO-003.7
        self.start()
        bare = self.origin()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 1)
        self.rest_built()
        self.git("push", "-q", "origin", "goal/g1")
        tested = self.git("rev-parse", "goal/g1")
        posts = []
        post = lambda path, data: posts.append((path, data)) or {"number": 11 if len(posts) == 1 else 12}
        holds = Path(self.tmp.name, "holdouts"); holds.mkdir()
        os.environ["GSTACK_GOAL_HOLDOUTS"] = str(holds); self.addCleanup(os.environ.pop, "GSTACK_GOAL_HOLDOUTS", None)
        with self.assertRaisesRegex(gr.Refused, "no holdout at"):
            gr.finalize(self.repo, "g1", post, environments=self.envs, base="main")
        (holds / "g1.py").write_text(HOLDOUT_SRC + "# swapped\n")
        with self.assertRaisesRegex(gr.Refused, "doesn't match the approved holdout.sha256"):
            gr.finalize(self.repo, "g1", post, environments=self.envs, base="main")
        (holds / "g1.py").write_text(HOLDOUT_SRC)
        out = gr.finalize(self.repo, "g1", post, environments=self.envs, base="main")
        self.assertEqual(out, {"finalize_pr": 11, "branch": "goal-finalize/g1"})
        self.assertEqual((posts[0][1]["head"], posts[0][1]["base"]), ("goal-finalize/g1", "goal/g1"))
        g = lambda *a: subprocess.run(["git", "--git-dir", str(bare), *a], check=True, capture_output=True, text=True).stdout.strip()
        self.assertEqual(g("rev-parse", "goal-finalize/g1^"), tested)                       # one commit on the tested head
        self.assertEqual(g("diff", "--name-only", tested, "goal-finalize/g1").split(), ["goal-runs/g1/RESULT.md", "goal-runs/g1/holdout.py"])
        self.assertEqual(g("show", "goal-finalize/g1:goal-runs/g1/holdout.py") + "\n", HOLDOUT_SRC)
        self.assertIn("# Goal run: g1", g("show", "goal-finalize/g1:goal-runs/g1/RESULT.md"))
        with self.assertRaisesRegex(gr.Refused, "already #11"):
            gr.finalize(self.repo, "g1", post, environments=self.envs, base="main")

        final = "9" * 40
        prs = {"pulls/11": {"merged": False, "base": {"ref": "goal/g1"}}}
        compare = {"files": [{"filename": "goal-runs/g1/RESULT.md"}, {"filename": "goal-runs/g1/holdout.py"}]}
        get = lambda path: prs.get(path.split("/", 3)[-1]) if "/pulls/" in path else compare
        with self.assertRaisesRegex(gr.Refused, "hasn't merged"):
            gr.propose("g1", get, post, repo=self.repo, environments=self.envs, base="main")
        prs["pulls/11"] = {"merged": True, "base": {"ref": "goal/g1"}, "merge_commit_sha": final}
        compare["files"].append({"filename": "src/sneak.py"})
        with self.assertRaisesRegex(gr.Refused, "not only the run record"):
            gr.propose("g1", get, post, repo=self.repo, environments=self.envs, base="main")
        compare["files"].pop()
        self.assertEqual(gr.propose("g1", get, post, repo=self.repo, environments=self.envs, base="main"), {"final_pr": 12})
        self.assertEqual((posts[-1][1]["head"], posts[-1][1]["base"]), ("goal/g1", "main"))
        self.assertIn("merges as the bot (GO-011.2)", posts[-1][1]["body"])

        merged_pr = {"base": {"ref": "main"}, "head": {"ref": "goal/g1", "sha": final}, "merged": True, "merge_commit_sha": "f" * 40}
        with self.assertRaisesRegex(gr.Refused, "is #12, not #13"):
            gr.complete("g1", 13, "f" * 40, lambda path: merged_pr)
        self.assertEqual(gr.complete("g1", 12, "f" * 40, lambda path: merged_pr)["outcome"], "complete")

    def test_a_sync_after_propose_is_accepted_and_anything_else_is_not(self):  # review F2
        self.start()
        self.origin()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 1)
        self.rest_built()
        self.git("switch", "-q", "goal/g1")
        final = self.commit("run record", {"goal-runs/g1/RESULT.md": "record\n"})     # what the finalize merge leaves
        self.git("switch", "-q", "main")
        st = gr.load("g1"); st.update(finalize_pr=8, final_pr=9, finalized_head=final); gr.save(st)

        moves = []

        def sync(files):
            self.git("switch", "-q", "main")
            moves.append(1)
            m = self.commit("main moves", {"other/m.py": "m = %d\n" % len(moves)})
            self.git("switch", "-q", "goal/g1")
            self.git("merge", "-q", "--no-ff", "--no-commit", m)
            for k, v in files.items():
                (self.repo / k).write_text(v)
            self.git("add", "-A"); self.git("commit", "-q", "-m", "sync main")
            head = self.git("rev-parse", "HEAD")
            self.git("switch", "-q", "main")
            return head

        moved = sync({})
        self.assertEqual(gr.resync(self.repo, "g1", moved, base="main"), {"finalized_head": moved})
        merged_pr = {"base": {"ref": "main"}, "head": {"ref": "goal/g1", "sha": moved}, "merged": True, "merge_commit_sha": "f" * 40}
        with self.assertRaisesRegex(gr.Refused, "changes the run record"):
            gr.resync(self.repo, "g1", sync({"goal-runs/g1/RESULT.md": "forged\n"}), base="main")
        with self.assertRaisesRegex(gr.Refused, "isn't a merge onto the recorded head"):
            gr.resync(self.repo, "g1", final, base="main")

        def sync_tip(extra, off_main=False):       # main's tip plus one commit, merged onto the recorded head
            self.git("switch", "-q", "-c", f"tip{len(moves)}", "main")
            moves.append(1)
            if off_main:
                self.commit("a commit main doesn't have", {"other/off.py": "off\n"})
            if extra:
                self.commit("not empty", extra)
            else:
                self.git("commit", "-q", "--allow-empty", "-m", "Sync main")
            tip = self.git("rev-parse", "HEAD")
            self.git("switch", "-q", "--detach", gr.load("g1")["finalized_head"])
            self.git("merge", "-q", "--no-ff", "-m", "sync main", tip)
            head = self.git("rev-parse", "HEAD")
            self.git("switch", "-q", "main")
            return head
        empty_sync = sync_tip(None)
        self.assertEqual(gr.resync(self.repo, "g1", empty_sync, base="main"), {"finalized_head": empty_sync})
        with self.assertRaisesRegex(gr.Refused, "isn't on main or main's tip plus an empty commit"):
            gr.resync(self.repo, "g1", sync_tip({"other/z.py": "z\n"}), base="main")
        with self.assertRaisesRegex(gr.Refused, "isn't on main or main's tip plus an empty commit"):
            gr.resync(self.repo, "g1", sync_tip(None, off_main=True), base="main")   # empty, but not on top of main
        merged_pr = dict(merged_pr, head={"ref": "goal/g1", "sha": empty_sync})
        self.assertEqual(gr.complete("g1", 9, "f" * 40, lambda path: merged_pr)["outcome"], "complete")

    def test_finalize_needs_the_goal_branch_where_the_tests_passed(self):  # GO-003.7
        self.start()
        self.origin()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 1)   # not pushed: origin is behind
        self.rest_built()
        with self.assertRaisesRegex(gr.Refused, "where the goal tests passed"):
            gr.finalize(self.repo, "g1", lambda p, d: {"number": 1}, environments=self.envs, base="main")

    def test_a_failed_holdout_stops_the_run(self):  # GO-003.6
        self.start()
        out = gr.stop("g1", "goal-holdout failed: possible reward hack")
        self.assertEqual(out["outcome"], "stopped")
        self.assertEqual(self.next(), (False, out))
        with self.assertRaisesRegex(gr.Refused, "already ended"):
            gr.stop("g1", "again")

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


class MergedUsesTheContainer(RunnerFixture):
    def test_merged_runs_the_goal_tests_through_sandboxed(self):
        """GO-003.11: merged judges a head the way goal-tests does, not on the bare host."""
        self.start(); self.next()
        seen = []
        real = gr.gb.sandboxed
        main_goalmod = (self.repo / "goalmod.py").read_text() if (self.repo / "goalmod.py").exists() else None

        def fake(goal, trusted, candidate=None):
            # review F1: the verdict script's tree is main as the run started, not the candidate
            t = Path(trusted, "goalmod.py")
            seen.append((Path(trusted) != Path(candidate), t.read_text() if t.exists() else None,
                         Path(candidate, "goalmod.py").read_text()))
            return lambda r, g, tid: "passed"
        gr.gb.sandboxed = fake
        gr.SANDBOXED = True
        try:
            out = gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\nx = 1\n"), 1)
        finally:
            gr.gb.sandboxed, gr.SANDBOXED = real, False
        self.assertEqual(seen, [(True, main_goalmod, "done = False\nsafe = True\nx = 1\n")])
        self.assertEqual(set(out["results"].values()), {"passed"})


class Resume(RunnerFixture):
    """Goal gstack-delivery-through-merge item 2: resume reads the persisted delivery, re-observes
    GitHub and the review records, records only what GitHub itself answered, and returns the next
    supervisor action; an unreadable budget or authority record blocks it."""

    def delivery_state(self):
        self.start(); head = self.item("done = True\nsafe = True\n")
        st = gr.load("g1")
        reviews = Path(self.tmp.name, "reviews"); (reviews / "rev-1").mkdir(parents=True)
        (reviews / "rev-1" / "state.json").write_text(json.dumps({"outcome": "no_blocking_findings", "heads": [[head]]}))
        (reviews / "rev-1" / "packet.json").write_text(json.dumps({"repos": [{"path": str(self.repo), "head": head, "base": st["main_at_start"], "review_base": st["main_at_start"]}]}))
        os.environ["GSTACK_PEER_REVIEW_DIR"] = str(reviews); self.addCleanup(os.environ.pop, "GSTACK_PEER_REVIEW_DIR", None)
        st["delivery"] = {"schema_version": 1, "goal": "g1", "approval": {"repo": "o/r", "pr": 7, "review_id": 4242, "head": "h" * 40, "owner": "d"},
                          "max_review_rounds": 3, "active_seconds": 5, "source_bindings": [],
                          "changes": {"implementation": {"repo": "o/r", "path": str(self.repo), "base": st["main_at_start"], "head": head,
                                                         "target": "main", "pr": 42, "review_id": "rev-1", "review_attempts": [],
                                                         "original_findings": [], "merge": None, "release_record": None}},
                          "release_companion": None, "required_checkouts": []}
        gr.save(st)
        d = gr.run_dir("g1"); (d / "spend.jsonl").touch()
        self.assertTrue((d / "ledger.jsonl").is_file() and (d / "goal" / "GOAL.md").is_file())
        return head

    def github(self, head, merged=False, checks="success", approval=None, base_ref="main", other_repo=None):
        """A GitHub reader for the delivery: the approving review, one pull request and its checks.
        other_repo: {pr: pr_json} answered for repository o/other (review F5)."""
        approval = ({"id": 4242, "state": "APPROVED", "commit_id": "h" * 40, "user": {"login": "d"}} if approval is None
                    else None if approval == "missing" else approval)
        def get(path):
            if path.startswith("repos/o/other/") and other_repo is not None:
                if path.endswith("/pulls/42"):
                    return other_repo
                if path.endswith("/check-runs"):
                    return {"check_runs": []}
                return None
            if path.endswith("/pulls/7/reviews/4242"):
                return approval
            if path.endswith("/pulls/42"):
                return {"number": 42, "merged": merged, "merge_commit_sha": "m" * 40 if merged else None,
                        "head": {"sha": head}, "base": {"ref": base_ref, "sha": gr.load("g1")["main_at_start"], "repo": {"full_name": "o/r"}},
                        "mergeable_state": "clean", "merged_by": {"login": "moxywolf-agent[bot]"}, "merged_at": "t"}
            if path.endswith("/check-runs"):
                bound = f"pr=42;base_ref={base_ref};base={gr.load('g1')['main_at_start']}"
                return {"check_runs": [{"id": i, "name": n, "status": "completed", "conclusion": checks, "external_id": bound}
                                       for i, n in enumerate(("tests", "goal-envelope", "goal-tests"), 1)]}
            return None
        return get

    def test_resume_establishes_the_approval_and_the_ledgers_before_anything(self):   # review F1
        head = self.delivery_state()
        for bad in ({"id": 4242, "state": "COMMENTED", "commit_id": "h" * 40, "user": {"login": "d"}},
                    {"id": 4242, "state": "APPROVED", "commit_id": "x" * 40, "user": {"login": "d"}},
                    {"id": 4242, "state": "APPROVED", "commit_id": "h" * 40, "user": {"login": "someone-else"}}, "missing"):
            with self.assertRaises(gr.Refused) as c:
                gr.resume("g1", self.github(head, approval=bad), "o/r")
            self.assertIn("authority not established", str(c.exception))
        st = gr.load("g1"); st["delivery"]["approval"]["head"] = "f" * 40; gr.save(st)   # an invented approval head
        with self.assertRaises(gr.Refused) as c:
            gr.resume("g1", self.github(head), "o/r")
        self.assertIn("not this run's", str(c.exception))
        st = gr.load("g1"); st["delivery"]["approval"]["head"] = "h" * 40; gr.save(st)
        (gr.run_dir("g1") / "ledger.jsonl").write_text("")                                 # valid JSON, no grants
        with self.assertRaises(gr.Refused) as c:
            gr.resume("g1", self.github(head), "o/r")
        self.assertIn("grants no push", str(c.exception))

    def test_a_review_of_another_head_or_a_retargeted_pull_request_does_not_merge(self):   # review F2
        head = self.delivery_state()
        reviews = Path(os.environ["GSTACK_PEER_REVIEW_DIR"])
        (reviews / "rev-1" / "state.json").write_text(json.dumps({"outcome": "no_blocking_findings", "heads": [["o" * 40]]}))
        out = gr.resume("g1", self.github(head), "o/r")
        self.assertIn("pending", out["next"]); self.assertIn("not the candidate head", out["next"]["pending"])
        (reviews / "rev-1" / "state.json").write_text(json.dumps({"outcome": "no_blocking_findings", "heads": [[head]]}))
        base = gr.load("g1")["main_at_start"]
        (reviews / "rev-1" / "packet.json").write_text(json.dumps({"repos": [{"path": str(self.repo), "head": head, "base": base, "review_base": base}]}))
        self.assertEqual(gr.resume("g1", self.github(head), "o/r")["next"]["action"], "merge")
        self.assertIn("blocked", gr.resume("g1", self.github(head, base_ref="release"), "o/r")["next"])
        # round 2 F2: the review must have been of this candidate range, from this repository, with a packet
        (reviews / "rev-1" / "packet.json").write_text(json.dumps({"repos": [{"path": str(self.repo), "head": head, "base": "e" * 40, "review_base": "e" * 40}]}))
        out = gr.resume("g1", self.github(head), "o/r"); self.assertIn("not the candidate range", out["next"]["pending"])
        (reviews / "rev-1" / "packet.json").unlink()
        out = gr.resume("g1", self.github(head), "o/r"); self.assertIn("no packet", out["next"]["pending"])

    def test_a_two_repository_review_is_read_at_this_change_repository(self):   # round 2 F8
        head = self.delivery_state()
        reviews = Path(os.environ["GSTACK_PEER_REVIEW_DIR"]); base = gr.load("g1")["main_at_start"]
        other = Path(self.tmp.name, "other"); other.mkdir()
        (reviews / "rev-1" / "state.json").write_text(json.dumps({"outcome": "no_blocking_findings", "heads": [["a" * 40, head]]}))
        (reviews / "rev-1" / "packet.json").write_text(json.dumps({"repos": [
            {"path": str(other), "head": "a" * 40, "base": "b" * 40, "review_base": "b" * 40},
            {"path": str(self.repo), "head": head, "base": base, "review_base": base}]}))
        self.assertEqual(gr.resume("g1", self.github(head), "o/r")["next"]["action"], "merge")
        (reviews / "rev-1" / "packet.json").write_text(json.dumps({"repos": [
            {"path": str(self.repo), "head": head, "base": base, "review_base": base},
            {"path": str(self.repo), "head": head, "base": base, "review_base": base}]}))
        self.assertIn("2 of the review's 2 repositories match", gr.resume("g1", self.github(head), "o/r")["next"]["pending"])

    def test_a_persisted_merge_github_contradicts_is_invalidated_not_trusted(self):   # review F3
        head = self.delivery_state()
        st = gr.load("g1"); st["delivery"]["changes"]["implementation"]["merge"] = {"verified": True, "head": head, "sha": head}; gr.save(st)
        out = gr.resume("g1", self.github(head, merged=False), "o/r")
        m = gr.load("g1")["delivery"]["changes"]["implementation"]["merge"]
        self.assertFalse(m["verified"]); self.assertTrue(m["contradicted"]); self.assertEqual(m["was"]["sha"], head)
        self.assertEqual(out["next"]["action"], "merge", "GitHub's answer, not the record, decides: the candidate is unmerged and green")
        self.assertNotEqual(out["delivery_status"], "complete")
        out = gr.resume("g1", self.github(head, merged=True), "o/r")       # GitHub's own answer, then, is what counts
        self.assertEqual(out["next"]["action"], "record_release")

    def test_two_repositories_sharing_a_pull_request_number_are_observed_apart(self):   # review F5
        head = self.delivery_state()
        st = gr.load("g1"); ch = st["delivery"]["changes"]["implementation"]
        st["delivery"]["changes"]["other"] = dict(ch, repo="o/other", pr=42, review_id="rev-1", merge=None, release_record=None)
        gr.save(st)
        other = {"number": 42, "merged": True, "merge_commit_sha": head, "head": {"sha": head}, "base": {"ref": "main", "repo": {"full_name": "o/other"}},
                 "merged_by": {"login": "moxywolf-agent[bot]"}, "merged_at": "t"}
        out = gr.resume("g1", self.github(head, merged=False, other_repo=other), "o/r")
        d = gr.load("g1")["delivery"]["changes"]
        self.assertIsNone(d["implementation"]["merge"], "the other repository's merge must not mark this one")
        self.assertTrue(d["other"]["merge"]["verified"]); self.assertIn("/repos/o/other/pulls/42", d["other"]["merge"]["observed_from"])
        self.assertEqual(out["next"], {"action": "merge", "change": "implementation", "head": head, "pr": 42})

    def test_resume_observes_and_returns_merge_when_everything_is_green(self):
        head = self.delivery_state()
        out = gr.resume("g1", self.github(head), "o/r")
        self.assertEqual(out["next"], {"action": "merge", "change": "implementation", "head": head, "pr": 42})
        self.assertEqual(out["delivery_status"], "in_progress")
        saved = gr.load("g1")["delivery"]
        self.assertIsNone(saved["changes"]["implementation"]["merge"], "no merge was observed, so none is recorded")
        self.assertEqual(saved["last_observed"]["next"]["action"], "merge")

    def test_a_declared_merge_counts_for_nothing_and_an_observed_one_is_recorded_from_github(self):
        head = self.delivery_state()
        st = gr.load("g1"); st["delivery"]["changes"]["implementation"]["merge"] = {"head": head, "sha": head}; gr.save(st)
        out = gr.resume("g1", self.github(head), "o/r")
        self.assertEqual(out["next"]["action"], "merge", "a model-written merge field is not a merge")
        out = gr.resume("g1", self.github(head, merged=True), "o/r")
        self.assertEqual(out["next"]["action"], "record_release")
        m = gr.load("g1")["delivery"]["changes"]["implementation"]["merge"]
        self.assertTrue(m["verified"]); self.assertEqual(m["merged_by"], "moxywolf-agent[bot]"); self.assertIn("/pulls/42", m["observed_from"])

    def test_red_checks_or_an_unclean_review_are_pending_and_an_unreadable_budget_blocks(self):
        head = self.delivery_state()
        self.assertIn("pending", gr.resume("g1", self.github(head, checks="failure"), "o/r")["next"])
        Path(os.environ["GSTACK_PEER_REVIEW_DIR"], "rev-1", "state.json").write_text(json.dumps({"outcome": "blocking_findings", "heads": [[head]]}))
        self.assertIn("pending", gr.resume("g1", self.github(head), "o/r")["next"])
        (gr.run_dir("g1") / "ledger.jsonl").write_text("{not json\n")
        with self.assertRaises(gr.Refused) as c:
            gr.resume("g1", self.github(head), "o/r")
        self.assertIn("authority", str(c.exception))
        (gr.run_dir("g1") / "ledger.jsonl").unlink()
        with self.assertRaises(gr.Refused):
            gr.resume("g1", self.github(head), "o/r")

    def test_a_run_without_a_delivery_record_cannot_resume(self):
        self.start()
        with self.assertRaises(gr.Refused):
            gr.resume("g1", self.github("x" * 40), "o/r")



class ResumeExecutes(Resume):
    """Goal gstack-delivery-through-merge item 3: with a GitHub writer, resume carries out each
    allowed action through the existing gates; a lost response is found by observing, never by a
    second merge request; a record already written is reused; a gate that holds stops it."""

    def writer(self, fail=False):
        calls = []
        def put(path, data):
            calls.append((path, data))
            if fail:
                raise ConnectionResetError("the response was lost")
            return {"merged": True}
        return put, calls

    def test_the_owner_gate_still_holding_stops_before_any_merge_request(self):
        head = self.delivery_state()
        put, calls = self.writer()
        base_get = self.github(head)
        get = lambda path: ({"environments": [{"name": "goal-holdout"}]} if path.endswith("/environments") else [] if "/deployments" in path
                            else base_get(path))
        with self.assertRaises(gr.Refused) as c:      # the real act(): main isn't this run's goal pull request
            gr.resume("g1", get, "o/r", put=put)
        self.assertIn("an item merges into goal/g1, not main", str(c.exception))
        self.assertEqual(calls, [])
        self.assertNotIn("merge_requested", gr.load("g1")["delivery"]["changes"]["implementation"])

    def test_a_moved_pull_request_head_is_never_merged(self):
        head = self.delivery_state()
        put, calls = self.writer()
        out = gr.resume("g1", self.github("o" * 40), "o/r", put=put)
        self.assertIn("blocked", out["next"]); self.assertIn("moved head", out["next"]["blocked"])
        self.assertEqual((calls, out["executed"]), ([], []))

    def test_a_lost_merge_response_is_found_on_github_and_never_requested_again(self):
        head = self.delivery_state()
        orig = gr.act; gr.act = lambda *a, **k: {"allowed": "merge"}; self.addCleanup(setattr, gr, "act", orig)
        put, calls = self.writer(fail=True)
        out = gr.resume("g1", self.github(head), "o/r", put=put)
        self.assertEqual(len(calls), 1); self.assertEqual(calls[0][1]["sha"], head)
        self.assertIn("doesn't show it merged yet", out["stopped_by"])
        ch = gr.load("g1")["delivery"]["changes"]["implementation"]
        self.assertIn("lost", ch["merge_requested"]["response"]); self.assertFalse((ch.get("merge") or {}).get("verified"))
        self.assertEqual(out["executed"][0]["action"], "merge")
        put2, calls2 = self.writer()
        reviews = Path(os.environ["GSTACK_PEER_REVIEW_DIR"])
        (reviews / "rev-1" / "release-o-r-42.json").write_text(json.dumps({"head": head, "merge_commit": "m" * 40}))
        out = gr.resume("g1", self.github(head, merged=True), "o/r", put=put2)   # GitHub had merged it
        self.assertEqual(calls2, [])
        ch = gr.load("g1")["delivery"]["changes"]["implementation"]
        self.assertTrue(ch["merge"]["verified"]); self.assertTrue(ch["release_record"]["verified"])
        self.assertEqual(out["delivery_status"], "complete")

    def test_a_failure_after_the_record_was_written_resumes_without_rewriting_it(self):
        head = self.delivery_state()
        reviews = Path(os.environ["GSTACK_PEER_REVIEW_DIR"])
        f = reviews / "rev-1" / "release-o-r-42.json"
        f.write_text(json.dumps({"head": head, "merge_commit": "m" * 40, "outcome": "agent_merge_autonomous"}))
        before = f.read_bytes()
        put, calls = self.writer()
        for _ in range(2):
            out = gr.resume("g1", self.github(head, merged=True), "o/r", put=put)
            self.assertEqual(out["delivery_status"], "complete")
        self.assertEqual((f.read_bytes(), calls), (before, []))
        f.write_text(json.dumps({"head": "o" * 40, "merge_commit": "m" * 40}))   # a record of another head is refused
        st = gr.load("g1"); st["delivery"]["changes"]["implementation"]["release_record"] = None; gr.save(st)
        out = gr.resume("g1", self.github(head, merged=True), "o/r", put=put)
        self.assertIn("not this change's merge", out["stopped_by"])
        self.assertNotEqual(out["delivery_status"], "complete")

    def test_a_missing_release_companion_prevents_complete(self):
        head = self.delivery_state()
        st = gr.load("g1"); dl = st["delivery"]
        dl["changes"]["marketplace"] = dict(dl["changes"]["implementation"], pr=43, review_id="rev-2", merge=None, release_record=None)
        dl["release_companion"] = "marketplace"; gr.save(st)
        reviews = Path(os.environ["GSTACK_PEER_REVIEW_DIR"])
        (reviews / "rev-1" / "release-o-r-42.json").write_text(json.dumps({"head": head, "merge_commit": "m" * 40}))
        put, calls = self.writer()
        out = gr.resume("g1", self.github(head, merged=True), "o/r", put=put)   # #43 isn't observed
        self.assertNotEqual(out["delivery_status"], "complete")
        self.assertIn("marketplace: not merged", out["missing"])
        self.assertEqual(calls, [])



class Repairs(ResumeExecutes):
    """Goal gstack-delivery-completion: regression cases for review 20261027-101630-b321160-f16vgusw
    F3 (a stopped or held run advances nothing) and the persisted merge request (never resent by a
    fresh process). Written before the fix."""

    def snapshot(self):
        return (gr.run_dir("g1") / "state.json").read_bytes()

    def test_r3_a_stopped_or_held_run_records_releases_merges_and_syncs_nothing(self):
        head = self.delivery_state()
        orig = gr.act; gr.act = lambda *a, **k: {"allowed": "merge"}; self.addCleanup(setattr, gr, "act", orig)
        for setup in ("stopped", "held"):
            st = gr.load("g1")
            if setup == "stopped":
                st["outcome"], st["reason"] = "stopped", "rounds_exhausted"
            else:
                st["outcome"] = None
                st.setdefault("messages", []).append({"n": 99, "kind": "escalation", "trigger": "dorian_call", "item": None,
                                                      "text": "held", "at": "t", "waits": True, "status": "open", "words": None, "delivered": True})
            gr.save(st)
            before = self.snapshot()
            put, calls = self.writer()
            for merged in (False, True):
                out = gr.resume("g1", self.github(head, merged=merged), "o/r", put=put)
                self.assertEqual(out["executed"], []); self.assertIn("refused", out)
            self.assertEqual(calls, [])
            self.assertEqual(self.snapshot(), before, f"a {setup} run's delivery state is preserved")
            st = gr.load("g1"); st["outcome"] = None; st["messages"] = [m for m in st.get("messages", []) if m.get("n") != 99]; gr.save(st)

    def test_r4_a_merge_request_persisted_by_an_earlier_process_is_never_sent_again(self):
        head = self.delivery_state()
        orig = gr.act; gr.act = lambda *a, **k: {"allowed": "merge"}; self.addCleanup(setattr, gr, "act", orig)
        st = gr.load("g1")
        st["delivery"]["changes"]["implementation"]["merge_requested"] = {"at": "2026-10-27T00:00:00Z", "head": head, "pr": 42}
        gr.save(st)                                                       # the earlier process died after asking
        put, calls = self.writer()
        out = gr.resume("g1", self.github(head), "o/r", put=put)          # GitHub still shows it unmerged
        self.assertEqual(calls, [])
        self.assertIn("earlier", out["stopped_by"] or out["next"].get("blocked", "") or out["next"].get("pending", ""))
        reviews = Path(os.environ["GSTACK_PEER_REVIEW_DIR"])
        (reviews / "rev-1" / "release-o-r-42.json").write_text(json.dumps({"head": head, "merge_commit": "m" * 40}))
        out = gr.resume("g1", self.github(head, merged=True), "o/r", put=put)   # it had landed after all
        self.assertEqual(calls, []); self.assertEqual(out["delivery_status"], "complete")



class RepairsRound2(ResumeExecutes):
    """Review 20261027-124210-98b5ed8-o897p6eo F2 and F3. Written before the fix."""

    def test_f2_a_pending_decision_never_ends_the_run_complete(self):
        head = self.delivery_state()
        st = gr.load("g1"); ch = st["delivery"]["changes"]["implementation"]
        ch["merge"] = {"verified": True, "head": head, "sha": "m" * 40}
        ch["release_record"] = {"verified": True, "path": "/r"}
        st["final_pr"] = 42; gr.save(st)
        base_get = self.github(head, merged=True)
        lost = lambda path: None if path.endswith("/pulls/42") else base_get(path)   # the PR can't be read now
        put, calls = self.writer()
        out = gr.resume("g1", lost, "o/r", put=put)
        self.assertNotEqual(out["delivery_status"], "complete")
        self.assertIn("pending", out["next"])
        self.assertIsNone(gr.load("g1")["outcome"], "a pending decision leaves the run open")

    def test_f3_an_out_of_lane_or_foreign_release_record_is_not_a_verified_release(self):
        head = self.delivery_state()
        reviews = Path(os.environ["GSTACK_PEER_REVIEW_DIR"])
        f = reviews / "rev-1" / "release-o-r-42.json"
        for rec in ({"review_id": "rev-1", "repo": "o/r", "head": head, "merge_commit": "m" * 40, "outcome": "agent_merge_out_of_lane"},
                    {"review_id": "another", "repo": "o/r", "head": head, "merge_commit": "m" * 40, "outcome": "agent_merge_autonomous"},
                    {"review_id": "rev-1", "repo": "o/other", "head": head, "merge_commit": "m" * 40, "outcome": "agent_merge_autonomous"}):
            f.write_text(json.dumps(rec)); before = f.read_bytes()
            st = gr.load("g1"); st["delivery"]["changes"]["implementation"]["release_record"] = None; gr.save(st)
            put, calls = self.writer()
            out = gr.resume("g1", self.github(head, merged=True), "o/r", put=put)
            self.assertFalse((gr.load("g1")["delivery"]["changes"]["implementation"].get("release_record") or {}).get("verified"))
            self.assertNotEqual(out["delivery_status"], "complete"); self.assertTrue(out["stopped_by"])
            self.assertEqual(f.read_bytes(), before, "the record is kept as it is")
        f.write_text(json.dumps({"review_id": "rev-1", "repo": "o/r", "head": head, "merge_commit": "m" * 40, "outcome": "agent_merge_autonomous"}))
        st = gr.load("g1"); st["delivery"]["changes"]["implementation"]["release_record"] = None; gr.save(st)
        self.assertEqual(gr.resume("g1", self.github(head, merged=True), "o/r", put=self.writer()[0])["delivery_status"], "complete")


if __name__ == "__main__":
    unittest.main()
