"""GO-005 criteria 4 to 6: the goal ledger, and what a goal run's pushes, pull requests and merges set off."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_guard as gguard  # noqa: E402
import goal_run as gr  # noqa: E402
import test_goal_run as tgr  # noqa: E402  its runner fixture

DEPLOY = "jobs:\n  d:\n    runs-on: ubuntu-latest\n    environment: production\n    steps:\n      - run: ./deploy\n"
GREEN = {"tests": "success", "goal-envelope": "success", "goal-tests": "success"}
CLEAN = {"outcome": "fixes_verified", "coverage_checked": True, "coverage_status": "covered", "heads": [["a" * 40], ["b" * 40]]}


class Triggers(tgr.RunnerFixture):
    def refused_start(self, workflow, envs=("goal-holdout",)):
        if workflow:
            self.commit("wf", {".github/workflows/deploy.yml": workflow})
        with self.assertRaises(gr.Refused) as e:
            self.start(environments=lambda: list(envs))
        self.assertEqual(self.branches, [])                       # nothing was pushed
        return str(e.exception)

    def named_in_stops(self):
        self.commit("brief", {"goals/g1/GOAL.md": tgr.BRIEF + "\n## Stop conditions\n- deploy.yml and production deploy "
                                                              "on the merge into main; that merge is Dorian's call\n"})
        self.tree = self.git("rev-parse", "main:goals/g1")

    def test_a_check_given_a_deploy_environment_isnt_a_check(self):
        self.assertIn("tests.yml runs on push with environment production",
                      self._tests_yml())

    def _tests_yml(self):
        self.commit("wf", {".github/workflows/tests.yml": "on: push\n" + DEPLOY})
        with self.assertRaises(gr.Refused) as e:
            self.start()
        return str(e.exception)

    def test_a_check_named_workflow_that_deploys_without_an_environment_isnt_a_check(self):
        self.commit("wf", {".github/workflows/tests.yml": "on: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n"
                                                          "    steps:\n      - run: python3 run_all_tests.py\n      - run: ./deploy\n"})
        with self.assertRaises(gr.Refused) as e:
            self.start()
        self.assertIn("tests.yml runs on push and its content isn't the check pinned", str(e.exception))

    def test_start_reads_current_main_not_a_stale_copy(self):
        bare = Path(self.tmp.name, "remote.git")
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(bare)], check=True)
        self.git("remote", "add", "origin", str(bare)); self.git("fetch", "-q", "origin")
        self.git("switch", "-q", "-c", "elsewhere")
        self.commit("deploy on main", {".github/workflows/deploy.yml": "on: push\n" + DEPLOY})
        stale = self.git("rev-parse", "origin/main")
        self.git("push", "-q", "origin", "elsewhere:main")
        self.git("update-ref", "refs/remotes/origin/main", stale)       # main moved; origin/main here didn't
        self.git("switch", "-q", "main"); self.git("branch", "-q", "-D", "elsewhere")
        with self.assertRaisesRegex(gr.Refused, "deploy.yml"):
            gr.start(self.repo, "g1", 7, "claude/claude-opus", self.verify(), {"contents": "write"}, self.create,
                     base="origin/main", environments=self.envs)
        self.assertEqual(self.branches, [])

    def test_a_deploy_on_a_push_to_any_branch_stops_the_start(self):
        msg = self.refused_start("on: push\n" + DEPLOY)
        self.assertIn(".github/workflows/deploy.yml runs on push with environment production", msg)

    def test_a_deploy_on_a_pull_request_stops_the_start(self):
        self.assertIn("runs on pull_request", self.refused_start("on:\n  pull_request:\n" + DEPLOY))
        self.assertIn("runs on pull_request_target", self.refused_start("on: [pull_request_target]\n" + DEPLOY))

    def test_a_deployment_environment_stops_the_start(self):
        self.assertIn("deployment environment production", self.refused_start(None, envs=("goal-holdout", "production")))

    def test_a_deploy_on_main_only_starts_when_the_brief_names_it(self):
        main_only = "on:\n  push:\n    branches:\n      - main\n" + DEPLOY
        self.assertIn("deploy.yml", self.refused_start(main_only))
        self.named_in_stops()
        self.start(environments=lambda: ["goal-holdout", "production"])
        self.assertEqual(self.branches[0][0], "goal/g1")

    def test_a_named_deploy_on_every_push_still_stops_the_start(self):
        self.named_in_stops()
        self.assertIn("deploy.yml", self.refused_start("on: push\n" + DEPLOY))

    def test_branches_outside_the_on_block_dont_make_a_deploy_main_only(self):
        self.named_in_stops()
        for wf in ("# branches: [main]\non: push\n" + DEPLOY,
                   "on:\n  push:\n  # branches: [main]\n" + DEPLOY,
                   "on: push\njobs:\n  d:\n    strategy:\n      matrix:\n        branches: [main]\n    environment: production\n",
                   "on:\n  push:\n    branches: [main, dev]\n" + DEPLOY,
                   "on:\n  push:\n    branches: ['**']\n" + DEPLOY):
            with self.subTest(wf=wf[:40]):
                self.assertIn("deploy.yml", self.refused_start(wf))

    def test_each_main_only_shape_starts_when_named(self):
        for on in ("on:\n  push:\n    branches: [main]  # deploys the merge\n",
                   "on:\n  push:\n    branches:\n      - 'main'\n"):
            with self.subTest(on=on):
                self.assertTrue(gguard.main_only(on + DEPLOY, {"push"}))

    def test_a_deploy_added_after_the_start_stops_the_next_push(self):
        self.start()
        self.assertEqual(gr.act(self.repo, "g1", "vcs.push", "build/GX-1-a", self.envs, base="main")["allowed"], "vcs.push")
        self.commit("wf", {".github/workflows/deploy.yml": "on: push\n" + DEPLOY})
        with self.assertRaises(gr.Refused):
            gr.act(self.repo, "g1", "vcs.push", "build/GX-1-a", self.envs, base="main")
        self.assertEqual(gr.load("g1")["outcome"], "stopped")
        self.assertIn("changed since the run started", gr.load("g1")["reason"])

    def test_a_new_deployment_environment_stops_the_next_pull_request(self):
        self.start()
        with self.assertRaises(gr.Refused):
            gr.act(self.repo, "g1", "pr.open", "goal/g1<-build/GX-1-a", lambda: ["goal-holdout", "staging"], base="main")
        self.assertEqual(gr.load("g1")["outcome"], "stopped")


class Pins(unittest.TestCase):
    def test_every_pinned_check_is_the_workflow_in_this_repository(self):
        import hashlib
        root = Path(__file__).resolve().parents[3] / ".github" / "workflows"
        for name, pin in gguard.CHECKS.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), pin,
                                 f"{name} changed: re-review it as a check and move its pin in goal_guard.CHECKS")


class Ledger(tgr.RunnerFixture):
    def act(self, klass, resource, **kw):
        return gr.act(self.repo, "g1", klass, resource, self.envs, base="main", **kw)

    def test_an_item_merge_into_the_goal_branch_after_a_clean_review_is_allowed_and_into_main_refused(self):
        self.start()
        self.assertEqual(self.act("merge", "goal/g1", head="b" * 40, review=CLEAN, checks=GREEN)["by"], "DR-113")
        with self.assertRaisesRegex(gr.Refused, "not main"):
            self.act("merge", "main", head="b" * 40, review=CLEAN, checks=GREEN)
        for review, why in ((dict(CLEAN, outcome="rounds_exhausted"), "not clean"),
                            (dict(CLEAN, coverage_status="uncovered"), "coverage"),
                            (dict(CLEAN, coverage_overridden=True), "coverage"),
                            (CLEAN, "last head")):
            with self.subTest(why=why), self.assertRaisesRegex(gr.Refused, why):
                self.act("merge", "goal/g1", head=("a" * 40 if why == "last head" else "b" * 40), review=review, checks=GREEN)

    def test_a_clean_review_alone_doesnt_merge_an_item(self):
        self.start()
        for checks, why in (({**GREEN, "goal-tests": "failure"}, "goal-tests at bbbbbbbbbbbb is failure"),
                            ({k: v for k, v in GREEN.items() if k != "goal-envelope"}, "goal-envelope at bbbbbbbbbbbb is missing"),
                            ({**GREEN, "tests": "in_progress"}, "tests at bbbbbbbbbbbb is in_progress")):
            with self.subTest(why=why), self.assertRaisesRegex(gr.Refused, why):
                self.act("merge", "goal/g1", head="b" * 40, review=CLEAN, checks=checks)
        with self.assertRaisesRegex(gr.Refused, "checks at that head"):
            self.act("merge", "goal/g1", head="b" * 40, review=CLEAN)

    def test_the_newest_check_run_of_each_name_counts(self):
        runs = [{"id": 1, "name": "goal-tests", "status": "completed", "conclusion": "failure"},
                {"id": 2, "name": "goal-tests", "status": "completed", "conclusion": "success"},
                {"id": 3, "name": "tests", "status": "queued", "conclusion": None}]
        self.assertEqual(gguard.latest_checks(runs), {"goal-tests": "success", "tests": "queued"})

    def test_the_final_pull_request_into_main_is_granted_once(self):
        self.start()
        self.act("pr.open", "goal/g1<-build/GX-1-a")
        self.act("pr.open", "goal/g1<-build/GX-2-b")             # into the goal branch, as often as it takes
        self.act("pr.open", "main<-goal/g1")
        with self.assertRaisesRegex(gr.Refused, "Dorian's call"):
            self.act("pr.open", "main<-goal/g1")
        with self.assertRaisesRegex(gr.Refused, "Dorian's call"):
            self.act("pr.open", "main<-build/GX-1-a")

    def test_the_ledger_never_grants_merge_or_a_push_to_main(self):
        self.start()
        rows = gguard.gov._ledger(gr.run_dir("g1") / "ledger.jsonl")
        self.assertNotIn("merge", {r["class"] for r in rows})
        with self.assertRaisesRegex(gr.Refused, "never granted"):
            gguard.granted(gr.run_dir("g1") / "ledger.jsonl", "merge", "goal/g1", [])
        for branch in ("main", "goal/other"):
            with self.subTest(branch=branch), self.assertRaisesRegex(gr.Refused, "Dorian's call"):
                self.act("vcs.push", branch)

    def test_an_existing_host_that_isnt_a_reviewers_is_refused_though_the_change_is_in_envelope(self):
        self.start()                                              # builder claude/claude-opus
        sha = self.item("done = True\nsafe = True\nURL = 'https://api.known.com/x'\n")
        self.commit("host on main", {"src_known.txt": "https://api.known.com/x\n"})
        call = gr.open_call(self.repo, "g1", "Which?", ["a", "b"], "claude/opus", "gpt/gpt-6", sha, base="main")
        self.assertEqual(call["type"], "in_envelope_code")
        with self.assertRaisesRegex(gr.Refused, "api.known.com"):
            self.act("net.connect", "https://api.known.com/x")
        self.assertEqual(self.act("net.connect", "openrouter.ai")["allowed"], "net.connect")   # a reviewer's host
        with self.assertRaisesRegex(gr.Refused, "api.anthropic.com"):
            self.act("net.connect", "api.anthropic.com")                                       # the builder's own vendor

    def test_reviewers_and_their_models_are_granted_and_the_builders_family_isnt(self):
        self.start()
        self.act("review.send_code", "codex")
        self.act("external.model_call", "google/gemini-3.1-pro-preview")
        for klass, res in (("review.send_code", "openrouter-claude"), ("external.model_call", "anthropic/claude-opus-5")):
            with self.subTest(res=res), self.assertRaisesRegex(gr.Refused, "Dorian's call"):
                self.act(klass, res)

    def test_an_action_after_the_run_ended_is_refused(self):
        self.start()
        gr.stop("g1", "test")
        with self.assertRaisesRegex(gr.Refused, "already ended"):
            self.act("vcs.push", "build/GX-1-a")


if __name__ == "__main__":
    unittest.main()
