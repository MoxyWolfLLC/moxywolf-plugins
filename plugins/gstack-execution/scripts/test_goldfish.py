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

    def change_criteria(self, text):
        self.packet["acceptance_criteria"] = [text]
        self.packet["coverage"]["criteria"][0]["declared"] = text
        self.save()

    def test_a_changed_criteria_hash_reads_absent_at_the_same_head(self):
        self.goldfish()
        self.change_criteria("f(1) == 2 and f(2) == 3")
        self.assertEqual(self.open_review()["goldfish"], "absent")

    def test_a_changed_criteria_hash_reads_absent_when_the_head_also_moved(self):
        self.goldfish()   # unconsumed: no open has run in this fixture
        self.change_criteria("f(1) == 2 and f(2) == 3")
        self.at(self.commit("def f(x):\n    return 1 + x\n"))
        self.assertEqual(self.open_review()["goldfish"], "absent",
                         "without the hash check this would read ran_earlier")

    def test_an_open_with_no_pre_pass_still_appends_its_marker(self):
        self.assertEqual(self.open_review()["goldfish"], "absent")
        self.assertEqual([e.get("opened") is not None for e in self.entries()], [True])

    def test_each_checkpoint_is_judged_by_its_own_pre_passes(self):
        self.goldfish()
        self.assertEqual(self.open_review()["goldfish"], "ran_at_head")
        self.at(self.commit("def f(x):\n    return x + 1  # second checkpoint\n"))
        self.assertEqual(self.open_review()["goldfish"], "absent", "the first checkpoint's pre-pass is spent")
        self.goldfish()
        self.assertEqual(self.open_review()["goldfish"], "ran_at_head",
                         "a pre-pass after the last open decides, not the first one ever written")
        self.assertEqual(sum("opened" in e for e in self.entries()), 3)

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

    def test_a_tool_that_starts_and_fails_appends_nothing(self):
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "echo partial; exit 3"
        try:
            with self.assertRaises(pr.ReviewError) as e:
                pr.cmd_goldfish(argparse.Namespace(packet=str(self.pfile), builder="claude", timeout=30))
        finally:
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
        self.assertEqual(e.exception.outcome, "review_unavailable")
        self.assertFalse(pr.goldfish_path(self.packet).exists())

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

    def test_the_prompt_carries_the_surface_trust_lines_round_carries(self):
        seen = {}
        real = pr.run_reviewer
        def capture(tool, prompt, root, timeout, schema=None, named=()):
            seen["prompt"] = prompt
            return json.dumps(ANSWER), "fake"
        pr.run_reviewer = capture
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                pr.cmd_goldfish(argparse.Namespace(packet=str(self.pfile), builder="claude", timeout=30))
        finally:
            pr.run_reviewer = real
        from enclosure import RULE
        for line in (pr.TRUST_FILES, pr.TRUST_PROVENANCE, RULE):
            self.assertIn(line, seen["prompt"])
        round_prompt = pr.build_prompt(self.packet, 1, None, None)
        self.assertIn(pr.TRUST_FILES, round_prompt)
        self.assertIn(pr.TRUST_PROVENANCE, round_prompt)

    def count(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = pr.cmd_goldfish_count(argparse.Namespace(repo=str(self.repo)))
        return got, out.getvalue()

    def test_the_drop_condition_quotes_counted_reviews_and_refers_after_ten(self):
        self.open_review()   # absent: not counted
        for i in range(10):
            self.goldfish()
            self.open_review()
        got, text = self.count()
        self.assertEqual((len(got["counted"]), got["ran_earlier"]), (10, 0))
        self.assertEqual(text.count("goldfish=ran_at_head"), 10)
        self.assertIn("bring XE-045 back to Dorian", text)
        self.goldfish()
        self.at(self.commit("def f(x):\n    return x + 1  # after the pre-pass\n"))
        self.open_review()
        got, text = self.count()
        self.assertEqual((len(got["counted"]), got["ran_earlier"]), (11, 1))
        self.assertNotIn("bring XE-045 back", text)

    def test_the_drop_condition_survives_a_removed_checkout(self):
        self.sh("remote", "add", "origin", "https://example.invalid/acme/repo.git")
        for i in range(9):
            self.goldfish(); self.open_review()
        self.goldfish()
        self.at(self.commit("def f(x):\n    return x + 1  # moved\n"))
        self.open_review()   # the one ran_earlier
        moved = self.tmp / "elsewhere"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(moved)], check=True)
        subprocess.run(["git", "-C", str(moved), "remote", "set-url", "origin", "https://example.invalid/acme/repo.git"], check=True)
        shutil.rmtree(self.repo)   # every review's checkout is gone
        with contextlib.redirect_stdout(io.StringIO()):
            got = pr.cmd_goldfish_count(argparse.Namespace(repo=str(moved)))
        self.assertEqual((len(got["counted"]), got["ran_earlier"]), (10, 1),
                         "a removed checkout neither hides a ran_earlier nor drops a ran_at_head")

    def test_the_drop_condition_counts_only_this_repository(self):
        self.goldfish(); self.open_review()
        other = self.tmp / "other"; other.mkdir()
        subprocess.run(["git", "-C", str(other), "init", "-q"], check=True)
        with contextlib.redirect_stdout(io.StringIO()):
            got = pr.cmd_goldfish_count(argparse.Namespace(repo=str(other)))
        self.assertEqual(got["counted"], [])
        self.assertEqual(len(self.count()[0]["counted"]), 1)

    # ---- the review never reads it ----

    def test_a_review_comes_out_the_same_with_or_without_a_pre_pass(self):
        without, out_a = self.review()
        reviews_before = sorted(p.name for p in pr.REVIEW_DIR.iterdir())
        states_before = sorted(pr.REVIEW_DIR.glob("*/state.json"))
        self.goldfish()
        self.assertEqual(sorted(p.name for p in pr.REVIEW_DIR.iterdir()), reviews_before,
                         "the pre-pass opens no review")
        self.assertEqual(sorted(pr.REVIEW_DIR.glob("*/state.json")), states_before, "and writes no state.json")
        with_, out_b = self.review()
        self.assertEqual(out_a, out_b)
        for k in ("outcome", "coverage_status", "coverage_checked", "release_lane", "reviewer", "rounds_used"):
            self.assertEqual(without.get(k), with_.get(k), k)
        self.assertEqual((without["goldfish"], with_["goldfish"]), ("absent", "ran_at_head"))


if __name__ == "__main__":
    unittest.main()
