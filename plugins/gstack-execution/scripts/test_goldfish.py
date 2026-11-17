#!/usr/bin/env python3
"""XE-045 acceptance: the goldfish pre-pass advises and nothing else.

What these pin is the drop condition's honesty and the review's independence. A later re-run must not
hide a change made after the first pre-pass, a changed criterion must not count as the same pass, a
missing tool must not be swapped for another, and a review must come out the same with or without one.
"""
import argparse, contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import peer_review as pr

ANSWER = {"criteria": [{"criterion_no": 1, "shown": False, "assumes": ["f is only called with ints"]}]}
CLEAN = {"verdict": "no_blocking_findings",
         "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
         "findings": [], "blocker_resolutions": []}


class GoldfishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="xe045-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"; self.repo.mkdir()
        self.sh("init", "-q"); self.sh("config", "user.email", "t@t"); self.sh("config", "user.name", "t")
        (self.repo / "a.py").write_text("def f(x):\n    return x\n"); self.sh("add", "."); self.sh("commit", "-qm", "base")
        self.base = self.sh("rev-parse", "HEAD")
        self.head = self.commit("def f(x):\n    return x + 1\n")
        self.packet = {
            "outcome": "f adds one", "acceptance_criteria": ["f(1) == 2"], "items": ["FX-001"],
            "repos": [{"path": str(self.repo), "base": self.base, "head": self.head}],
            "changed_behavior": "f returns x+1", "exclusions": [],
            "tests": {"commands": [], "results": "", "environment": "test"}, "release_owner": "fixture-human",
            "data_use": {"owner": "fixture-human", "classification": "test", "allow_repository": True,
                         "allow_history": True, "allowed_tools": ["codex", "claude"]},
            "coverage": {"status": "checked", "criteria": [{"item": "FX-001", "criterion_no": 1, "declared": "fixture", "probability": 0.9}]},
            "model_selection": {"status": "checked", "mode": "shadow", "tier": "floor", "rule": "fixture"},
        }
        self.pfile = self.tmp / "packet.json"; self.save()
        pr.REVIEW_DIR = self.tmp / "reviews"
        pr._SELFTEST = True
        self.spec = pr.spec_review_gate
        pr.spec_review_gate = lambda packet: None   # SR-001 has its own tests; this fixture has no DESIGN.md
        self.addCleanup(setattr, pr, "spec_review_gate", self.spec)

    def sh(self, *c):
        return subprocess.run(["git", "-C", str(self.repo), *c], check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, text):
        (self.repo / "a.py").write_text(text); self.sh("commit", "-qam", "change")
        return self.sh("rev-parse", "HEAD")

    def save(self):
        self.pfile.write_text(json.dumps(self.packet))

    def at(self, head):
        self.packet["repos"][0]["head"] = head; self.save()

    def goldfish(self, builder="claude"):
        (self.tmp / "answer.json").write_text(json.dumps(ANSWER))
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "cat " + str(self.tmp / "answer.json")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                return pr.cmd_goldfish(argparse.Namespace(packet=str(self.pfile), builder=builder, timeout=30))
        finally:
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)

    def open_review(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return pr.cmd_open(argparse.Namespace(builder="claude", packet=str(self.pfile), max_rounds=3, timeout=30))

    def review(self):
        """open, then one stub round; returns the state and the round's outcome."""
        state = self.open_review()
        (self.tmp / "reply.json").write_text(json.dumps(CLEAN))
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "cat " + str(self.tmp / "reply.json")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                outcome = pr.cmd_round(argparse.Namespace(review_id=state["review_id"], head=[]))
        finally:
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
        return pr.load(pr.rdir(state["review_id"]), "state.json"), outcome

    def entries(self):
        return json.loads(pr.goldfish_path(self.packet).read_text())["entries"]

    # ---- what open records ----

    def test_no_pre_pass_reads_absent(self):
        self.assertEqual(self.open_review()["goldfish"], "absent")

    def test_a_pre_pass_at_the_opened_head_reads_ran_at_head(self):
        self.goldfish()
        self.assertEqual(self.open_review()["goldfish"], "ran_at_head")

    def test_a_first_entry_at_another_head_reads_ran_earlier_even_after_a_rerun_at_the_opened_head(self):
        self.goldfish()
        self.at(self.commit("def f(x):\n    return int(x) + 1\n"))
        self.goldfish()   # the re-run at the head being opened
        self.assertEqual(len(self.entries()), 2, "a re-run appends; it never rewrites the first entry")
        self.assertEqual(self.open_review()["goldfish"], "ran_earlier")

    def test_a_changed_criteria_hash_reads_absent_even_when_the_head_also_moved(self):
        self.goldfish()
        self.packet["acceptance_criteria"] = ["f(1) == 2 and f(2) == 3"]
        self.packet["coverage"]["criteria"][0]["declared"] = "fixture 2"
        self.save()
        self.assertEqual(self.open_review()["goldfish"], "absent")
        self.at(self.commit("def f(x):\n    return 1 + x\n"))
        self.assertEqual(self.open_review()["goldfish"], "absent")

    # ---- what it refuses ----

    def test_a_missing_tool_exits_non_zero_and_nothing_is_substituted_or_written(self):
        pr._SELFTEST = False   # the real path: no fake command reaches run_reviewer
        bin_ = self.tmp / "bin"; bin_.mkdir(); (bin_ / "git").symlink_to(shutil.which("git"))
        path = os.environ["PATH"]; os.environ["PATH"] = str(bin_)
        try:
            with self.assertRaises(pr.ReviewError) as e:
                pr.cmd_goldfish(argparse.Namespace(packet=str(self.pfile), builder="codex", timeout=30))
        finally:
            os.environ["PATH"] = path
        self.assertEqual(e.exception.outcome, "review_unavailable")
        self.assertIn("codex", e.exception.detail)
        self.assertFalse(pr.goldfish_path(self.packet).exists(), "a run that did not answer appends nothing")

    def test_an_unknown_builder_exits_non_zero(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "peer_review.py"), "goldfish", str(self.pfile),
                            "--builder", "gemini"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("gemini", r.stderr)

    def test_a_run_inside_a_reviewer_session_is_refused(self):
        os.environ[pr.RECURSION_ENV] = "1"
        try:
            with self.assertRaises(SystemExit) as e:
                self.goldfish()
        finally:
            os.environ.pop(pr.RECURSION_ENV, None)
        self.assertIn("reviewer session", str(e.exception.code))
        self.assertFalse(pr.goldfish_path(self.packet).exists())

    # ---- the review never reads it ----

    def test_a_review_comes_out_the_same_with_or_without_a_pre_pass(self):
        without, out_a = self.review()
        reviews_before = sorted(p.name for p in pr.REVIEW_DIR.iterdir())
        self.goldfish()
        self.assertEqual(sorted(p.name for p in pr.REVIEW_DIR.iterdir()), reviews_before + ["goldfish"],
                         "the pre-pass opens no review and writes no state.json")
        with_, out_b = self.review()
        self.assertEqual(out_a, out_b)
        for k in ("outcome", "coverage_status", "coverage_checked", "release_lane", "reviewer", "rounds_used"):
            self.assertEqual(without.get(k), with_.get(k), k)
        self.assertEqual((without["goldfish"], with_["goldfish"]), ("absent", "ran_at_head"))


if __name__ == "__main__":
    unittest.main()
