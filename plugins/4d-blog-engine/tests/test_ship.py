"""BP-001 criteria 1 to 4: ship.py pushes, merges on green, pulls back and checks the live page.

Git runs against a local bare repository, so nothing here reaches GitHub. The pull-request calls go
through an injected `api` that serves fixtures and records what was asked (XE-019).

ponytail: stdlib unittest, tempdirs, real git.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ship  # noqa: E402


def sh(cwd, *cmd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Repos:
    """A bare 'origin' with main, and a clone of it."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.origin, self.clone = root / "origin.git", root / "clone"
        sh(root, "git", "init", "-q", "--bare", "-b", "main", str(self.origin))
        sh(root, "git", "clone", "-q", str(self.origin), str(self.clone))
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            sh(self.clone, "git", "config", k, v)
        self.commit("first")
        sh(self.clone, "git", "push", "-q", "origin", "HEAD:main")

    def commit(self, name):
        (self.clone / name).write_text(name)
        sh(self.clone, "git", "add", name)
        sh(self.clone, "git", "commit", "-qm", name)
        return sh(self.clone, "git", "rev-parse", "HEAD")


class FakeGitHub:
    """Serves the calls merge() makes, from fixture check-runs; merging advances origin's main."""

    def __init__(self, repos, runs_seq):
        self.repos, self.runs_seq, self.calls, self.pr = repos, list(runs_seq), [], None

    def __call__(self, method, path, data=None):
        self.calls.append((method, path, data))
        if method == "GET" and "/pulls?" in path:
            return [self.pr] if self.pr else []
        if method == "POST" and path.endswith("/pulls"):
            head = ship.remote_sha(self.repos.clone, data["head"])  # what GitHub sees: the pushed head
            self.pr = {"number": 7, "head": {"sha": head}}
            return self.pr
        if "/check-runs" in path:
            return {"check_runs": self.runs_seq.pop(0) if len(self.runs_seq) > 1 else self.runs_seq[0]}
        if method == "PUT" and path.endswith("/merge"):
            c = self.repos.clone
            sh(c, "git", "switch", "-q", "main")
            sh(c, "git", "merge", "-q", "--no-ff", "-m", "merge", data["sha"])
            sh(c, "git", "push", "-q", "origin", "main")
            sha = sh(c, "git", "rev-parse", "HEAD")
            sh(c, "git", "reset", "-q", "--hard", "HEAD~1")  # local lags until pull-back
            return {"merged": True, "sha": sha}
        raise AssertionError(f"unexpected call {method} {path}")


def run(name, status="completed", conclusion="success", i=1):
    return {"id": i, "name": name, "status": status, "conclusion": conclusion}


class Push(unittest.TestCase):
    def test_push_requires_remote_equals_local(self):
        r = Repos()
        sh(r.clone, "git", "switch", "-qc", "publish/x")
        head = r.commit("post")
        self.assertEqual(ship.push(r.clone, "publish/x"), head)
        self.assertEqual(ship.remote_sha(r.clone, "publish/x"), head)

    def test_cli_push_state_records_the_unprotected_publish(self):
        r = Repos()
        sh(r.clone, "git", "switch", "-qc", "publish/x")
        head = r.commit("post")
        with tempfile.TemporaryDirectory() as d:
            st = Path(d) / "state.md"
            st.write_text("---\nslug: s\n---\n")
            self.assertEqual(ship.main(["push", "--repo", str(r.clone), "--branch", "publish/x",
                                        "--state", str(st)]), 0)
            text = st.read_text()
        self.assertIn("published_pr: none\n", text)
        self.assertIn(f"published_merge: {head}\n", text)
        self.assertIn("live_verified_at: pending", text)

    def test_push_failure_is_a_refusal(self):
        r = Repos()
        with self.assertRaises(ship.Refusal):
            ship.push(r.clone, "no-such-branch")


class Merge(unittest.TestCase):
    def setUp(self):
        self.r = Repos()
        sh(self.r.clone, "git", "switch", "-qc", "publish/x")
        self.head = self.r.commit("post")
        ship.push(self.r.clone, "publish/x")

    def merge(self, gh, checks=("unit", "e2e"), deadline=5):
        return ship.merge(gh, self.r.clone, "o/r", "publish/x", "main", self.head, list(checks),
                          "t", "b", deadline=deadline, poll=0)

    def test_merges_pinned_on_green_and_pulls_back(self):
        gh = FakeGitHub(self.r, [[run("unit", "in_progress", None)],
                                 [run("unit"), run("e2e", i=2)]])
        n, sha = self.merge(gh)
        self.assertEqual(n, 7)
        put = [c for c in gh.calls if c[0] == "PUT"][0]
        self.assertEqual(put[2]["sha"], self.head)
        self.assertEqual(sh(self.r.clone, "git", "rev-parse", "HEAD"), sha)
        self.assertEqual(ship.remote_sha(self.r.clone, "main"), sha)

    def test_failed_check_refuses_and_never_merges(self):
        gh = FakeGitHub(self.r, [[run("unit"), run("e2e", conclusion="failure", i=2)]])
        with self.assertRaisesRegex(ship.Refusal, "e2e: failure"):
            self.merge(gh)
        self.assertFalse([c for c in gh.calls if c[0] == "PUT"])

    def test_check_that_never_appears_is_a_failure(self):
        gh = FakeGitHub(self.r, [[run("unit")]])
        with self.assertRaisesRegex(ship.Refusal, "e2e \\(never appeared\\)"):
            self.merge(gh, deadline=0)
        self.assertFalse([c for c in gh.calls if c[0] == "PUT"])

    def cli(self, gh, head):
        orig = ship.agent_api
        ship.agent_api = gh
        try:
            return ship.main(["merge", "--repo", str(self.r.clone), "--slug", "o/r", "--branch", "publish/x",
                              "--base", "main", "--head", head, "--checks", "unit,e2e", "--deadline", "0"])
        finally:
            ship.agent_api = orig

    def test_cli_merges_the_head_it_was_given_not_the_moved_branch(self):
        self.r.commit("after-push")  # local branch moves; origin still has the pushed head
        gh = FakeGitHub(self.r, [[run("unit"), run("e2e", i=2)]])
        self.assertEqual(self.cli(gh, self.head), 0)
        put = [c for c in gh.calls if c[0] == "PUT"][0]
        self.assertEqual(put[2]["sha"], self.head)
        self.assertIn("check-runs", [c for c in gh.calls if "check-runs" in c[1]][0][1])
        self.assertIn(self.head, [c for c in gh.calls if "check-runs" in c[1]][0][1])

    def test_cli_refuses_a_head_the_pull_request_does_not_carry(self):
        moved = self.r.commit("after-push")
        gh = FakeGitHub(self.r, [[run("unit"), run("e2e", i=2)]])
        self.assertEqual(self.cli(gh, moved), 1)
        self.assertFalse([c for c in gh.calls if c[0] == "PUT"])

    def test_protected_republish_with_a_failing_check_keeps_the_previous_record(self):
        prior = "---\nslug: s\npublished_pr: 88\npublished_merge: abc\nlive_verified_at: 2026-10-16T00:00:00Z\n---\n"
        with tempfile.TemporaryDirectory() as d:
            st = Path(d) / "state.md"
            st.write_text(prior)
            gh = FakeGitHub(self.r, [[run("unit"), run("e2e", conclusion="failure", i=2)]])
            orig = ship.agent_api
            ship.agent_api = gh
            try:
                rc = ship.main(["merge", "--repo", str(self.r.clone), "--slug", "o/r", "--branch", "publish/x",
                                "--base", "main", "--head", self.head, "--checks", "unit,e2e",
                                "--deadline", "0", "--state", str(st)])
            finally:
                ship.agent_api = orig
            self.assertEqual(rc, 1)
            self.assertEqual(st.read_text(), prior)

    def test_cli_requires_head(self):
        with self.assertRaises(SystemExit) as e:
            ship.main(["merge", "--repo", "r", "--slug", "o/r", "--branch", "b", "--base", "main",
                       "--checks", "unit"])
        self.assertEqual(e.exception.code, 2)

    def test_latest_run_of_a_check_wins(self):
        gh = FakeGitHub(self.r, [[run("unit", conclusion="failure", i=1), run("unit", i=3), run("e2e", i=2)]])
        self.merge(gh)


PAGE = '<p>The structure I use is an <a href="/series/permission-engineering">auditable decision record</a>.</p>'


class VerifyLive(unittest.TestCase):
    def test_linked(self):
        ship.verify_live("u", "/series/permission-engineering", "Auditable decision record",
                         deadline=0, get=lambda u: (200, PAGE))

    def test_absolute_href_counts(self):
        ship.verify_live("u", "/series/permission-engineering", "auditable decision record", deadline=0,
                         get=lambda u: (200, PAGE.replace('"/series', '"https://opencontrols.ai/series')))

    def test_unlinked_is_hub_link_missing(self):
        with self.assertRaisesRegex(ship.Refusal, "hub_link_missing"):
            ship.verify_live("u", "/series/permission-engineering", "auditable decision record", deadline=0,
                             get=lambda u: (200, "<p>auditable decision record</p>"))

    def test_link_on_other_text_is_hub_link_missing(self):
        with self.assertRaisesRegex(ship.Refusal, "hub_link_missing"):
            ship.verify_live("u", "/series/permission-engineering", "auditable decision record", deadline=0,
                             get=lambda u: (200, '<a href="/series/permission-engineering">Read the series</a>'))

    def test_whitespace_and_case_still_count(self):
        ship.verify_live("u", "/series/permission-engineering", "auditable decision record", deadline=0,
                         get=lambda u: (200, PAGE.replace("auditable decision record",
                                                          "Auditable\n  decision RECORD")))

    def test_extra_trailing_character_is_hub_link_missing(self):
        for text in ("auditable decision records", "auditable decision record."):
            with self.assertRaisesRegex(ship.Refusal, "hub_link_missing"):
                ship.verify_live("u", "/series/permission-engineering", "auditable decision record", deadline=0,
                                 get=lambda u: (200, PAGE.replace("auditable decision record", text)))

    def test_term_only_inside_longer_anchor_text_is_hub_link_missing(self):
        with self.assertRaisesRegex(ship.Refusal, "hub_link_missing"):
            ship.verify_live("u", "/series/permission-engineering", "auditable decision record", deadline=0,
                             get=lambda u: (200, '<a href="/series/permission-engineering">'
                                                 'an auditable decision record format</a>'))

    def test_404_is_not_live(self):
        with self.assertRaisesRegex(ship.Refusal, "not_live"):
            ship.verify_live("u", "/series/x", "t", deadline=0, get=lambda u: (404, ""))

    def test_waits_for_the_deploy(self):
        answers = [(404, ""), (200, PAGE)]
        ship.verify_live("u", "/series/permission-engineering", "auditable decision record",
                         deadline=5, poll=0, get=lambda u: answers.pop(0))


class State(unittest.TestCase):
    def test_sets_and_adds_fields(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.md"
            p.write_text("---\nslug: s\npublished_pr: 1\n---\n\n# body\n")
            ship.set_state(p, {"published_pr": 88, "live_verified_at": "2026-10-16T00:00:00Z"})
            text = p.read_text()
            self.assertIn("published_pr: 88\n", text)
            self.assertIn("live_verified_at: 2026-10-16T00:00:00Z\n---\n", text)
            self.assertTrue(text.endswith("# body\n"))


if __name__ == "__main__":
    unittest.main()
