#!/usr/bin/env python3
"""XE-029 acceptance. SM-004's review 20260929-175128 is the case: round 3 saw only the round's two
changed files, marked 8 criteria unmet for missing evidence, called the verdict blocking with only a
`separate` finding, and was recorded `malformed_output`; round 2 ran without a token and read no CI."""
import io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace as ns

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr

CRIT = ["hooks.json names the command", "tests pass"]


def reply(verdict, met, findings=(), resolutions=()):
    return json.dumps({"verdict": verdict,
                       "acceptance": [{"criterion": c, "met": m, "evidence": "x:1"} for c, m in zip(CRIT, met)],
                       "findings": [dict(id=i, severity=s, file="a.py", line=1, what="w", evidence="e", criterion="c", fix="f")
                                    for i, s in findings],
                       "blocker_resolutions": list(resolutions), "regressions_from_fixes": []})


class FixRoundSurface(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="xe029-")); self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "app"; self.repo.mkdir()
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()
        g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        (self.repo / "keep.txt").write_text("0"); g("add", "."); g("commit", "-qm", "base"); self.base = g("rev-parse", "HEAD")
        (self.repo / "hooks.json").write_text("{}"); g("add", "."); g("commit", "-qm", "round 1"); self.h1 = g("rev-parse", "HEAD")
        (self.repo / "fix.py").write_text("x = 1\n"); g("add", "."); g("commit", "-qm", "round 2"); self.h2 = g("rev-parse", "HEAD")

    def test_a_fix_round_carries_the_whole_change_and_its_own_delta(self):
        repos = [{"path": str(self.repo), "base": self.h1, "head": self.h2, "review_base": self.base}]
        out = self.tmp / "o"; out.mkdir()
        surf, stats = pr.build_surface(repos, out)
        changed = surf / "changed" / "0-app"
        self.assertTrue((changed / "hooks.json").exists(), "changed only before round 2, still in the surface")
        self.assertTrue((changed / "fix.py").exists())
        self.assertIn("hooks.json", (surf / "CHANGE.diff").read_text())
        self.assertIn("fix.py", (surf / "ROUND.diff").read_text())
        self.assertNotIn("hooks.json", (surf / "ROUND.diff").read_text())
        self.assertIn("ROUND.diff", (surf / "SURFACE.md").read_text())

    def test_a_packet_from_before_this_item_keeps_the_round_delta(self):
        repos = [{"path": str(self.repo), "base": self.h1, "head": self.h2}]
        out = self.tmp / "o2"; out.mkdir()
        surf, _ = pr.build_surface(repos, out)
        self.assertFalse((surf / "changed" / "0-app" / "hooks.json").exists())
        self.assertFalse((surf / "ROUND.diff").exists())


class VerdictAndAcceptance(unittest.TestCase):
    packet = {"acceptance_criteria": CRIT}

    def test_unmet_criterion_with_only_a_separate_finding_is_valid(self):
        out = pr.validate(reply("blocking_findings", [False, True], [("F6", "separate")]), self.packet, None, {})
        self.assertEqual(out["verdict"], "blocking_findings")

    def test_blocking_verdict_with_everything_met_and_no_blocker_is_still_malformed(self):
        with self.assertRaises(pr.ReviewError) as c:
            pr.validate(reply("blocking_findings", [True, True], [("F6", "separate")]), self.packet, None, {})
        self.assertEqual(c.exception.outcome, "malformed_output")

    def test_clean_verdict_with_a_blocking_finding_is_still_malformed(self):
        with self.assertRaises(pr.ReviewError) as c:
            pr.validate(reply("no_blocking_findings", [True, True], [("F1", "blocking")]), self.packet, None, {})
        self.assertEqual(c.exception.outcome, "malformed_output")


class DispatchNeedsACiReader(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ); self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.env)))
        os.environ.pop("GITHUB_TOKEN", None)
        empty = tempfile.mkdtemp(prefix="nogh-"); self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        os.environ["PATH"] = empty                       # no gh anywhere

    def test_a_named_run_with_no_token_and_no_gh_is_refused(self):
        with self.assertRaises(SystemExit) as c:
            pr.require_ci_reader({"tests": {"ci_runs": [{"repo": "app", "run_id": 1}]}}, [])
        self.assertIn("agent_token.py exec", str(c.exception))
        with self.assertRaises(SystemExit):
            pr.require_ci_reader({}, ["app=1"])

    def test_dispatch_refuses_before_starting_a_round(self):
        root = Path(tempfile.mkdtemp(prefix="xe029-reviews-")); self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        old = pr.REVIEW_DIR; pr.REVIEW_DIR = root; self.addCleanup(setattr, pr, "REVIEW_DIR", old)
        d = root / "r1"; d.mkdir()
        (d / "state.json").write_text(json.dumps({"rounds_used": 0, "outcome": "opened"}))
        (d / "packet.json").write_text(json.dumps({"tests": {"ci_runs": [{"repo": "app", "run_id": 1}]}}))
        with self.assertRaises(SystemExit) as c:
            pr.cmd_dispatch(ns(review_id="r1", head=[], ci_run=[]))
        self.assertIn("agent_token.py exec", str(c.exception))
        self.assertFalse((d / "dispatch.json").exists(), "nothing was started")

    def test_no_named_run_or_a_token_goes_ahead(self):
        pr.require_ci_reader({}, [])
        os.environ["GITHUB_TOKEN"] = "t"
        pr.require_ci_reader({"tests": {"ci_runs": [{"repo": "app", "run_id": 1}]}}, [])


class MergeInstructionSaysItPrints(unittest.TestCase):
    def test_it_warns_that_it_did_not_post(self):
        o, e = io.StringIO(), io.StringIO()
        with redirect_stdout(o), redirect_stderr(e):
            pr.cmd_merge_instruction(ns(covers="83", text="merge #83", given_at="2026-09-30T16:32Z", owner="dorianatmoxywolf"))
        self.assertIn("gstack-merge-instruction", json.loads(o.getvalue())["body"])
        self.assertIn("did not post it", e.getvalue())


if __name__ == "__main__":
    unittest.main()
