#!/usr/bin/env python3
"""EV-002 and EV-004 acceptance: findings are bound to content, links are re-resolved,
and the approver's reconstruction has a field it can be written in.

The failure these pin is silent by construction. A finding keeps a file and a line; the
file changes; the name still resolves; the report stays complete, internally consistent,
and wrong about its subject. Nothing throws. So each test here changes the world under a
finished review and asserts that the review notices.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr

BLOCKING = {
    "verdict": "blocking_findings",
    "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
    "findings": [{"id": "F1", "severity": "blocking", "file": "a.py", "line": 2,
                  "what": "off by one", "evidence": "a.py:2 returns x + 2", "criterion": "f(1) == 2", "fix": "return x + 1"}],
    "blocker_resolutions": [],
}


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ev2-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"; self.repo.mkdir()
        self.sh("init", "-q"); self.sh("config", "user.email", "t@t"); self.sh("config", "user.name", "t")
        self.write("def f(x):\n    return x\n"); self.sh("add", "."); self.sh("commit", "-qm", "base")
        self.base = self.sh("rev-parse", "HEAD")
        self.write("def f(x):\n    return x + 2\n"); self.sh("commit", "-qam", "head")
        self.head = self.sh("rev-parse", "HEAD")
        self.packet = {
            "outcome": "f adds one", "acceptance_criteria": ["f(1) == 2"],
            "repos": [{"path": str(self.repo), "base": self.base, "head": self.head}],
            "changed_behavior": "f returns x+1", "exclusions": [],
            "tests": {"commands": [], "results": "", "environment": "test"}, "release_owner": "fixture-human",
            "data_use": {"owner": "fixture-human", "classification": "test", "allow_repository": True,
                         "allow_history": True, "allowed_tools": ["codex", "claude"]},
        }
        self.pfile = self.tmp / "packet.json"; self.pfile.write_text(json.dumps(self.packet))
        pr.REVIEW_DIR = self.tmp / "reviews"
        pr._SELFTEST = True

    def sh(self, *c):
        return subprocess.run(["git", "-C", str(self.repo), *c], check=True, capture_output=True, text=True).stdout.strip()

    def write(self, text):
        (self.repo / "a.py").write_text(text)

    def ns(self, **k):
        return argparse.Namespace(**k)

    def open_review(self, max_rounds=3):
        return pr.cmd_open(self.ns(builder="claude", packet=str(self.pfile), max_rounds=max_rounds, timeout=30))["review_id"]

    def fake_round(self, rid, payload=None):
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "cat " + str(self.tmp / "reply.json")
        (self.tmp / "reply.json").write_text(json.dumps(payload or BLOCKING))
        try:
            return pr.cmd_round(self.ns(review_id=rid, head=[]))
        finally:
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)

    def reviewed(self):
        """A finished round with one blocking finding bound to content."""
        rid = self.open_review()
        self.assertEqual(self.fake_round(rid), "blocking_findings")
        return rid, pr.rdir(rid)

    # ---- binding ----

    def test_round_binds_each_finding_to_content_at_the_reviewed_head(self):
        _, d = self.reviewed()
        subjects = pr.load(d, "round-1.json")["subjects"]
        s = subjects["F1"]
        self.assertTrue(s["bound"])
        self.assertEqual(s["head"], self.head)
        self.assertEqual(s["blob"], self.sh("rev-parse", f"{self.head}:a.py"))
        self.assertTrue(s["span"], "a finding must carry a content hash, not only a name")
        self.assertTrue(s["line_exists"])

    def test_snapshot_prefixed_and_repo_relative_paths_bind_to_one_subject(self):
        """Codex reports '0-repo/a.py'; Claude reports 'a.py'. Both name the same code,
        so both must bind to the same content or the binding proves nothing."""
        repos = self.packet["repos"]
        a = pr.bind_subjects([dict(BLOCKING["findings"][0], file="a.py")], repos)["F1"]
        b = pr.bind_subjects([dict(BLOCKING["findings"][0], file=f"0-{self.repo.name}/a.py")], repos)["F1"]
        self.assertTrue(a["bound"] and b["bound"])
        self.assertEqual((a["blob"], a["span"]), (b["blob"], b["span"]))

    def test_a_line_past_the_end_of_the_file_is_not_a_resolved_subject(self):
        s = pr.bind_subjects([dict(BLOCKING["findings"][0], line=400)], self.packet["repos"])["F1"]
        self.assertFalse(s["line_exists"], "a finding pointing past the end of the file never resolved")

    def test_a_path_no_repository_holds_is_not_bound(self):
        s = pr.bind_subjects([dict(BLOCKING["findings"][0], file="nowhere/missing.py")], self.packet["repos"])["F1"]
        self.assertFalse(s["bound"])
        self.assertIn("no packet repository", s["why"])

    # ---- verification ----

    def test_verify_passes_while_nothing_has_moved(self):
        rid, d = self.reviewed()
        pr.cmd_disposition(self.ns(review_id=rid, items=["F1=fixed"]))
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "links_verified", report["checks"])
        self.assertGreater(report["examined"], 0)

    def test_subject_changing_under_an_undisposed_finding_is_a_stale_link(self):
        """The failure the whole command exists for: the name still resolves, the
        content behind it is different, and nothing else in the record disagrees."""
        _, d = self.reviewed()
        self.write("def f(x):\n    return x + 1  # rewritten\n"); self.sh("commit", "-qam", "moved on")
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "stale_link")
        broken = [c for c in report["checks"] if not c["ok"]]
        self.assertTrue(any("no longer describes the code" in c["detail"] for c in broken), broken)

    def test_expected_drift_under_a_fixed_finding_is_not_stale(self):
        """A finding disposed `fixed` SHOULD read differently now. Treating that as
        drift would make the check cry wolf on every successful repair."""
        rid, d = self.reviewed()
        pr.cmd_disposition(self.ns(review_id=rid, items=["F1=fixed"]))
        self.write("def f(x):\n    return x + 1\n"); self.sh("commit", "-qam", "fix")
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "links_verified", [c for c in report["checks"] if not c["ok"]])

    def test_an_altered_record_is_detected_at_the_reviewed_head(self):
        """Run directories are ordinary writable files. A record that no longer matches
        the commit it claims to describe is reported rather than trusted."""
        _, d = self.reviewed()
        rec = pr.load(d, "round-1.json")
        rec["subjects"]["F1"]["span"] = "0" * 16
        pr.save(d, "round-1.json", rec)
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "stale_link")
        self.assertTrue(any("record altered" in c["detail"] for c in report["checks"] if not c["ok"]))

    def test_a_disposition_naming_no_finding_is_reported(self):
        """cmd_disposition refuses an unknown id, so this can only arrive by a hand
        edit of the run directory, which is exactly what the contract says those files
        are: writable evidence, not tamperproof storage."""
        rid, d = self.reviewed()
        pr.save(d, "dispositions.json", {"F1": "fixed", "F9": "deferred"})
        report = pr.verify_links(d)
        self.assertTrue(any(c["link"].startswith("disposition F9") and not c["ok"] for c in report["checks"]))
        self.assertEqual(report["outcome"], "incomplete_record")

    def test_a_missing_disposition_is_an_incomplete_record_not_a_stale_link(self):
        """An absent entry and a link that resolved to the wrong thing are different
        failures. One outcome name for both would blur the finding this work reports."""
        _, d = self.reviewed()
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "incomplete_record")
        self.assertTrue(all(c["kind"] == "record" for c in report["checks"] if not c["ok"]))

    def test_a_blocking_finding_without_a_disposition_is_reported(self):
        _, d = self.reviewed()
        report = pr.verify_links(d)
        self.assertTrue(any("disposition for blocking F1" in c["link"] and not c["ok"] for c in report["checks"]))

    def test_a_review_that_predates_binding_is_unverifiable_not_verified(self):
        """An old record cannot be re-resolved. That is a third answer, and folding it
        into either of the other two would be the false pass this work is about."""
        _, d = self.reviewed()
        rec = pr.load(d, "round-1.json"); rec.pop("subjects"); pr.save(d, "round-1.json", rec)
        self.assertEqual(pr.verify_links(d)["outcome"], "links_unverifiable")

    def test_verifying_nothing_is_not_a_pass(self):
        """EV-001 applied to the verifier itself."""
        _, d = self.reviewed()
        pr.save(d, "packet.json", dict(self.packet, repos=[]))
        pr.save(d, "state.json", dict(pr.load(d, "state.json"), rounds_used=0))
        pr.save(d, "dispositions.json", {})
        self.assertEqual(pr.verify_links(d)["outcome"], "examined_nothing")

    # ---- the human edge ----

    def test_release_records_what_the_approver_can_check_and_verify_re_runs_it(self):
        rid, d = self.reviewed()
        pr.cmd_disposition(self.ns(review_id=rid, items=["F1=fixed"]))
        self.write("def f(x):\n    return x + 1\n"); self.sh("commit", "-qam", "fix")
        clean = {"verdict": "no_blocking_findings",
                 "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
                 "findings": [], "blocker_resolutions": [{"id": "F1", "resolved": True, "evidence": "a.py:2"}]}
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "cat " + str(self.tmp / "reply.json")
        (self.tmp / "reply.json").write_text(json.dumps(clean))
        try:
            self.assertEqual(pr.cmd_round(self.ns(review_id=rid, head=[f"{self.repo}={self.sh('rev-parse', 'HEAD')}"])), "fixes_verified")
        finally:
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
        with self.assertRaises(pr.ReviewError) as caught:
            pr.cmd_release(self.ns(review_id=rid, target="main", observation=["the suite ran clean :: git -C %s log -1 --format=%%H" % self.repo]))
        self.assertEqual(caught.exception.outcome, "awaiting_human_release")
        release = pr.load(d, "release.json")
        claims = [o["claim"] for o in release["observations"]]
        self.assertTrue(any("is the reviewed head" in c for c in claims), claims)
        self.assertIn("the suite ran clean", claims)
        self.assertIn("not evidence that a person read", release["observations_note"])
        self.assertEqual(pr.verify_links(d)["outcome"], "links_verified")

    def test_an_observation_that_no_longer_holds_is_caught_by_verify(self):
        rid, d = self.reviewed()
        pr.save(d, "release.json", {"observations": [
            {"claim": "head is what I checked", "command": f"git -C {self.repo} rev-parse HEAD",
             "output_digest": "deadbeefdeadbeef", "automatic": True}]})
        report = pr.verify_links(d)
        self.assertTrue(any("head is what I checked" in c["link"] and not c["ok"] for c in report["checks"]))

    def test_release_refuses_while_an_evidential_link_is_stale(self):
        """A passing review plus moved code is exactly the document a person signs."""
        rid, d = self.reviewed()
        state = pr.load(d, "state.json"); state["outcome"] = "no_blocking_findings"; pr.save(d, "state.json", state)
        rec = pr.load(d, "round-1.json")
        rec["subjects"]["F1"]["span"] = "0" * 16
        pr.save(d, "round-1.json", rec)
        with self.assertRaises(pr.ReviewError) as caught:
            pr.cmd_release(self.ns(review_id=rid, target="main", observation=[]))
        self.assertIn(caught.exception.outcome, {"stale_link", "release_blocked"})


class ReviewRegressions(unittest.TestCase):
    """Blockers from review 20260912-122421-80159e3-_lrr97ak (codex/gpt-6-astra)."""

    setUp = LinkTests.setUp
    sh, write, ns = LinkTests.sh, LinkTests.write, LinkTests.ns
    open_review, fake_round, reviewed = LinkTests.open_review, LinkTests.fake_round, LinkTests.reviewed

    def test_f1_a_dot_prefixed_path_still_binds(self):
        """lstrip('./') removed the leading dot, so findings in .claude-plugin and
        .github bound as unresolvable and every check on them was skipped."""
        (self.repo / ".claude-plugin").mkdir()
        (self.repo / ".claude-plugin" / "marketplace.json").write_text('{"a": 1}\n')
        self.sh("add", "."); self.sh("commit", "-qm", "hidden dir")
        repos = [dict(self.packet["repos"][0], head=self.sh("rev-parse", "HEAD"))]
        for reported in (".claude-plugin/marketplace.json", f"0-{self.repo.name}/.claude-plugin/marketplace.json", "./.claude-plugin/marketplace.json"):
            with self.subTest(path=reported):
                s = pr.bind_subjects([dict(BLOCKING["findings"][0], file=reported, line=1)], repos)["F1"]
                self.assertTrue(s["bound"], f"{reported} must bind")
                self.assertEqual(s["path"], ".claude-plugin/marketplace.json")

    def test_f2_a_missing_round_record_is_not_a_verified_review(self):
        """The state claimed a round ran; its record was gone; the verifier examined no
        findings and reported success. That is the failure this command is for."""
        _, d = self.reviewed()
        (d / "round-1.json").unlink()
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "incomplete_record")
        self.assertTrue(any("round 1 record exists" in c["link"] and not c["ok"] for c in report["checks"]))

    def test_f2_a_round_carrying_only_an_outcome_does_not_verify(self):
        """The first repair caught a wholly missing round. A record with an outcome and
        nothing else still contributed no checks and verified by being empty, which is
        the same defect one layer in."""
        _, d = self.reviewed()
        pr.save(d, "round-1.json", {"round": 1, "outcome": "no_blocking_findings"})
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "incomplete_record")
        self.assertTrue(any("record is complete" in c["link"] and not c["ok"] for c in report["checks"]))

    def test_f2_a_round_whose_acceptance_drops_a_criterion_does_not_verify(self):
        _, d = self.reviewed()
        rec = pr.load(d, "round-1.json"); rec["acceptance"] = []; pr.save(d, "round-1.json", rec)
        report = pr.verify_links(d)
        self.assertTrue(any("acceptance covers every criterion" in c["link"] and not c["ok"] for c in report["checks"]))

    def test_f2_a_round_that_failed_honestly_is_a_complete_record(self):
        """review_unavailable is a legitimate round with no findings. Demanding fields
        it cannot have would make the check cry wolf on every honest failure."""
        _, d = self.reviewed()
        pr.save(d, "round-1.json", {"round": 1, "outcome": "review_unavailable", "error": "codex CLI not installed on PATH"})
        report = pr.verify_links(d)
        self.assertTrue(any("record is complete" in c["link"] and c["ok"] for c in report["checks"]))

    def test_f3_a_finding_repointed_away_from_its_subject_is_caught(self):
        """Verification re-hashed the subject's own stored path, which says nothing
        about the finding that cites it."""
        _, d = self.reviewed()
        rec = pr.load(d, "round-1.json")
        rec["findings"][0]["file"] = "nonexistent.py"; rec["findings"][0]["line"] = 999999
        pr.save(d, "round-1.json", rec)
        report = pr.verify_links(d)
        self.assertEqual(report["outcome"], "stale_link")
        self.assertTrue(any("no longer names the subject" in c["detail"] for c in report["checks"] if not c["ok"]))

    def test_f4_a_blocker_resolved_in_a_later_round_still_needs_its_disposition(self):
        """Checking only the final round excused exactly the blockers that were acted on."""
        rid, d = self.reviewed()
        pr.cmd_disposition(self.ns(review_id=rid, items=["F1=fixed"]))
        self.write("def f(x):\n    return x + 1\n"); self.sh("commit", "-qam", "fix")
        clean = {"verdict": "no_blocking_findings",
                 "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
                 "findings": [], "blocker_resolutions": [{"id": "F1", "resolved": True, "evidence": "a.py:2"}]}
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "cat " + str(self.tmp / "reply.json")
        (self.tmp / "reply.json").write_text(json.dumps(clean))
        try:
            pr.cmd_round(self.ns(review_id=rid, head=[f"{self.repo}={self.sh('rev-parse', 'HEAD')}"]))
        finally:
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
        self.assertEqual(pr.verify_links(d)["outcome"], "links_verified")
        pr.save(d, "dispositions.json", {})
        report = pr.verify_links(d)
        self.assertTrue(any("disposition for blocking F1 (round 1)" in c["link"] and not c["ok"] for c in report["checks"]),
                        "the round-one blocker's disposition must still be required after a later round resolves it")
        self.assertNotEqual(report["outcome"], "links_verified")

    def test_f6_a_repository_path_with_spaces_produces_a_usable_observation(self):
        """Formatting a command string and splitting it apart again tore every path
        containing a space into pieces, and these repositories live under
        "MoxyWolf Shared Files"."""
        spaced = self.tmp / "repo with spaces"
        shutil.copytree(self.repo, spaced)
        head = subprocess.run(["git", "-C", str(spaced), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        obs = pr.human_observations({"repos": [{"path": str(spaced), "head": head}]}, [])
        self.assertTrue(obs[0]["supported"])
        self.assertIn("repo with spaces", obs[0]["command"])
        self.assertEqual(obs[0]["output_head"], head)

    def test_f6_an_observation_whose_command_failed_is_never_recorded_as_support(self):
        head = self.sh("rev-parse", "HEAD")
        with self.assertRaises(pr.ReviewError):
            pr.human_observations({"repos": [{"path": str(self.tmp / "not-a-repo"), "head": head}]}, [])
        obs = pr.human_observations({"repos": []}, ["the suite ran :: false"])
        self.assertFalse(obs[0]["supported"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
