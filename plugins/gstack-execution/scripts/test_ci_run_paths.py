#!/usr/bin/env python3
"""XE-020: a CI run is named by the same path its repository is, and one naming no repository
refuses at open. The case is review 20260924-162903-25a6677-7hrcgdnp: the packet named /tmp/xe019,
the repository resolved to /private/tmp/xe019, and the CI evidence read nothing."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr


class CiRunPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="xe020-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.real = self.tmp / "real" / "app"; self.real.mkdir(parents=True)
        self.alias = self.tmp / "alias"                       # /tmp -> /private/tmp, in miniature
        self.alias.symlink_to(self.tmp / "real", target_is_directory=True)
        self.via_alias = str(self.alias / "app")

    def packet(self, repo):
        return {"repos": [{"path": str(self.real.resolve())}], "tests": {"ci_runs": [{"repo": repo, "run_id": 7}]}}

    def test_an_aliased_path_resolves_and_matches(self):
        p = pr.resolve_ci_runs(self.packet(self.via_alias))
        self.assertEqual(p["tests"]["ci_runs"][0]["repo"], str(self.real.resolve()))

    def test_a_directory_name_still_matches(self):
        self.assertEqual(pr.resolve_ci_runs(self.packet("app"))["tests"]["ci_runs"][0]["repo"], "app")

    def test_a_run_naming_no_repository_refuses_by_name(self):
        with self.assertRaises(pr.ReviewError) as c:
            pr.resolve_ci_runs(self.packet(str(self.tmp / "elsewhere")))
        self.assertIn("not a repository in this packet", str(c.exception))
        self.assertIn("elsewhere", str(c.exception))

    def test_ci_run_flag_resolves_the_same_way(self):
        p = self.packet("app")
        pr.apply_ci_runs(p, [f"{self.via_alias}=9"])
        self.assertEqual(p["tests"]["ci_runs"], [{"repo": str(self.real.resolve()), "run_id": 9}])
        with self.assertRaises(pr.ReviewError):
            pr.apply_ci_runs(p, ["nowhere=9"])

    def test_a_packet_without_repos_is_resolved_not_refused(self):
        # a fix-round packet fragment carries no repos; the match is judged at load, where repos exist
        p = {"tests": {"ci_runs": [{"repo": "app", "run_id": 1}]}}
        pr.apply_ci_runs(p, [f"{self.via_alias}=9"])
        self.assertEqual(p["tests"]["ci_runs"], [{"repo": str(self.real.resolve()), "run_id": 9}])

    def test_open_refuses_a_packet_whose_run_names_no_repository(self):
        # through load_packet, which cmd_open calls: the refusal happens before any review opens
        git = lambda *a: subprocess.run(["git", "-C", str(self.real), *a], check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
        (self.real / "f").write_text("a\n"); git("add", "."); git("commit", "-qm", "a"); base = git("rev-parse", "HEAD")
        (self.real / "f").write_text("b\n"); git("commit", "-qam", "b"); head = git("rev-parse", "HEAD")
        body = {"outcome": "o", "acceptance_criteria": ["c"], "changed_behavior": "b", "exclusions": [],
                "release_owner": "dorianatmoxywolf", "tests": {"commands": [], "results": "r"},
                "repos": [{"path": self.via_alias, "base": base, "head": head}]}
        missing = [f for f in pr.PACKET_FIELDS if f not in body]
        for f in missing:
            body[f] = [] if f in ("prior_findings",) else {"owner": "dorianatmoxywolf"} if f == "data_use" else "x"
        ok = self.tmp / "ok.json"
        body["tests"]["ci_runs"] = [{"repo": self.via_alias, "run_id": 1}]
        ok.write_text(json.dumps(body))
        self.assertEqual(pr.load_packet(ok)["tests"]["ci_runs"][0]["repo"], str(self.real.resolve()))
        bad = self.tmp / "bad.json"
        body["tests"]["ci_runs"] = [{"repo": str(self.tmp / "elsewhere"), "run_id": 1}]
        bad.write_text(json.dumps(body))
        with self.assertRaises(pr.ReviewError) as c:
            pr.load_packet(bad)
        self.assertIn("not a repository in this packet", str(c.exception))


if __name__ == "__main__":
    unittest.main()
