"""GO-003.5: the goal checks' decisions, the sandbox they run candidate code in, and the workflows
that call them. The container test runs wherever Docker runs; CI must have it (a CI run without
Docker fails rather than skips), and a laptop without a daemon reports the test as skipped."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import goal_checks as gc  # noqa: E402

CO = ("/.github/ @dorianatmoxywolf\n/goals/ @dorianatmoxywolf\n/goal-runs/ @dorianatmoxywolf\n"
      "/plugins/gstack-execution/scripts/goal_envelope.py @dorianatmoxywolf\n")
BRIEF = "## Allowed paths\n- `src/**`\n\n## Goal tests\n- `tests/test_g.py::G.test_done` (outcome)\n- `tests/test_g.py::G.test_safe` (invariant)\n"


def pr(base="goal/g1", head="build/item-1", number=5, head_sha="a" * 40, base_sha="b" * 40):
    return {"number": number, "base": {"ref": base, "sha": base_sha}, "head": {"ref": head, "sha": head_sha}}


NODE_LOCK = """{
  "name": "cand",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {"name": "cand", "version": "1.0.0", "dependencies": {"ms": "2.1.3"}},
    "node_modules/ms": {
      "version": "2.1.3",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
      "integrity": "sha512-6FlzubTLZG3J2a/NVCAleEhjzq5oxgHyaCU9yYXvcLsvoVaHJq/s5xXI6/XXP6tz7R9xAOtHnSO/tXtF3WRTlA==",
      "license": "MIT"
    }
  }
}
"""

class Decisions(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(gc.classify(pr()), ("item", "g1"))
        self.assertEqual(gc.classify(pr(base="main", head="goal/g1")), ("goal", "g1"))
        self.assertEqual(gc.classify(pr(base="main", head="build/x")), ("none", None))
        self.assertEqual(gc.classify(pr(base="release", head="goal/g1")), ("none", None))

    def fake_run(self, results, rc=0):
        def run(cmd, **kw):
            self.cmd = cmd
            return subprocess.CompletedProcess(cmd, rc, json.dumps(results) + "\n", "")
        return run

    def goal_repo(self):
        d = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, d)
        (d / "goals" / "g1").mkdir(parents=True); (d / "goals" / "g1" / "GOAL.md").write_text(BRIEF)
        return d

    def test_an_item_needs_its_invariants_and_the_goal_pr_needs_every_test(self):
        res = {"tests/test_g.py::G.test_done": {"kind": "outcome", "result": "failed"},
               "tests/test_g.py::G.test_safe": {"kind": "invariant", "result": "passed"}}
        repo = self.goal_repo()
        self.assertEqual(gc.tests(pr(), repo, "m" * 40, "/c", self.fake_run(res))["conclusion"], "success")
        v = gc.tests(pr(base="main", head="goal/g1"), repo, "m" * 40, "/c", self.fake_run(res))
        self.assertEqual(v["conclusion"], "failure")
        self.assertIn("every goal test must pass", v["summary"])
        res["tests/test_g.py::G.test_safe"]["result"] = "not_run"
        self.assertEqual(gc.tests(pr(), repo, "m" * 40, "/c", self.fake_run(res))["conclusion"], "failure")

    def test_tests_that_report_nothing_or_no_goal_fail(self):
        repo = self.goal_repo()
        self.assertEqual(gc.tests(pr(), repo, "m" * 40, "/c", self.fake_run({}))["title"], "examined no goal tests")
        bad = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "Traceback")
        self.assertEqual(gc.tests(pr(), repo, "m" * 40, "/c", bad)["title"], "the goal tests did not report")
        self.assertIn("not on main", gc.tests(pr(base="goal/g9"), repo, "m" * 40, "/c", bad)["title"])

    def test_a_pull_request_that_isnt_a_goals_passes_both_checks(self):
        p = pr(base="main", head="build/x")
        self.assertEqual(gc.tests(p, "/nowhere", "m", "/c")["conclusion"], "success")
        self.assertEqual(gc.envelope(p, "/nowhere", "m", "none")["conclusion"], "success")

    def test_the_sandbox_has_no_network_no_environment_and_reads_only(self):
        cmd = gc.sandbox_cmd("/m", "/c", "g1")
        joined = " ".join(cmd)
        for flag in ("--network none", "--read-only", "--cap-drop ALL", "no-new-privileges", "--user 65534:65534",
                     "--tmpfs /tmp:exec"):
            self.assertIn(flag, joined)
        self.assertIn("/m:/main:ro", joined); self.assertIn("/c:/candidate:ro", joined)
        envs = [cmd[i + 1] for i, a in enumerate(cmd) if a in ("-e", "--env")]
        self.assertEqual(envs, ["HOME=/tmp"])
        self.assertNotIn("--env-file", cmd)

    def test_publish_posts_on_the_head_or_nothing_when_it_moved(self):
        v = {"pr": 5, "head": "a" * 40, "base": "b" * 40, "base_ref": "goal/g1", "conclusion": "success", "title": "t", "summary": "s"}
        calls = []

        def call(m, p, d=None, live=pr()):
            calls.append((m, p, d))
            return live
        self.assertIn("published goal-tests: success", gc.publish("goal-tests", v, "o/r", call))
        self.assertEqual(calls[-1][0:2], ("POST", "repos/o/r/check-runs"))
        self.assertEqual(calls[-1][2]["external_id"], f"pr={v['pr']};base_ref={v['base_ref']};base={v['base']}")
        self.assertEqual((calls[-1][2]["name"], calls[-1][2]["head_sha"]), ("goal-tests", "a" * 40))
        for moved in (pr(head_sha="c" * 40), pr(base_sha="d" * 40), pr(base="main")):   # a retarget at the same SHA too
            calls.clear()
            self.assertIn("published nothing", gc.publish("goal-tests", v, "o/r", lambda m, p, d=None, live=moved: calls.append(m) or live))
            self.assertEqual(calls, ["GET"])


class Holdout(unittest.TestCase):  # GO-003.6
    SRC = "import unittest\n\n\nclass H(unittest.TestCase):\n    def test_h(self):\n        self.assertTrue(True)\n"

    def repo(self):
        d = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, d)
        (d / "goals" / "g1").mkdir(parents=True)
        (d / "goals" / "g1" / "holdout.sha256").write_text(__import__("hashlib").sha256(self.SRC.encode()).hexdigest() + "\n")
        return d

    def run_with(self, result, detail=None):
        def run(cmd, **kw):
            self.cmd, self.kw = cmd, kw
            out = {"result": result} if detail is None else {"result": result, "detail": detail}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(out) + "\n", "")
        return run

    def test_the_holdout_runs_only_on_the_goal_pull_request_into_main(self):
        self.assertEqual(gc.holdout(pr(), "/r", "m", "/c", "")["conclusion"], "success")              # an item
        self.assertEqual(gc.holdout(pr(base="main", head="build/x"), "/r", "m", "/c", "")["conclusion"], "success")

    def test_a_missing_or_wrong_holdout_runs_nothing(self):
        g, repo = pr(base="main", head="goal/g1"), self.repo()
        never = lambda *a, **k: self.fail("ran a holdout it should have refused")
        self.assertIn("no GOAL_G1_HOLDOUT secret", gc.holdout(g, repo, "m", "/c", "", never)["title"])
        self.assertEqual(gc.holdout(g, repo, "m", "/c", self.SRC + "# changed\n", never)["title"],
                         "the holdout doesn't match holdout.sha256")

    def test_the_holdout_reaches_the_sandbox_on_stdin_only(self):
        g, repo = pr(base="main", head="goal/g1"), self.repo()
        v = gc.holdout(g, repo, "m", "/c", self.SRC, self.run_with("passed"))
        self.assertEqual(v["conclusion"], "success")
        self.assertEqual(self.kw["input"], self.SRC)
        self.assertIn("-i", self.cmd)
        self.assertNotIn(self.SRC, " ".join(self.cmd))
        self.assertEqual([self.cmd[i + 1] for i, a in enumerate(self.cmd) if a == "-e"], ["HOME=/tmp"])
        self.assertIn("--network none", " ".join(self.cmd))

    def test_a_failing_holdout_is_a_possible_reward_hack(self):
        g, repo = pr(base="main", head="goal/g1"), self.repo()
        for result in ("failed", "not_run"):
            v = gc.holdout(g, repo, "m", "/c", self.SRC, self.run_with(result))
            self.assertEqual(v["conclusion"], "failure")
            self.assertIn("possible reward hack", v["title"])
        v = gc.holdout(g, repo, "m", "/c", self.SRC, self.run_with("failed", "FAIL: test_empty (goal_holdout.H.test_empty)\nAssertionError: 2 != 0"))
        self.assertIn("FAIL: test_empty", v["summary"])                  # GO-003.6: the diagnosis reaches the check
        self.assertIn("this holdout is spent", v["summary"])

    def test_the_sealed_harness_runs_holdout_source_that_is_never_a_file(self):
        import goal_brief as gb
        cand = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, cand)
        # the candidate hunts for the holdout's own words in everything it inherits: environment, stdin, home
        (cand / "goalmod.py").write_text(
            "import os, sys\nmark = 'holdout-' + 'canary-7f3a'\nfound = [k for k, v in os.environ.items() if mark in v]\n"
            "found += ['stdin'] if mark in sys.stdin.read() else []\n"
            "for d, _, fs in os.walk(os.path.expanduser('~')):\n"
            "    found += [f for f in fs if mark in open(os.path.join(d, f), errors='replace').read()]\nprint(found)\n")
        src = ("# holdout-canary-7f3a\nimport os, subprocess, sys, unittest\n\n\nclass H(unittest.TestCase):\n    def test_sees_nothing(self):\n"
               "        r = subprocess.run([sys.executable, '-c', 'import goalmod'], cwd=os.environ['GOAL_CANDIDATE'],"
               " stdin=None, capture_output=True, text=True)\n        self.assertEqual(r.stdout.strip(), '[]', r.stdout + r.stderr)\n")
        self.assertEqual(gb.run_holdout(cand, src), "passed")
        self.assertEqual(gb.run_holdout(cand, src.replace("'[]'", "'nope'")), "failed")
        self.assertEqual(gb.run_holdout(cand, "import unittest\n"), "not_run")                 # no tests is not a pass
        result, why = gb.run_holdout(cand, src.replace("'[]'", "'nope'"), detail=True)        # the diagnosis names what failed
        self.assertEqual(result, "failed")
        self.assertIn("FAIL: test_sees_nothing", why)
        self.assertIn("AssertionError", why)
        self.assertNotIn("holdout-canary", why)                                               # and never carries the source
        self.assertEqual(gb.run_holdout(cand, src, detail=True), ("passed", ""))
        many = ("import subprocess, sys, unittest\n\n\nclass M(unittest.TestCase):\n"          # review F1, F2
                "    def test_long(self):\n        self.fail('x' * 4000)\n"
                "    def test_plain(self):\n        raise Exception('diagnosis')\n"
                "    def test_called(self):\n        subprocess.run([sys.executable, '-c', 'import sys; sys.exit(3)'], check=True)\n")
        result, why = gb.run_holdout(cand, many, detail=True)
        self.assertEqual(result, "failed")
        for name in ("FAIL: test_long", "ERROR: test_plain", "ERROR: test_called"):
            self.assertIn(name, why)
        self.assertIn("AssertionError: xxx", why); self.assertIn("[... cut]", why)
        self.assertIn("Exception: diagnosis", why)
        self.assertIn("subprocess.CalledProcessError", why)


class Envelope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t"); self.git("config", "user.name", "t")
        self.commit({".github/CODEOWNERS": CO, "goals/g1/GOAL.md": BRIEF, "src/a.py": "a\n"})
        self.main = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "-c", "goal/g1")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, files):
        for k, v in files.items():
            (self.repo / k).parent.mkdir(parents=True, exist_ok=True); (self.repo / k).write_text(v)
        self.git("add", "-A"); self.git("commit", "-q", "-m", "c")
        return self.git("rev-parse", "HEAD")

    def test_the_envelope_verdict_names_files_and_counts_commits(self):
        ok = self.commit({"src/b.py": "b\n"})
        v = gc.envelope(pr(), self.repo, self.main, ok)
        self.assertEqual(v["conclusion"], "success")
        self.assertIn("Examined 1 goal-authored commits", v["summary"])
        bad = self.commit({".github/workflows/x.yml": "on: push\n"})
        v = gc.envelope(pr(), self.repo, self.main, bad)
        self.assertEqual(v["conclusion"], "failure")
        self.assertIn(".github/workflows/x.yml, a CODEOWNERS path", v["summary"])

    def test_a_candidate_that_replaces_the_enforcement_still_fails_mains_check(self):  # review F4
        cand = self.commit({"plugins/gstack-execution/scripts/goal_envelope.py": "def check(*a, **k):\n    return [], 1\n",
                            ".github/workflows/goal-envelope.yml": "on: pull_request_target\njobs: {}\n",
                            "src/c.py": "c\n"})
        out = Path(self.tmp.name, "verdict.json")
        prf = Path(self.tmp.name, "pr.json"); prf.write_text(json.dumps(pr()))
        r = subprocess.run([sys.executable, str(HERE / "goal_checks.py"), "envelope", "--pr", str(prf), "--repo", str(self.repo),
                            "--main", self.main, "--candidate", cand, "--out", str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        v = json.loads(out.read_text())
        self.assertEqual(v["conclusion"], "failure")
        self.assertIn("plugins/gstack-execution/scripts/goal_envelope.py, a CODEOWNERS path", v["summary"])
        self.assertIn(".github/workflows/goal-envelope.yml, a CODEOWNERS path", v["summary"])

    def test_a_goal_pull_request_into_main_needs_its_run_record(self):
        goal = pr(base="main", head="goal/g1")
        code = self.commit({"src/b.py": "b\n"})
        v = gc.envelope(goal, self.repo, self.main, code)
        self.assertEqual(v["conclusion"], "failure")
        self.assertIn("doesn't carry its run record goal-runs/g1/RESULT.md", v["summary"])
        recorded = self.commit({"goal-runs/g1/RESULT.md": "record\n"})
        self.assertEqual(gc.envelope(goal, self.repo, self.main, recorded)["conclusion"], "success")
        self.assertEqual(gc.envelope(pr(), self.repo, self.main, code)["conclusion"], "success")   # an item PR doesn't need it

    def test_a_sync_whose_candidate_is_main_passes(self):
        self.assertEqual(gc.envelope(pr(), self.repo, self.main, self.main)["conclusion"], "success")

    def test_an_unreadable_main_fails(self):
        self.assertEqual(gc.envelope(pr(), self.repo, "f" * 40, self.main)["title"], "envelope could not be read")


class Harness(unittest.TestCase):
    def test_candidate_code_that_exits_zero_is_not_a_pass(self):  # review F3, outside the container too
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        goal, cand = t / "goal", t / "cand"
        (goal / "tests").mkdir(parents=True); cand.mkdir()
        (goal / "GOAL.md").write_text("## Goal tests\n- `tests/test_e.py::E.test_x` (invariant)\n")
        (goal / "tests" / "test_e.py").write_text("import os, subprocess, sys, unittest\n\n\nclass E(unittest.TestCase):\n"
                                                  "    def test_x(self):\n        subprocess.run([sys.executable, '-c', 'import goalmod'], cwd=os.environ['GOAL_CANDIDATE'])\n"
                                                  "        self.fail('never')\n")
        (cand / "goalmod.py").write_text("import os\nos.write(1, b'\\ngoal-test-result x passed\\n')\nos._exit(0)\n")
        self.assertEqual(gc.sandbox_run("g", goal, cand), {"tests/test_e.py::E.test_x": {"kind": "invariant", "result": "failed"}})


class Workflows(unittest.TestCase):
    def test_each_goal_workflow_runs_mains_copy_and_keeps_tokens_out_of_candidate_steps(self):
        for name in ("goal-envelope", "goal-tests", "goal-holdout"):
            with self.subTest(name=name):
                text = (ROOT / ".github" / "workflows" / f"{name}.yml").read_text()
                self.assertIn("pull_request_target:", text)
                self.assertIn("types: [opened, synchronize, reopened, edited]", text)      # a retarget is an edit
                self.assertNotIn("github.event.pull_request.base", text)                 # the PR is read at job start
                self.assertIn("\npermissions: {}\n", text)
                self.assertIn("ref: ${{ steps.r.outputs.main }}", text)
                self.assertIn("persist-credentials: false", text)
                self.assertIn(f"publish --name {name} ", text)
                self.assertNotIn("github.event.pull_request.head.ref", text)    # never checked out by name
                steps = text.split("      - ")
                judge = [s for s in steps if s.startswith(("name: Run the goal tests", "name: Judge the envelope", "name: Run the holdout"))]
                self.assertEqual(len(judge), 1)
                self.assertNotIn("token", judge[0])                              # no token where candidate is read or run
                self.assertNotIn("secrets.", text)
                if name == "goal-holdout":                                       # the secret: one step, by name, in the environment
                    self.assertEqual(text.count("secrets["), 1)
                    self.assertIn("GOAL_HOLDOUT: ${{ secrets[needs.classify.outputs.secret] }}", judge[0])
                    self.assertIn("environment: goal-holdout", text)
                    self.assertIn("branches: [main]", text)
                else:
                    self.assertNotIn("env:", judge[0])


class Sandbox(unittest.TestCase):
    """The container itself: candidate code can't reach the network or the job's environment."""

    def setUp(self):
        ok = shutil.which("docker") and subprocess.run(["docker", "info"], capture_output=True).returncode == 0
        if not ok:
            if os.environ.get("CI"):
                self.fail("CI must run the goal-test sandbox; Docker isn't available")
            self.skipTest("no Docker daemon here; CI runs this test")

    def test_a_goal_test_can_run_a_program_it_writes_in_tmp(self):  # cloud-review-survives' stub gitleaks
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        main = t / "main"
        shutil.copytree(HERE, main / "plugins" / "gstack-execution" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        (main / "goals" / "g1" / "tests").mkdir(parents=True)
        (main / ".github").mkdir(); shutil.copy(ROOT / ".github" / "test_codeowners.py", main / ".github")
        shutil.copy(ROOT / ".github" / "CODEOWNERS", main / ".github")
        (main / "goals" / "g1" / "GOAL.md").write_text("## Goal tests\n- `tests/test_x.py::X.test_stub_runs` (invariant)\n")
        (main / "goals" / "g1" / "tests" / "test_x.py").write_text(
            "import os, subprocess, sys, tempfile, unittest\n\n\nclass X(unittest.TestCase):\n"
            "    def test_stub_runs(self):\n        d = tempfile.mkdtemp(); p = os.path.join(d, 'stub')\n"
            "        open(p, 'w').write('#!' + sys.executable + '\\nprint(42)\\n'); os.chmod(p, 0o755)\n"
            "        self.assertEqual(subprocess.run([p], capture_output=True, text=True).stdout.strip(), '42')\n")
        r = subprocess.run(gc.sandbox_cmd(main, main, "g1"), capture_output=True, text=True, timeout=600)
        results = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual({k.split(".")[-1]: v["result"] for k, v in results.items()}, {"test_stub_runs": "passed"})

    def test_a_node_candidate_builds_with_its_locked_dependencies_and_no_network(self):
        """GO-002.6: the dependencies install from the lockfile in their own container; the goal test
        then runs the candidate's build in the sandbox, which writes into its own folder, still offline."""
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        main, cand = t / "main", t / "cand"
        shutil.copytree(HERE, main / "plugins" / "gstack-execution" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        (main / ".github").mkdir(); shutil.copy(ROOT / ".github" / "test_codeowners.py", main / ".github")
        shutil.copy(ROOT / ".github" / "CODEOWNERS", main / ".github")
        (main / "goals" / "g1" / "tests").mkdir(parents=True)
        (main / "goals" / "g1" / "GOAL.md").write_text("## Goal tests\n- `tests/test_n.py::N.test_build` (outcome)\n")
        (main / "goals" / "g1" / "tests" / "test_n.py").write_text(
            "import os, subprocess, unittest\n\n\nclass N(unittest.TestCase):\n"
            "    def test_build(self):\n        c = os.environ['GOAL_CANDIDATE']\n"
            "        b = subprocess.run(['npm', 'run', '-s', 'build'], cwd=c, capture_output=True, text=True, timeout=300)\n"
            "        self.assertEqual(b.returncode, 0, b.stderr)\n"
            "        n = subprocess.run(['node', '-e', 'fetch(\"https://example.com\").then(()=>console.log(\"online\"),()=>console.log(\"offline\"))'],"
            " capture_output=True, text=True, timeout=60)\n"
            "        self.assertEqual((b.stdout.strip(), n.stdout.strip()), ('2 days = 172800000', 'offline'))\n")
        cand.mkdir()
        (cand / "package.json").write_text('{"name":"cand","version":"1.0.0","private":true,"dependencies":{"ms":"2.1.3"},'
                                           '"scripts":{"build":"node build.js"}}\n')
        (cand / "package-lock.json").write_text(NODE_LOCK)
        (cand / "build.js").write_text("const ms = require('ms'); const fs = require('fs');\n"
                                       "fs.mkdirSync('out', {recursive: true}); fs.writeFileSync('out/x', '1');\n"
                                       "console.log('2 days = ' + ms('2 days'));\n")
        os.chmod(t, 0o755)
        deps = gc.install_deps(cand)
        self.addCleanup(shutil.rmtree, deps, True)
        r = subprocess.run(gc.sandbox_cmd(main, cand, "g1", deps), capture_output=True, text=True, timeout=600)
        results = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual({k.split(".")[-1]: v["result"] for k, v in results.items()}, {"test_build": "passed"}, r.stderr[-2000:])
        self.assertFalse((cand / "out").exists())            # the build wrote into the sandbox's copy, not the checkout

    def test_a_dependency_free_node_build_writes_in_the_sandbox_copy(self):
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        main, cand = t / "main", t / "cand"
        shutil.copytree(HERE, main / "plugins" / "gstack-execution" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        (main / ".github").mkdir(); shutil.copy(ROOT / ".github" / "test_codeowners.py", main / ".github")
        shutil.copy(ROOT / ".github" / "CODEOWNERS", main / ".github")
        (main / "goals" / "g1" / "tests").mkdir(parents=True)
        (main / "goals" / "g1" / "GOAL.md").write_text("## Goal tests\n- `tests/test_n.py::N.test_build` (outcome)\n")
        (main / "goals" / "g1" / "tests" / "test_n.py").write_text(
            "import os, subprocess, unittest\n\n\nclass N(unittest.TestCase):\n"
            "    def test_build(self):\n"
            "        b = subprocess.run(['npm', 'run', '-s', 'build'], cwd=os.environ['GOAL_CANDIDATE'], capture_output=True, text=True, timeout=120)\n"
            "        self.assertEqual((b.returncode, b.stdout.strip()), (0, 'built'), b.stderr)\n")
        cand.mkdir()
        (cand / "package.json").write_text('{"name":"cand","version":"1.0.0","private":true,"scripts":{"build":"node build.js"}}\n')
        (cand / "build.js").write_text("require('fs').writeFileSync('out.txt', '1'); console.log('built');\n")
        os.chmod(t, 0o755)
        self.assertIsNone(gc.install_deps(cand))
        r = subprocess.run(gc.sandbox_cmd(main, cand, "g1"), capture_output=True, text=True, timeout=600)
        results = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual({k.split(".")[-1]: v["result"] for k, v in results.items()}, {"test_build": "passed"}, r.stderr[-2000:])
        self.assertFalse((cand / "out.txt").exists())

    def test_a_symlinked_install_file_is_refused(self):
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        outside = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, outside, True)
        (outside / "secret").write_text("x"); (t / "other.json").write_text("{}")
        for target in (outside / "secret", t / "other.json"):
            for name in ("package.json", "package-lock.json", ".npmrc"):
                with self.subTest(target=target.name, name=name):
                    for f in ("package.json", "package-lock.json", ".npmrc"):
                        (t / f).unlink(missing_ok=True); (t / f).write_text("{}")
                    (t / name).unlink(); (t / name).symlink_to(target)
                    with self.assertRaises(SystemExit):
                        gc.install_deps(t, run=lambda *a, **k: self.fail("installed through a symlink"))

    def test_no_lockfile_installs_nothing(self):
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        self.assertIsNone(gc.install_deps(t, run=lambda *a, **k: self.fail("installed without a lockfile")))

    def test_the_install_container_gets_three_files_and_no_checkout(self):
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        for f in ("package.json", "package-lock.json", ".npmrc", "secret.env", "src.js"):
            (t / f).write_text("x")
        seen = {}
        def run(cmd, **k):
            seen["cmd"] = cmd
            seen["files"] = sorted(p.name for p in Path(cmd[cmd.index("-v") + 1].split(":")[0]).iterdir())
            return subprocess.CompletedProcess(cmd, 0, "", "")
        deps = gc.install_deps(t, run=run); self.addCleanup(shutil.rmtree, deps, True)
        self.assertEqual(seen["files"], [".npmrc", "package-lock.json", "package.json"])
        self.assertEqual(seen["cmd"].count("-v"), 1)
        self.assertIn("--ignore-scripts", seen["cmd"])
        self.assertNotIn("GOAL_HOLDOUT", " ".join(seen["cmd"]))

    def test_baseline_runs_in_the_container(self):
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        wt, goal = Path(tempfile.mkdtemp()), t / "g1"         # review F1: 0700, as main_checkout() makes it
        self.addCleanup(shutil.rmtree, wt, True)
        os.chmod(t, 0o755)
        shutil.copytree(HERE, wt / "plugins" / "gstack-execution" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        (wt / ".github").mkdir(); shutil.copy(ROOT / ".github" / "test_codeowners.py", wt / ".github")
        shutil.copy(ROOT / ".github" / "CODEOWNERS", wt / ".github")
        (goal / "tests").mkdir(parents=True)
        (goal / "GOAL.md").write_text("## Goal tests\n- `tests/test_y.py::Y.test_in_container` (invariant)\n")
        (goal / "tests" / "test_y.py").write_text(      # passes only in the container, where the candidate is /candidate
            "import os, unittest\n\n\nclass Y(unittest.TestCase):\n"
            "    def test_in_container(self):\n        self.assertEqual(os.environ['GOAL_CANDIDATE'], '/candidate')\n")
        import goal_brief as gb
        self.assertEqual(gb.baseline(goal, wt, run=gb.sandboxed(goal, wt)), ([], 1))
        self.assertTrue(gb.baseline(goal, wt)[0])               # on the host the same test fails: baseline would differ

    def test_candidate_code_sees_no_network_and_no_token(self):
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        main, cand = t / "main", t / "candidate"
        shutil.copytree(HERE, main / "plugins" / "gstack-execution" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        (main / ".github").mkdir(); shutil.copy(ROOT / ".github" / "test_codeowners.py", main / ".github")
        shutil.copy(ROOT / ".github" / "CODEOWNERS", main / ".github")
        (main / "goals" / "g1" / "tests").mkdir(parents=True)
        (main / "goals" / "g1" / "GOAL.md").write_text(
            "## Goal tests\n- `tests/test_s.py::S.test_code_runs` (invariant)\n"
            "- `tests/test_s.py::S.test_network` (invariant)\n- `tests/test_s.py::S.test_token` (invariant)\n")
        (main / "goals" / "g1" / "tests" / "test_s.py").write_text(
            "import os, subprocess, sys, unittest\n\n\ndef run(expr):\n"
            "    r = subprocess.run([sys.executable, '-c', 'import goalmod; print(repr(%s))' % expr],\n"
            "                       cwd=os.environ['GOAL_CANDIDATE'], capture_output=True, text=True, timeout=60)\n"
            "    return r.stdout.strip()\n\n\nclass S(unittest.TestCase):\n"
            "    def test_code_runs(self):\n        self.assertEqual(run('goalmod.ok'), 'True')\n\n"
            "    def test_network(self):\n        self.assertEqual(run('goalmod.reach()'), 'True')\n\n"
            "    def test_token(self):\n        self.assertEqual(run('goalmod.token()'), \"'leaked-secret'\")\n")
        cand.mkdir()
        (cand / "goalmod.py").write_text(
            "import os, socket\nok = True\n\n\ndef reach():\n    socket.create_connection(('1.1.1.1', 53), 3).close()\n    return True\n\n\n"
            "def token():\n    return os.environ.get('GITHUB_TOKEN')\n")
        saved, os.environ["GITHUB_TOKEN"] = os.environ.get("GITHUB_TOKEN"), "leaked-secret"
        try:
            r = subprocess.run(gc.sandbox_cmd(main, cand, "g1"), capture_output=True, text=True, timeout=600)
        finally:
            os.environ.pop("GITHUB_TOKEN") if saved is None else os.environ.__setitem__("GITHUB_TOKEN", saved)
        results = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual({k.split(".")[-1]: v["result"] for k, v in results.items()},
                         {"test_code_runs": "passed", "test_network": "failed", "test_token": "failed"})


    def test_the_holdout_in_its_container_sees_no_secret_no_network_no_file(self):  # GO-003.6
        import hashlib
        t = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, t, True)
        main, cand = t / "main", t / "candidate"
        shutil.copytree(HERE, main / "plugins" / "gstack-execution" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        (main / ".github").mkdir(); shutil.copy(ROOT / ".github" / "test_codeowners.py", main / ".github")
        shutil.copy(ROOT / ".github" / "CODEOWNERS", main / ".github")
        src = ("import os, subprocess, sys, unittest\n\n\ndef run(expr):\n"
               "    r = subprocess.run([sys.executable, '-c', 'import goalmod; print(repr(%s))' % expr],\n"
               "                       cwd=os.environ['GOAL_CANDIDATE'], capture_output=True, text=True, timeout=60)\n"
               "    return r.stdout.strip()\n\n\nclass H(unittest.TestCase):\n"
               "    def test_code_runs(self):\n        self.assertEqual(run('goalmod.ok'), 'True')\n\n"
               "    def test_no_secret(self):\n        self.assertEqual(run('goalmod.secret()'), 'None')\n\n"
               "    def test_no_network(self):\n        self.assertEqual(run('goalmod.reach()'), 'False')\n\n"
               "    def test_no_holdout_file(self):\n        self.assertEqual(run('goalmod.files()'), '[]')\n")
        (main / "goals" / "g1").mkdir(parents=True)
        (main / "goals" / "g1" / "holdout.sha256").write_text(hashlib.sha256(src.encode()).hexdigest() + "\n")
        cand.mkdir()
        (cand / "goalmod.py").write_text(
            "import glob, os, socket\nok = True\n\n\ndef secret():\n    return os.environ.get('GOAL_HOLDOUT')\n\n\n"
            "def reach():\n    try:\n        socket.create_connection(('1.1.1.1', 53), 3).close()\n        return True\n"
            "    except OSError:\n        return False\n\n\n"
            "def files():\n    return [f for f in glob.glob('/tmp/**', recursive=True) + glob.glob('/candidate/**', recursive=True)"
            " if os.path.isfile(f) and 'test_no_' + 'holdout_file' in open(f, errors='replace').read()]\n")   # split: not in this file
        saved, os.environ["GOAL_HOLDOUT"] = os.environ.get("GOAL_HOLDOUT"), src
        try:
            v = gc.holdout(pr(base="main", head="goal/g1"), main, "m" * 40, cand, src)
        finally:
            os.environ.pop("GOAL_HOLDOUT") if saved is None else os.environ.__setitem__("GOAL_HOLDOUT", saved)
        self.assertEqual(v["conclusion"], "success", v)


if __name__ == "__main__":
    unittest.main()
