import pathlib
"""Exercise the real peer-review CLI and Git snapshots with controlled CLI responses."""
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import peer_review as peer
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("peer_review.py")


def load_pr():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pr_ga5", SCRIPT)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

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
        # XE-014: release refuses an unchecked review, so a fixture meant to release carries a scored report
        self.packet["coverage"] = {"status": "checked", "criteria": [{"item": "FX-001", "criterion_no": 1, "declared": "fixture", "probability": 0.9}]}
        self.packet["data_use"] = {"owner":"dorianatmoxywolf", "classification":"test", "allow_repository":True, "allow_history":True, "allowed_tools":["claude","codex"]}
        self.packet_file = self.root / "input.json"
        self.env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(self.root / "reviews"), PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("GSTACK_PEER_REVIEW_SESSION", None)
        self.env.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
        # XE-019: the caller's token would route record-release to the live API instead of the stubs
        self.env.pop("GITHUB_TOKEN", None)
        self.env.pop("GSTACK_GITHUB_API", None)
        binary = self.root / "bin"
        binary.mkdir()
        reviewer = binary / "codex"
        # XE-008: the layout comes from peer_review, not a hardcoded spelling. A copy of the
        # format in a fixture is one of the four homes that let it drift twice in an hour.
        prefix = peer.surface_prefix(0, self.packet['repos'][0], 'changed')
        reviewer.write_text('#!' + sys.executable + '\n' + f'PREFIX={prefix!r}\n' + "import os,sys,pathlib\nassert (pathlib.Path.cwd()/PREFIX/'value.txt').read_text() in ('after','fixed')\np=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1]);p.write_text(os.environ['REVIEW_RESPONSE'])\nprint('model: gpt-6-astra',file=sys.stderr)\nout=os.environ.get('REVIEWER_ENV_OUT')\nif out: pathlib.Path(out).write_text(' '.join(sorted(os.environ)))\n")
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

    def test_release_without_checked_coverage_is_refused_unless_the_owner_excepts_it(self):
        """XE-014.12: an open review with no coverage record releases only on an exception in the
        Release Owner's words, kept verbatim with its time, and the handoff leads with the status."""
        del self.packet["coverage"]
        self.open(); self.response(); self.round()
        r = self.call("release", self.rid)
        self.assertIn("release_blocked", r.stderr)
        self.assertIn("status: not_run", r.stderr)
        self.assertFalse((self.root / "reviews" / self.rid / "release.json").exists())
        words = "Scorer is down today; ship it. \u2014 D"
        r = self.call("release", self.rid, "--coverage-exception", words)
        self.assertIn("awaiting_human_release", r.stdout + r.stderr)
        self.assertEqual(r.stderr.splitlines()[0], f"coverage: not_run (exception: {words})")
        rec = json.loads((self.root / "reviews" / self.rid / "release.json").read_text())
        self.assertEqual(rec["coverage"]["exception"]["words"], words)
        self.assertRegex(rec["coverage"]["exception"]["recorded_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(next(iter(rec)), "coverage")

    def test_a_checked_review_releases_and_says_so_first(self):
        self.open(); self.response(); self.round()
        r = self.call("release", self.rid)
        self.assertIn("awaiting_human_release", r.stdout + r.stderr)
        self.assertEqual(r.stderr.splitlines()[0], "coverage: covered")

    def test_the_reviewer_never_receives_a_github_token(self):
        """XE-014.13: the dispatcher may hold the app token to read CI; the reviewer it starts may not."""
        out = self.root / "reviewer-env.txt"
        self.env.update(GITHUB_TOKEN="ghs_fixture", GH_TOKEN="gho_fixture", REVIEWER_ENV_OUT=str(out))
        self.open(); self.response()
        r, _ = self.round()
        seen = out.read_text().split()
        self.assertIn("REVIEWER_ENV_OUT", seen, r.stderr)   # the reviewer ran and recorded its env
        self.assertNotIn("GITHUB_TOKEN", seen)
        self.assertNotIn("GH_TOKEN", seen)

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
        gh.write_text("#!" + sys.executable + "\nimport os,sys\nargs=sys.argv[1:]\n"
                      "if args==['api','repos/example/project/pulls/1']: print(os.environ['GITHUB_RESPONSE'])\n"
                      "elif args==['api','repos/example/project/issues/1/comments?per_page=100']: print(os.environ.get('GITHUB_COMMENTS','[]'))\n"
                      "else: sys.exit('unexpected gh call: %r' % args)\n")
        gh.chmod(0o755)

    # GA-005: an agent merge is recorded as one, on an instruction the agent posted first.
    BOT = {"login": "moxywolf-agent[bot]", "type": "Bot"}

    def instruction_comment(self, covers=(1,), owner="dorianatmoxywolf", when="2000-01-01T00:00:00Z", by=None):
        pr = load_pr()
        return {"user": by or self.BOT, "created_at": when, "html_url": "https://github.com/example/project/pull/1#c1",
                "body": pr.merge_instruction_body("merge it", "2026-09-20T05:00:00Z", covers, owner)}

    def bot_merge(self, comments):
        self.open(); self.response(); self.round()
        self.call("release", self.rid)
        self.install_github_response(merged_by=self.BOT)
        self.env["GITHUB_COMMENTS"] = json.dumps(comments)
        return self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")

    def test_agent_merge_on_instruction_is_recorded_as_the_agents(self):
        r = self.bot_merge([self.instruction_comment()])
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertEqual(rec["outcome"], "agent_merge_on_instruction")
        self.assertEqual(rec["merged_by"], "moxywolf-agent[bot]")
        self.assertEqual(rec["instructed_by"], "dorianatmoxywolf")
        self.assertEqual(rec["instruction"], "merge it")
        self.assertEqual(rec["instruction_comment"], "https://github.com/example/project/pull/1#c1")

    def test_agent_merge_without_a_matching_instruction_is_recorded_as_autonomous(self):
        cases = {"no comment": [],
                 "covers another PR": [self.instruction_comment(covers=(2,))],
                 "another owner": [self.instruction_comment(owner="someone-else")],
                 "posted after the merge": [self.instruction_comment(when="2999-01-01T00:00:00Z")],
                 "posted by a person, not the merging bot": [self.instruction_comment(by={"login": "x", "type": "User"})],
                 "unparseable marker": [{"user": self.BOT, "created_at": "2000-01-01T00:00:00Z", "body": "<!-- gstack-merge-instruction: {nope -->"}]}
        for name, comments in cases.items():
            with self.subTest(name):
                self.setUp()
                r = self.bot_merge(comments)
                self.assertEqual(r.returncode, 0, r.stderr)
                rec = json.loads(r.stdout)
                self.assertEqual(rec["outcome"], "agent_merge_autonomous")
                self.assertEqual(rec["authorized_by"], "dorianatmoxywolf")
                self.assertIn("DR-113", rec["authority"])
                self.assertNotIn("instruction", rec)

    def test_a_goal_item_released_to_its_goal_branch_records_that_merge(self):  # GO-003 review F6
        self.open(); self.response(); self.round()
        self.call("release", self.rid, "--target", "goal/g1")
        self.install_github_response(merged_by=self.BOT, base={"ref": "goal/g1", "repo": {"full_name": "example/project"}})
        self.env["GITHUB_COMMENTS"] = "[]"
        r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["outcome"], "agent_merge_autonomous")

    def test_a_goal_item_released_to_main_cannot_record_a_goal_branch_merge(self):  # GO-003 review F6
        self.open(); self.response(); self.round()
        self.call("release", self.rid)                                           # target defaults to main
        self.install_github_response(merged_by=self.BOT, base={"ref": "goal/g1", "repo": {"full_name": "example/project"}})
        self.env["GITHUB_COMMENTS"] = "[]"
        r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
        self.assertNotEqual(r.returncode, 0)

    def test_an_autonomous_merge_before_the_handoff_is_still_refused(self):
        # GA-009: DR-113 removes the instruction, not the review or the handoff.
        self.open(); self.response(); self.round()
        self.call("release", self.rid)
        self.install_github_response(merged_by=self.BOT, merged_at="2000-01-01T00:00:00Z")
        r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("merge predates the release handoff", r.stderr)

    def test_the_instruction_the_producer_writes_is_the_one_the_recorder_reads(self):
        pr = load_pr()
        body = pr.merge_instruction_body("merge #1 and #3\nplease", "2026-09-20T05:00:00Z", [3, 1, 1], "dorian")
        self.assertIn("> merge #1 and #3", body)
        self.assertEqual(pr.parse_merge_instruction(body),
                         {"instruction": "merge #1 and #3\nplease", "given_at": "2026-09-20T05:00:00Z", "covers": [1, 3], "instructed_by": "dorian"})
        r = self.call("merge-instruction", "--covers", "#1, 3", "--text", "merge it", "--given-at", "t", "--owner", "dorian")
        self.assertEqual(pr.parse_merge_instruction(json.loads(r.stdout)["body"])["covers"], [1, 3])

    def test_record_release_reads_github_over_rest_with_the_app_token_when_gh_is_absent(self):
        import http.server, threading
        self.open(); self.response(); self.round()
        self.call("release", self.rid)
        self.install_github_response()
        (self.root / "bin" / "gh").unlink()
        record, seen = self.env.pop("GITHUB_RESPONSE"), []

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(h):
                seen.append((h.path, h.headers.get("Authorization")))
                raw = record.encode(); h.send_response(200); h.send_header("Content-Length", str(len(raw))); h.end_headers(); h.wfile.write(raw)
            def log_message(h, *a): pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close); self.addCleanup(srv.shutdown)
        self.env.update(GITHUB_TOKEN="ghs_fixture", GSTACK_GITHUB_API=f"http://127.0.0.1:{srv.server_port}")
        r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["outcome"], "human_merge_recorded")
        self.assertEqual(seen, [("/repos/example/project/pulls/1", "token ghs_fixture")])

    def test_a_callers_github_token_does_not_reach_the_record(self):
        # XE-019 criterion 2: a shell exporting a token GitHub would refuse, and an API URL nothing
        # answers on, must not route record-release away from the stub. Proven in CI on every run.
        from unittest import mock
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "ghs_refused", "GSTACK_GITHUB_API": "http://127.0.0.1:9"}):
            self.setUp()
        self.assertNotIn("GITHUB_TOKEN", self.env)
        self.test_human_merge_is_recorded_from_github()

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
                       {"merged_by":{"login":"dorianatmoxywolf","type":"Bot"}},
                       {"merged_by":{"login":"some-other-app[bot]","type":"Bot"}}]:
            with self.subTest(change=change):
                self.env["GITHUB_RESPONSE"] = json.dumps(dict(baseline, **change))
                r = self.call("record-release", self.rid, "--repo", str(self.repo), "--pr", "1")
                self.assertNotEqual(r.returncode, 0)


class ReleaseLanes(GovernedReview):
    """GA-010: the lane is decided by what the change touches, by code, at the reviewed head."""

    def commit_change(self, rel, text="x\n", delete=False, rename_to=None):
        """One more commit on top of the fixture head, returning the new head; the packet follows."""
        p = self.repo / rel
        if delete:
            self.git("rm", "-q", rel)
        elif rename_to:
            (self.repo / rename_to).parent.mkdir(parents=True, exist_ok=True)
            self.git("mv", rel, rename_to)
        else:
            p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text); self.git("add", rel)
        self.git("commit", "-qm", f"touch {rel}")
        self.head = self.git("rev-parse", "HEAD")
        self.packet["repos"][0]["head"] = self.head
        return self.head

    def lane(self):
        return peer.release_lane(self.packet["repos"])

    def test_the_fixture_change_is_contained(self):
        L = self.lane()
        self.assertEqual((L["lane"], L["decided_by"], L["matched"], L["table"]), ("contained", ["none"], [], "default"))

    def test_a_migration_path_is_closed_by_path(self):
        self.commit_change("db/migrations/0001_init.sql", "create table t(x int);\n")
        L = self.lane()
        self.assertEqual((L["lane"], L["decided_by"]), ("closed", ["path"]))
        self.assertEqual([m["path"] for m in L["matched"]], ["db/migrations/0001_init.sql"])

    def test_a_deleted_tracked_file_is_closed_by_effect(self):
        self.commit_change("value.txt", delete=True)
        L = self.lane()
        self.assertEqual((L["lane"], L["decided_by"]), ("closed", ["effect"]))
        self.assertEqual(L["matched"][0]["effect"], "deletes_tracked_file")

    def test_a_shared_script_is_wide_and_a_rename_is_wide(self):
        self.commit_change("scripts/helper.py", "def h(): pass\n")
        self.assertEqual(self.lane()["lane"], "wide")
        self.base = self.head; self.packet["repos"][0]["base"] = self.base   # the rename is base..head, not a later add
        self.commit_change("scripts/helper.py", rename_to="scripts/helper2.py")
        L = self.lane()
        self.assertEqual(L["lane"], "wide")
        self.assertIn("renames_tracked_file", [m.get("effect") for m in L["matched"]])

    def test_a_file_many_callers_name_is_wide_by_effect(self):
        for i in range(6):
            (self.repo / f"caller{i}.py").write_text("import widget\n")
        self.git("add", "."); self.git("commit", "-qm", "callers")
        self.base = self.git("rev-parse", "HEAD"); self.packet["repos"][0]["base"] = self.base
        self.commit_change("widget.py", "VALUE = 2\n")
        L = self.lane()
        self.assertEqual(L["lane"], "wide")
        self.assertEqual([m["effect"] for m in L["matched"]], ["many_callers"])
        (self.repo / "caller5.py").unlink(); self.git("add", "."); self.git("commit", "-qm", "five callers")
        self.base = self.git("rev-parse", "HEAD"); self.packet["repos"][0]["base"] = self.base
        self.commit_change("widget.py", "VALUE = 3\n")
        self.assertEqual(self.lane()["lane"], "contained")   # exactly five is not more than five

    def test_the_most_restrictive_lane_wins(self):
        self.commit_change("scripts/helper.py", "x = 1\n")
        self.commit_change("db/migrations/0002.sql", "alter table t add y int;\n")
        self.assertEqual(self.lane()["lane"], "closed")

    def test_a_repository_table_replaces_the_default_whole(self):
        self.commit_change(".gstack/release-lanes.json", json.dumps({"lanes": {"closed": {"paths": ["docs/**"], "effects": []}, "wide": {"paths": [], "effects": []}}}))
        self.commit_change("db/migrations/0003.sql", "x\n")   # closed by the default table, nothing by this one
        self.commit_change("docs/a.md", "# a\n")
        L = self.lane()
        self.assertEqual((L["lane"], [m["path"] for m in L["matched"]]), ("closed", ["docs/a.md"]))
        self.assertTrue(L["table"].endswith(".gstack/release-lanes.json@" + self.head[:7]), L["table"])

    def test_a_readme_only_change_is_contained(self):
        self.base = self.head; self.packet["repos"][0]["base"] = self.base
        self.commit_change("README.md", "# fixture\n")
        L = self.lane()
        self.assertEqual((L["lane"], L["matched"]), ("contained", []))

    def test_a_migration_renamed_out_of_its_folder_is_still_closed(self):
        # F1 (review 20261013-202943): a rename touches its source too
        self.commit_change("db/migrations/0001.sql", "x\n")
        self.base = self.head; self.packet["repos"][0]["base"] = self.base
        self.commit_change("db/migrations/0001.sql", rename_to="archive/0001.sql")
        L = self.lane()
        self.assertEqual(L["lane"], "closed")
        self.assertIn("db/migrations/0001.sql", [m["path"] for m in L["matched"]])

    def test_each_repository_is_judged_by_its_own_table(self):
        # F3 (review 20261013-202943): A's permissive table must not cover B's docs change
        other = self.root / "other"; other.mkdir()
        g = lambda *a: subprocess.run(["git", "-C", str(other), *a], check=True, capture_output=True, text=True).stdout.strip()
        g("init", "-q"); g("config", "user.name", "F"); g("config", "user.email", "f@x"); g("config", "core.hooksPath", "/dev/null")
        (other / ".gstack").mkdir(); (other / ".gstack" / "release-lanes.json").write_text(json.dumps({"lanes": {"closed": {"paths": ["docs/**"], "effects": []}, "wide": {"paths": [], "effects": []}}}))
        (other / "a.txt").write_text("a"); g("add", "."); g("commit", "-qm", "base"); obase = g("rev-parse", "HEAD")
        (other / "docs").mkdir(); (other / "docs" / "x.md").write_text("x"); g("add", "."); g("commit", "-qm", "docs"); ohead = g("rev-parse", "HEAD")
        self.commit_change(".gstack/release-lanes.json", json.dumps({"lanes": {"closed": {"paths": [], "effects": []}, "wide": {"paths": [], "effects": []}}}))
        self.commit_change("db/migrations/0009.sql", "x\n")      # permissive table: nothing closes here
        self.packet["repos"].append({"path": str(other), "base": obase, "head": ohead})
        L = self.lane()
        self.assertEqual(L["lane"], "closed")
        self.assertEqual([(m["repo"], m["path"]) for m in L["matched"]], [("other", "docs/x.md")])
        self.assertEqual(len(L["table"]), 2)
        self.packet["repos"].reverse()
        self.assertEqual(self.lane()["lane"], "closed")           # order does not change the lane

    def test_an_error_round_still_carries_the_lane(self):
        # F5 (review 20261013-202943)
        self.commit_change("db/migrations/0010.sql", "x\n")
        self.open()
        self.env["REVIEW_RESPONSE"] = "not json at all"
        r, out = self.round()
        self.assertNotEqual(r.returncode, 0)
        rec = json.loads((self.root / "reviews" / self.rid / "round-1.json").read_text())
        self.assertEqual(rec["release_lane"]["lane"], "closed")

    def test_a_wide_release_is_refused_when_its_gates_do_not_hold(self):
        # F2 (review 20261013-202943, then 20261013-204622): the wide instruction is earned, not
        # claimed, and the ledger is read at release time: a check that fails after open counts
        self.commit_change("scripts/helper.py", "x = 1\n")
        self.open(); self.response(); self.round()
        ledger = Path(__file__).with_name("check_ledger.py")
        check = [sys.executable, str(ledger), "run", "--repo", str(self.repo), "--", "test", "-f", "ok"]   # same check fails, then passes
        r = subprocess.run(check, env=self.env, capture_output=True, text=True, cwd=str(self.repo))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        r = self.call("release", self.rid)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("release_blocked", r.stdout + r.stderr); self.assertIn("open failure", r.stdout + r.stderr)
        self.assertFalse((self.root / "reviews" / self.rid / "release.json").exists())
        # the same check passing clears it, and the release goes through
        (self.repo / "ok").write_text("")
        r = subprocess.run(check, env=self.env, capture_output=True, text=True, cwd=str(self.repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        (self.repo / "ok").unlink()                       # release wants a clean worktree
        r = self.call("release", self.rid)
        self.assertTrue((self.root / "reviews" / self.rid / "release.json").exists(), r.stdout + r.stderr)

    def test_a_quoted_pathname_still_matches_its_closed_glob(self):
        # F1 (review 20261013-204622): a non-ASCII workflow name is quoted by git without -z
        self.commit_change(".github/workflows/d\u00e9ploiement.yml", "on: push\n")
        L = self.lane()
        self.assertEqual(L["lane"], "closed")
        self.assertEqual([m["path"] for m in L["matched"]], [".github/workflows/d\u00e9ploiement.yml"])

    def test_an_unreadable_diff_is_refused_not_contained(self):
        self.packet["repos"][0]["head"] = "0" * 40
        with self.assertRaises(peer.ReviewError) as cm:
            self.lane()
        self.assertEqual(cm.exception.outcome, "malformed_packet")

    def test_open_records_the_lane_and_the_reviewer_cannot_move_it(self):
        self.commit_change("db/migrations/0004.sql", "x\n")
        self.open()
        state = json.loads((self.root / "reviews" / self.rid / "state.json").read_text())
        self.assertEqual(state["release_lane"]["lane"], "closed")
        self.response(release_lane={"lane": "contained"})      # a reviewer key, whatever validate does with it
        r, out = self.round()
        state = json.loads((self.root / "reviews" / self.rid / "state.json").read_text())
        self.assertEqual(state["release_lane"]["lane"], "closed")
        if r.returncode != 0:                                     # the key was refused as malformed; a clean round follows
            self.response(); r, out = self.round()
            self.assertEqual(r.returncode, 0, r.stderr)
        rounds = sorted((self.root / "reviews" / self.rid).glob("round-*.json"))
        rec = json.loads(rounds[-1].read_text())
        self.assertEqual(rec["release_lane"]["lane"], "closed")

    def test_release_on_a_closed_lane_says_dr113_does_not_apply(self):
        self.commit_change("db/migrations/0005.sql", "x\n")
        self.open(); self.response(); self.round()
        r = self.call("release", self.rid)
        rec = json.loads((self.root / "reviews" / self.rid / "release.json").read_text())
        self.assertEqual(rec["outcome"], "awaiting_human_release")
        self.assertEqual(rec["release_lane"]["lane"], "closed")
        self.assertIn("DR-113 does not apply", rec["instruction"])
        self.assertIn("does not merge", rec["instruction"])
        self.assertIn("closed by repo: db/migrations/0005.sql", rec["instruction"])   # F6: names what matched

    def test_release_on_a_wide_lane_names_its_gates(self):
        self.commit_change("scripts/helper.py", "x = 1\n")
        self.open(); self.response(); self.round()
        self.call("release", self.rid)
        rec = json.loads((self.root / "reviews" / self.rid / "release.json").read_text())
        self.assertEqual(rec["release_lane"]["lane"], "wide")
        self.assertIn("lane is wide", rec["instruction"])

    def test_an_autonomous_agent_merge_of_a_closed_lane_is_recorded_out_of_lane(self):
        self.commit_change("db/migrations/0006.sql", "x\n")
        r = self.bot_merge([])
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertEqual(rec["outcome"], "agent_merge_out_of_lane")
        self.assertEqual(rec["lane"], "closed")
        self.assertEqual([m["path"] for m in rec["matched"]], ["db/migrations/0006.sql"])
        self.assertNotIn("authority", rec); self.assertNotIn("authorized_by", rec)
        self.assertEqual(rec["release_lane"]["lane"], "closed")

    def test_an_instructed_agent_merge_of_a_closed_lane_is_on_instruction_and_carries_the_lane(self):
        self.commit_change("db/migrations/0007.sql", "x\n")
        r = self.bot_merge([self.instruction_comment()])
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertEqual((rec["outcome"], rec["release_lane"]["lane"]), ("agent_merge_on_instruction", "closed"))

    def test_an_autonomous_merge_of_a_contained_lane_is_still_autonomous(self):
        r = self.bot_merge([])
        rec = json.loads(r.stdout)
        self.assertEqual((rec["outcome"], rec["release_lane"]["lane"]), ("agent_merge_autonomous", "contained"))


# ReleaseLanes borrows GovernedReview's fixture, not its tests
for _name in [n for n in vars(GovernedReview) if n.startswith("test_")]:
    setattr(ReleaseLanes, _name, None)


class ReviewRootIsDeclared(unittest.TestCase):
    """EV-009. The old default wrote records to a session-local home, so the record was
    gone and the review ID in the design document still read like evidence."""

    def run_open(self, env_dir):
        env = {k: v for k, v in os.environ.items() if k != "GSTACK_PEER_REVIEW_DIR"}
        if env_dir:
            env["GSTACK_PEER_REVIEW_DIR"] = str(env_dir)
        return subprocess.run([sys.executable, str(SCRIPT), "open", "--help"],
                              capture_output=True, text=True, env=env)

    def test_unset_review_dir_is_named_in_the_error_rather_than_defaulted(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pr_ev9", SCRIPT)
        pr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pr)
        pr.REVIEW_DIR = None
        with self.assertRaises(SystemExit) as e:
            pr.review_root()
        self.assertIn("GSTACK_PEER_REVIEW_DIR", str(e.exception))
        self.assertIn("outlives this session", str(e.exception))

    def test_a_declared_directory_is_used_as_given(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pr_ev9b", SCRIPT)
        pr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pr)
        pr.REVIEW_DIR = pathlib.Path("/tmp/declared-review-root")
        self.assertEqual(pr.review_root(), pathlib.Path("/tmp/declared-review-root"))

    def test_no_code_path_falls_back_to_the_home_directory(self):
        """The defect was a default, so the test is about the source, not one call."""
        src = SCRIPT.read_text()
        self.assertNotIn('Path.home() / ".gstack"', src)
        self.assertNotIn("Path.home()/'.gstack'", src)

if __name__ == "__main__":
    unittest.main()
