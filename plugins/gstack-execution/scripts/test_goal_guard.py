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
PR = {"number": 31, "head": "b" * 40, "base_ref": "goal/g1", "base": "c" * 40}
BOUND = f"pr=31;base_ref=goal/g1;base={'c' * 40}"
GREEN = {"tests": ("success", None), "goal-envelope": ("success", BOUND), "goal-tests": ("success", BOUND)}
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
                                                          "    steps:\n      - run: python3 run_all_tests.py\n      - run: ./deploy\n",
                           ".github/goal-checks.json": '{"checks": {"tests.yml": "' + "0" * 64 + '"}}'})
        with self.assertRaises(gr.Refused) as e:
            self.start()
        self.assertIn("tests.yml runs on push and its content isn't the check pinned in .github/goal-checks.json", str(e.exception))

    def test_a_check_pinned_in_the_repositorys_pin_file_is_a_check(self):
        import hashlib
        wf = "on: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: npm test\n"
        self.commit("wf", {".github/workflows/tests.yml": wf,
                           ".github/goal-checks.json": '{"checks": {"tests.yml": "%s"}}' % hashlib.sha256(wf.encode()).hexdigest()})
        problems, _ = gguard.assess(self.repo, "main", tgr.BRIEF, ["goal-holdout"])
        self.assertEqual(problems, [])

    def test_an_unpinned_check_or_a_bad_pin_file_is_a_problem(self):
        wf = "on: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: npm test\n"
        self.commit("wf", {".github/workflows/tests.yml": wf})
        problems, _ = gguard.assess(self.repo, "main", tgr.BRIEF, ["goal-holdout"])
        self.assertTrue(any("isn't one of the repository's checks" in p for p in problems), problems)
        for bad in ("not json", '{"checks": []}', '{"checks": {"goal-holdout.yml": "%s"}}' % ("a" * 64),
                    '{"checks": {"tests.yml": "ABC"}}', '{"checks": {"../x.yml": "%s"}}' % ("a" * 64),
                    '{"checks": {"ci.yml": "%s"}}' % ("a" * 64)):
            self.commit("pins", {".github/goal-checks.json": bad})
            problems, _ = gguard.assess(self.repo, "main", tgr.BRIEF, ["goal-holdout"])
            self.assertTrue(any(".github/goal-checks.json" in p for p in problems), (bad, problems))

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

    def test_a_pin_file_broken_after_the_start_stops_the_next_push(self):
        self.start()
        self.commit("pins", {".github/goal-checks.json": "not json"})
        with self.assertRaises(gr.Refused):
            gr.act(self.repo, "g1", "vcs.push", "build/GX-1-a", self.envs, base="main")
        self.assertEqual(gr.load("g1")["outcome"], "stopped")

    def test_a_new_deployment_environment_stops_the_next_pull_request(self):
        self.start()
        with self.assertRaises(gr.Refused):
            gr.act(self.repo, "g1", "pr.open", "goal/g1<-build/GX-1-a", lambda: ["goal-holdout", "staging"], base="main")
        self.assertEqual(gr.load("g1")["outcome"], "stopped")


class Pins(unittest.TestCase):
    def test_every_pinned_check_is_the_workflow_in_this_repository(self):
        import hashlib, json
        gh = Path(__file__).resolve().parents[3] / ".github"
        own = json.loads((gh / "goal-checks.json").read_text())["checks"]
        self.assertIn("tests.yml", own)
        for name, pin in {**own, **gguard.GOAL_WORKFLOWS}.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((gh / "workflows" / name).read_bytes()).hexdigest(), pin,
                                 f"{name} changed: re-review it as a check and move its pin "
                                 f"({'goal_guard.GOAL_WORKFLOWS' if name in gguard.GOAL_WORKFLOWS else '.github/goal-checks.json'})")


class Ledger(tgr.RunnerFixture):
    def act(self, klass, resource, **kw):
        """Each attempt comes after Dorian has acknowledged the escalation the last refusal raised
        (GO-006.2 holds the run until he does; test_goal_digest covers the hold itself)."""
        for m in gr.held(gr.load("g1")):
            gr.acknowledge("g1", m["n"], "seen")
        return gr.act(self.repo, "g1", klass, resource, self.envs, base="main", **kw)

    def test_an_item_merge_into_the_goal_branch_after_a_clean_review_is_allowed_and_into_main_refused(self):
        self.start()
        self.assertEqual(self.act("merge", "goal/g1", head="b" * 40, review=CLEAN, checks=GREEN, pr=PR)["by"], "DR-113")
        with self.assertRaisesRegex(gr.Refused, "not main"):
            self.act("merge", "main", head="b" * 40, review=CLEAN, checks=GREEN, pr=PR)
        for review, why in ((dict(CLEAN, outcome="rounds_exhausted"), "not clean"),
                            (dict(CLEAN, coverage_status="uncovered"), "coverage"),
                            (dict(CLEAN, coverage_overridden=True), "coverage"),
                            (CLEAN, "last head")):
            with self.subTest(why=why), self.assertRaisesRegex(gr.Refused, why):
                self.act("merge", "goal/g1", head=("a" * 40 if why == "last head" else "b" * 40), review=review, checks=GREEN, pr=PR)

    def test_a_clean_review_alone_doesnt_merge_an_item(self):
        self.start()
        other = f"pr=30;base_ref=goal/g1;base={'c' * 40}"
        for checks, pr, why in (
                ({**GREEN, "goal-tests": ("failure", BOUND)}, PR, "goal-tests at bbbbbbbbbbbb is failure"),
                ({k: v for k, v in GREEN.items() if k != "goal-envelope"}, PR, "goal-envelope at bbbbbbbbbbbb is missing"),
                ({**GREEN, "tests": ("in_progress", None)}, PR, "tests at bbbbbbbbbbbb is in_progress"),
                ({**GREEN, "goal-tests": ("success", "pr=31;base_ref=main;base=" + "c" * 40)}, PR, "reached for pr=31;base_ref=main"),
                ({**GREEN, "goal-envelope": ("success", None)}, PR, "reached for nothing named"),       # a run from before provenance
                ({**GREEN, "goal-tests": ("success", other)}, PR, "reached for pr=30"),               # another pull request's pass
                (GREEN, {**PR, "base": "d" * 40}, "reached for pr=31;base_ref=goal/g1;base=cccc"),      # the base moved since
                (GREEN, {**PR, "base_ref": "main"}, "into main, not"),                                 # retargeted
                (GREEN, {**PR, "head": "e" * 40}, "PR #31 is at eeeeeeeeeeee")):
            with self.subTest(why=why), self.assertRaisesRegex(gr.Refused, why):
                self.act("merge", "goal/g1", head="b" * 40, review=CLEAN, checks=checks, pr=pr)
        with self.assertRaisesRegex(gr.Refused, "checks at that head"):
            self.act("merge", "goal/g1", head="b" * 40, review=CLEAN)

    def test_the_newest_check_run_of_each_name_counts(self):
        runs = [{"id": 1, "name": "goal-tests", "status": "completed", "conclusion": "failure"},
                {"id": 2, "name": "goal-tests", "status": "completed", "conclusion": "success"},
                {"id": 3, "name": "tests", "status": "queued", "conclusion": None}]
        self.assertEqual(gguard.latest_checks(runs), {"goal-tests": ("success", None), "tests": ("queued", None)})

    def test_a_sync_merges_without_a_review_only_when_it_changes_nothing_against_main(self):
        self.start()
        self.git("switch", "-q", "-c", "sync", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "Sync main")
        empty = self.git("rev-parse", "HEAD")
        changed = self.commit("sneak", {"helper.py": "x = 1\n"})
        self.git("switch", "-q", "main")
        sync_pr = dict(PR, head=empty)
        self.assertEqual(self.act("merge", "goal/g1", head=empty, checks=GREEN, pr=sync_pr, sync=True)["by"], "GO-004.1 sync")
        with self.assertRaisesRegex(gr.Refused, "one empty commit on main's tip"):
            self.act("merge", "goal/g1", head=changed, checks=GREEN, pr=dict(PR, head=changed), sync=True)
        with self.assertRaisesRegex(gr.Refused, "changes helper.py against main"):
            gguard.sync_allowed("goal/g1", "goal/g1", empty, GREEN, sync_pr, ["helper.py"])
        with self.assertRaisesRegex(gr.Refused, "goal-envelope at .* is missing"):
            self.act("merge", "goal/g1", head=empty, checks={"tests": ("success", None)}, pr=sync_pr, sync=True)
        with self.assertRaisesRegex(gr.Refused, "a sync merges into goal/g1, not main"):
            self.act("merge", "main", head=empty, checks=GREEN, pr=sync_pr, sync=True)
        self.git("switch", "-q", "-c", "detour", "main")             # a change and its revert: no diff, unreviewed history
        self.commit("change", {"helper.py": "x = 2\n"}); self.git("revert", "--no-edit", "HEAD")
        self.git("commit", "-q", "--allow-empty", "-m", "Sync main")
        detour = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "-c", "one-change", "main")         # one commit on main's tip, but not empty
        self.commit("change", {"helper.py": "x = 3\n"})
        one_change = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "main")
        with self.assertRaisesRegex(gr.Refused, "one empty commit on main's tip"):
            self.act("merge", "goal/g1", head=one_change, checks=GREEN, pr=dict(PR, head=one_change), sync=True)
        self.item("done = False\nsafe = True\n# goal work\n")      # the goal branch moves past main's tip
        self.git("switch", "-q", "-c", "off-goal", "goal/g1")
        self.git("commit", "-q", "--allow-empty", "-m", "Sync main")
        off_goal = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "main")
        for head in (detour, off_goal):
            with self.subTest(head=head), self.assertRaisesRegex(gr.Refused, "one empty commit on main's tip"):
                self.act("merge", "goal/g1", head=head, checks=GREEN, pr=dict(PR, head=head), sync=True)

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
