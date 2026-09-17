"""Exercise the real peer-review CLI and Git snapshots with controlled CLI responses."""
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("peer_review.py")

class GovernedReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", "/dev/null")
        (self.repo / "value.txt").write_text("before")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        (self.repo / "value.txt").write_text("after")
        self.git("commit", "-qam", "change")
        self.head = self.git("rev-parse", "HEAD")
        self.packet = {"outcome": "change value", "acceptance_criteria": ["value is after"],
                       "repos": [{"path": str(self.repo), "base": self.base, "head": self.head}],
                       "changed_behavior": "new value", "exclusions": [],
                       "tests": {"commands": ["read value.txt"], "results": "after", "environment": "fixture"},
                       "release_owner": "dorianatmoxywolf"}
        self.packet["data_use"] = {"owner":"dorianatmoxywolf", "classification":"test", "allow_repository":True, "allow_history":True, "allowed_tools":["claude","codex"]}
        self.packet_file = self.root / "input.json"
        self.env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(self.root / "reviews"), PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("GSTACK_PEER_REVIEW_SESSION", None)
        self.env.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
        binary = self.root / "bin"
        binary.mkdir()
        reviewer = binary / "codex"
        reviewer.write_text("#!" + sys.executable + "\nimport os,sys,pathlib\nassert (pathlib.Path.cwd()/'changed'/'0-repo'/'value.txt').read_text() in ('after','fixed')\np=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]);p.write_text(os.environ['REVIEW_RESPONSE'])\nprint('model: gpt-6-astra',file=sys.stderr)\n")
        reviewer.chmod(0o755)
        self.env["PATH"] = str(binary) + os.pathsep + os.environ["PATH"]

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def call(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=self.env, capture_output=True, text=True)

    def open(self):
        self.packet_file.write_text(json.dumps(self.packet))
        r = self.call("open", "--builder", "claude", "--packet", str(self.packet_file))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.rid = json.loads(r.stdout)["review_id"]

    def response(self, **changes):
        out = {"verdict": "no_blocking_findings", "acceptance": [{"criterion": "value is after", "met": True, "evidence": "value.txt:1"}],
               "findings": [], "regressions_from_fixes": [], "blocker_resolutions": [], "notes": ""}
        out.update(changes)
        self.env["REVIEW_RESPONSE"] = json.dumps(out)

    def round(self, *args):
        r = self.call("round", self.rid, *args)
        return r, json.loads(r.stdout) if r.stdout.startswith("{") else {}

    def test_missing_review_state_cannot_report_success(self):
        self.open()
        (self.root / "reviews" / self.rid / "state.json").write_text("{}")
        r = self.call("release", self.rid)
        self.assertNotEqual(r.returncode, 0)

    def test_peer_dispatch_requires_data_permission(self):
        self.open(); self.response()
        packet = self.root / "reviews" / self.rid / "packet.json"
        value=json.loads(packet.read_text());value.pop("data_use",None);packet.write_text(json.dumps(value))
        r, out=self.round()
        self.assertNotEqual(r.returncode,0)
        self.assertIn("data_use",r.stdout+r.stderr)

    def test_repeated_release_preserves_original_handoff(self):
        self.open();self.response();self.round()
        self.call("release",self.rid)
        path=self.root / "reviews" / self.rid / "release.json"
        first=path.stat().st_mtime_ns
        self.call("release",self.rid)
        self.assertEqual(first,path.stat().st_mtime_ns)

    def test_complete_evidence_passes(self):
        self.open(); self.response()
        r, out = self.round()
        self.assertEqual(out.get("outcome"), "no_blocking_findings", r.stderr)
        self.assertEqual(r.returncode, 0)

    def test_incomplete_or_contradictory_evidence_cannot_pass(self):
        cases = [[], [{"criterion": "value is after", "met": False, "evidence": "missing"}],
                 [{"criterion": "unrequested", "met": True, "evidence": "value.txt:1"}],
                 [{"criterion": "value is after", "met": "true", "evidence": "value.txt:1"}],
                 [{"criterion": "value is after", "met": True, "evidence": " "}],
                 [{"criterion": "value is after", "met": True, "evidence": "x"}]*2]
        for acceptance in cases:
            with self.subTest(acceptance=acceptance):
                self.open(); self.response(acceptance=acceptance)
                r, out = self.round()
                self.assertNotIn(out.get("outcome"), ("no_blocking_findings", "fixes_verified"))
                self.assertNotEqual(r.returncode, 0)

    def test_empty_or_duplicate_contract_is_refused(self):
        for criteria in [[], ["value is after"]*2, [" "]]:
            with self.subTest(criteria=criteria):
                self.packet["acceptance_criteria"] = criteria
                self.packet_file.write_text(json.dumps(self.packet))
                r = self.call("open", "--builder", "claude", "--packet", str(self.packet_file))
                self.assertNotEqual(r.returncode, 0)

    def test_missing_owner_is_refused(self):
        del self.packet["release_owner"]
        self.packet_file.write_text(json.dumps(self.packet))
        r = self.call("open", "--builder", "claude", "--packet", str(self.packet_file))
        self.assertNotEqual(r.returncode, 0)

    def blocking_round(self):
        self.open()
        self.response(verdict="blocking_findings", findings=[{"id":"F1", "severity":"blocking", "file":"value.txt", "line":1,
                      "what":"bad value", "evidence":"value.txt:1", "criterion":"value is after", "fix":"fix value"}])
        _, out = self.round()
        self.assertEqual(out.get("outcome"), "blocking_findings")
        (self.repo / "value.txt").write_text("fixed")
        self.git("commit", "-qam", "fix")
        return self.git("rev-parse", "HEAD")

    def test_dropped_blocker_is_not_verified(self):
        head = self.blocking_round()
        self.assertEqual(self.call("disposition", self.rid, "F1=fixed").returncode, 0)
        self.response()
        r, out = self.round("--head", str(self.repo)+"="+head)
        self.assertNotEqual(out.get("outcome"), "fixes_verified")
        self.assertNotEqual(r.returncode, 0)

    def test_explicit_fix_resolution_passes(self):
        head = self.blocking_round()
        self.call("disposition", self.rid, "F1=fixed")
        self.response(blocker_resolutions=[{"id":"F1", "resolved":True, "evidence":"value.txt:1 fixed"}])
        r, out = self.round("--head", str(self.repo)+"="+head)
        self.assertEqual(out.get("outcome"), "fixes_verified", r.stderr)

    def test_unapproved_blocker_deferral_is_refused(self):
        self.blocking_round()
        r = self.call("disposition", self.rid, "F1=deferred")
        self.assertNotEqual(r.returncode, 0)

    def test_unknown_disposition_and_empty_disproof_are_refused(self):
        self.blocking_round()
        for value in ["F99=fixed", "F1=disproved"]:
            with self.subTest(value=value):
                self.assertNotEqual(self.call("disposition", self.rid, value).returncode, 0)

    def test_blocking_review_cannot_prepare_release(self):
        self.blocking_round()
        r = self.call("release", self.rid)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("release_blocked", r.stderr)
        self.assertFalse((self.root / "reviews" / self.rid / "release.json").exists())

    def test_release_entry_never_merges_without_human(self):
        self.open(); self.response(); self.round()
        before = self.git("rev-parse", "HEAD")
        r = self.call("release", self.rid)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("human", (r.stdout+r.stderr).lower())
        self.assertEqual(before, self.git("rev-parse", "HEAD"))

    def test_release_refuses_stale_revision(self):
        self.open(); self.response(); self.round()
        (self.repo / "value.txt").write_text("unreviewed")
        self.git("commit", "-qam", "unreviewed")
        r = self.call("release", self.rid)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stale", (r.stdout+r.stderr).lower())

    def test_disproved_blocker_can_prepare_release_without_new_commits(self):
        self.open()
        self.response(verdict="blocking_findings", findings=[{"id":"F1", "severity":"blocking", "file":"value.txt", "line":1,
                      "what":"suspected bug", "evidence":"value.txt:1", "criterion":"value is after", "fix":"investigate"}])
        self.round()
        self.call("disposition", self.rid, "F1=disproved:read value.txt; expected value is present")
        self.response(blocker_resolutions=[{"id":"F1", "resolved":True, "evidence":"value.txt:1; suspicion disproved"}])
        r, out = self.round()
        self.assertEqual(out.get("outcome"), "fixes_verified", r.stderr)
        r = self.call("release", self.rid)
        self.assertIn("awaiting_human_release", r.stdout+r.stderr)

    def test_regression_requires_a_tracked_blocking_finding(self):
        self.open(); self.response(regressions_from_fixes=["R1"])
        r, out = self.round()
        self.assertEqual(out.get("outcome"), "malformed_output", r.stderr)

    def test_environment_cannot_substitute_reviewer(self):
        self.open(); self.response(acceptance=[])
        self.env["GSTACK_PEER_REVIEW_FAKE_CMD"] = "echo '{\"verdict\":\"no_blocking_findings\",\"acceptance\":[{\"criterion\":\"value is after\",\"met\":true,\"evidence\":\"forged\"}],\"findings\":[],\"blocker_resolutions\":[]}'"
        r, out = self.round()
        self.assertNotEqual(out.get("outcome"), "no_blocking_findings")
        self.assertNotEqual(r.returncode, 0)

    def install_github_response(self, **changes):
        self.git("remote", "add", "origin", "https://github.com/example/project.git")
        record = {"merged": True, "head": {"sha": self.head}, "base": {"ref": "main", "repo": {"full_name": "example/project"}},
                  "merged_by": {"login": "dorianatmoxywolf", "type": "User"}, "merge_commit_sha": "a"*40,
                  "merged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "html_url": "https://github.com/example/project/pull/1"}
        record.update(changes)
        self.env["GITHUB_RESPONSE"] = json.dumps(record)
        gh = self.root / "bin" / "gh"
        gh.write_text("#!" + sys.executable + "\nimport os,sys\nassert sys.argv[1:]==['api','repos/example/project/pulls/1']\nprint(os.environ['GITHUB_RESPONSE'])\n")
        gh.chmod(0o755)

    def test_human_merge_is_recorded_from_github(self):
        self.open(); self.response(); self.round()
        self.call("release", self.rid)
        self.install_github_response()
        r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["approver"], "dorianatmoxywolf")
        self.assertEqual(result["head"], self.head)
        self.assertEqual(result["action"], "merge")

    def test_github_login_case_does_not_change_identity(self):
        self.open(); self.response(); self.round()
        self.call("release", self.rid)
        self.install_github_response(merged_by={"login": "DorianAtMoxyWolf", "type": "User"})
        r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_wrong_actor_or_revision_cannot_authorize_release(self):
        self.open(); self.response(); self.round()
        self.call("release", self.rid)
        self.install_github_response()
        baseline = json.loads(self.env["GITHUB_RESPONSE"])
        for change in [{"base":{"ref":"other", "repo":{"full_name":"example/project"}}}, {"merged_at":"2000-01-01T00:00:00Z"}, {"merged":False}, {"head":{"sha":"b"*40}},
                       {"merged_by":{"login":"other-human","type":"User"}},
                       {"merged_by":{"login":"dorianatmoxywolf","type":"Bot"}}]:
            with self.subTest(change=change):
                self.env["GITHUB_RESPONSE"] = json.dumps(dict(baseline, **change))
                r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
                self.assertNotEqual(r.returncode, 0)

if __name__ == "__main__":
    unittest.main()
