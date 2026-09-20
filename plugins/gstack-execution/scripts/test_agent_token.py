"""GA-005 criteria 1 and 2: the agent acts on GitHub with a minted app token, the token never
reaches argv, output or a file, and nothing falls back to a person's credential."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "agent_token.py"
TOKEN = "ghs_FIXTURE_TOKEN_0123456789abcdef"


class Stub(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        Stub.seen.append((self.path, self.headers.get("Authorization", "")))
        if self.path == "/repos/owner/known/installation":
            body, code = {"id": 77, "account": {"login": "owner"}}, 200
        elif self.path == "/repos/owner/known/pulls":
            body, code = [], 200
        elif self.path == "/app/installations":
            body, code = [{"id": 42, "account": {"login": "MoxyWolfLLC"}},
                          {"id": 77, "account": {"login": "owner"}}], 200
        else:
            body, code = {"message": "Not Found"}, 404
        raw = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(raw))); self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        Stub.seen.append((self.path, self.headers.get("Authorization", "")))
        if self.path in ("/app/installations/42/access_tokens", "/app/installations/77/access_tokens"):
            body, code = {"token": TOKEN, "expires_at": "2099-01-01T00:00:00Z"}, 201
        else:
            body, code = {"message": "Bad credentials"}, 401
        raw = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(raw))); self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


class AgentToken(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        subprocess.run(["openssl", "genrsa", "-out", str(self.tmp / "key.pem"), "2048"], capture_output=True, check=True)
        self.envfile = self.tmp / "github-app.env"
        self.write_env(42)

    def write_env(self, inst):
        self.envfile.write_text(f"GITHUB_APP_ID=7\nGITHUB_APP_INSTALLATION_ID={inst}\nGITHUB_APP_KEY_FILE=key.pem\n")

    def run_script(self, *args):
        env = dict(os.environ, GSTACK_AGENT_APP_ENV=str(self.envfile),
                   GSTACK_GITHUB_API=f"http://127.0.0.1:{self.srv.server_port}")
        env.pop("GITHUB_TOKEN", None)
        # cwd is outside any checkout: these tests are about the token, not about which
        # installation owns a repository, and origin would otherwise force a resolve.
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              env=env, cwd=str(self.tmp))

    def test_the_token_reaches_the_command_and_nowhere_else(self):
        probe = self.tmp / "probe.json"
        child = ("import hashlib,json,os,sys;"
                 f"json.dump({{'argv':sys.argv,'tok':hashlib.sha256(os.environ['GITHUB_TOKEN'].encode()).hexdigest(),"
                 f"'header':os.environ['GIT_CONFIG_VALUE_0'],'key':os.environ['GIT_CONFIG_KEY_0']}},open({str(probe)!r},'w'))")
        r = self.run_script("exec", "--", sys.executable, "-c", child)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(probe.read_text())
        import base64, hashlib
        self.assertEqual(got["tok"], hashlib.sha256(TOKEN.encode()).hexdigest())
        self.assertEqual(got["key"], "http.https://github.com/.extraheader")
        self.assertIn(base64.b64encode(f"x-access-token:{TOKEN}".encode()).decode(), got["header"])
        self.assertNotIn(TOKEN, " ".join(got["argv"]))
        self.assertNotIn(TOKEN, r.stdout + r.stderr)
        files = [p for p in self.tmp.rglob("*") if p.is_file()]
        self.assertTrue(files, "examined no files")
        for p in files:
            self.assertNotIn(TOKEN, p.read_text(errors="replace"), p)
        path, auth = Stub.seen[-1]
        self.assertEqual(path, "/app/installations/42/access_tokens")
        self.assertEqual(auth.split()[0], "Bearer")
        self.assertEqual(len(auth.split()[1].split(".")), 3, "authenticated with a JWT")

    def test_a_failed_mint_names_the_endpoint_and_status_and_runs_nothing(self):
        self.write_env(99)
        marker = self.tmp / "ran"
        r = self.run_script("exec", "--", sys.executable, "-c", f"open({str(marker)!r},'w')")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("/app/installations/99/access_tokens", r.stderr)
        self.assertIn("401", r.stderr)
        self.assertIn("No other credential is tried", r.stderr)
        self.assertFalse(marker.exists(), "the command ran without a token")

    def test_no_app_env_means_no_credential_at_all(self):
        env = {k: v for k, v in os.environ.items() if k != "GSTACK_AGENT_APP_ENV"}
        r = subprocess.run([sys.executable, str(SCRIPT), "exec", "--", "true"], capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("GSTACK_AGENT_APP_ENV", r.stderr)

    def test_no_code_path_in_gstack_execution_reads_the_personal_token_file(self):
        code = [p for p in HERE.parent.rglob("*") if p.suffix in {".py", ".sh", ".mjs", ".js"}
                and not p.name.startswith("test_")]
        self.assertGreater(len(code), 5, f"examined only {len(code)} files")
        readers = [str(p.relative_to(HERE.parent)) for p in code if "github-pat.env" in p.read_text(errors="replace")]
        self.assertEqual(readers, [], "these read the personal token file")


class InstallationPerRepository(unittest.TestCase):
    """GA-006: the token is minted for the installation that owns the repository, and a repository
    the app cannot reach is a named refusal rather than a 404 the caller has to interpret."""

    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        subprocess.run(["openssl", "genrsa", "-out", str(self.tmp / "key.pem"), "2048"], capture_output=True, check=True)
        self.envfile = self.tmp / "github-app.env"
        self.envfile.write_text("GITHUB_APP_ID=7\nGITHUB_APP_INSTALLATION_ID=42\nGITHUB_APP_KEY_FILE=key.pem\n")
        Stub.seen.clear()

    def run_script(self, *args, cwd=None):
        env = dict(os.environ, GSTACK_AGENT_APP_ENV=str(self.envfile),
                   GSTACK_GITHUB_API=f"http://127.0.0.1:{self.srv.server_port}")
        env.pop("GITHUB_TOKEN", None)
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=cwd)

    def minted_from(self):
        return [path for path, _ in Stub.seen if path.endswith("/access_tokens")]

    def test_the_resolved_installation_wins_over_the_configured_one(self):
        r = self.run_script("exec", "--repo", "owner/known", "--", sys.executable, "-c", "pass")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("/repos/owner/known/installation", [p for p, _ in Stub.seen])
        self.assertEqual(self.minted_from(), ["/app/installations/77/access_tokens"],
                         "minted from the configured 42 instead of the resolved 77")

    def test_an_api_path_names_its_own_repository(self):
        r = self.run_script("api", "GET", "repos/owner/known/pulls")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.minted_from(), ["/app/installations/77/access_tokens"])

    def test_an_unreachable_repository_is_named_not_left_as_a_404(self):
        r = self.run_script("exec", "--repo", "stranger/repo", "--", sys.executable, "-c", "pass")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not installed on stranger", r.stderr)
        self.assertIn("MoxyWolfLLC", r.stderr, "does not say where it IS installed")
        self.assertIn("404", r.stderr)
        self.assertEqual(self.minted_from(), [], "fell back to the configured installation after a failed resolve")

    def test_no_repository_falls_back_and_says_what_it_tried(self):
        r = self.run_script("exec", "--", sys.executable, "-c", "pass", cwd=str(self.tmp))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--repo", r.stderr)
        self.assertIn("origin", r.stderr)
        self.assertEqual(self.minted_from(), ["/app/installations/42/access_tokens"])

    def test_the_parsers_cover_ssh_and_https_and_reject_what_is_not_a_repo(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("at", SCRIPT)
        at = importlib.util.module_from_spec(spec); spec.loader.exec_module(at)
        cases = 0
        for path, want in [("repos/o/r", "o/r"), ("/repos/o/r/pulls/1", "o/r"),
                           ("app/installations", None), ("repos/o", None), ("", None)]:
            self.assertEqual(at.repo_from_path(path), want, path); cases += 1
        for url, want in [("https://github.com/o/r.git", "o/r"), ("git@github.com:o/r.git", "o/r"),
                          ("https://github.com/o/r", "o/r"), ("https://example.com/o/r.git", None)]:
            git = self.tmp / "git"
            git.write_text(f"#!/bin/sh\necho {url}\n"); git.chmod(0o755)
            env = dict(os.environ, PATH=f"{self.tmp}:{os.environ['PATH']}")
            out = subprocess.run([sys.executable, "-c",
                                  f"import importlib.util;s=importlib.util.spec_from_file_location('at',{str(SCRIPT)!r});"
                                  "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(m.repo_from_origin())"],
                                 capture_output=True, text=True, env=env, cwd=str(self.tmp))
            self.assertEqual(out.stdout.strip(), str(want), url); cases += 1
        print(f"\nexamined {cases} parser cases")
        self.assertGreater(cases, 0, "examined no cases")

    def test_nothing_writes_a_resolved_id_to_disk(self):
        """A cached id would fail as a 404 long after the installation was removed, so the run
        leaves no new file behind. Searching files for the id itself gives false positives: a
        2048-bit PEM contains most short digit strings somewhere."""
        before = {p for p in self.tmp.rglob("*")}
        r = self.run_script("exec", "--repo", "owner/known", "--", sys.executable, "-c", "pass")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(before, "examined no files")
        after = {p for p in self.tmp.rglob("*")}
        self.assertEqual(after - before, set(), "the run left a file behind")
        home = Path(os.path.expanduser("~"))
        for name in (".agent_token_cache", ".gstack_installations.json"):
            self.assertFalse((home / name).exists(), f"cached to {name}")


class NoPushWithAPersonsToken(unittest.TestCase):
    """GA-005 criterion 4: every instruction that told the agent to push or open pull requests with
    the vault PAT says the app instead. Changelogs record what was, so they are exempt."""
    HOMES = ["plugins/gstack-execution/commands/gstack-build.md", "plugins/gstack-execution/commands/gstack-design-doc.md",
             "plugins/gstack-execution/GOVERNANCE.md", "plugins/gstack-execution/scripts/docs.md",
             "plugins/gstack-execution/scripts/repo_gates.py", "plugins/gstack-execution/scripts/review_host.sh", "README.md",
             "plugins/project-init/skills/session-start/SKILL.md", "plugins/project-init/skills/session-end/SKILL.md",
             "plugins/project-init/commands/session-end.md", "plugins/project-init/skills/project-init/SKILL.md"]

    def test_no_home_tells_the_agent_to_push_with_the_pat(self):
        import re
        root = HERE.parents[2]
        token = re.compile(r"\bPAT\b|github-pat\.env|GITHUB_PAT")
        action = re.compile(r"push|pull request|\bPR\b|/pulls", re.I)
        changelog = re.compile(r"^\s*[-*]\s*\*\*\d+\.\d+|^\s*#+\s*\d+\.\d+|changelog", re.I)
        examined, hits = 0, []
        for rel in self.HOMES:
            path = root / rel
            self.assertTrue(path.is_file(), f"{rel} is missing; the list of homes is stale")
            examined += 1
            for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if token.search(line) and action.search(line) and not changelog.search(line):
                    hits.append(f"{rel}:{n}: {line.strip()[:120]}")
        print(f"\nexamined {examined} files for push instructions naming the PAT: {len(hits)} found")
        self.assertEqual(examined, len(self.HOMES))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
