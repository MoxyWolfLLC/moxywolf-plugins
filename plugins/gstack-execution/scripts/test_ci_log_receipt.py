#!/usr/bin/env python3
"""XE-027 acceptance: a failed CI job reaches the reviewer as a receipt of quotes the dispatcher
checked against the log, or as the log itself; never as a summary nobody checked."""
import http.server, json, os, shutil, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ci_log_receipt as clr
import peer_review as pr

LOG = ("##[group]Run pytest\n" + "collected line ok\n" * 900
       + "FAILED tests/test_listing.py::test_rows - AssertionError: 999 != 1000\n"
       + "##[error]Process completed with exit code 1.\n" + "cleanup\n" * 40)
QUOTE = "FAILED tests/test_listing.py::test_rows - AssertionError: 999 != 1000"


def receipt(**over):
    r = {"schema": clr.SCHEMA, "source_sha256": clr.sha256(LOG), "status": "failure", "uncertain": False,
         "evidence": [{"kind": "failure", "quote": QUOTE}]}
    r.update(over)
    return json.dumps(r)


class ValidateTests(unittest.TestCase):
    def reason(self, raw, log=LOG, failed=True):
        return clr.validate_receipt(raw, log, failed)[2]

    def test_good_receipt_is_accepted_with_its_line(self):
        ev, uncertain, why = clr.validate_receipt(receipt(), LOG, True)
        self.assertIsNone(why); self.assertFalse(uncertain)
        self.assertEqual(ev[0]["line"], LOG[:LOG.index(QUOTE)].count("\n") + 1)

    def test_each_broken_receipt_is_refused_by_name(self):
        self.assertEqual(self.reason("not json"), "invalid_json")
        self.assertEqual(self.reason(receipt(source_sha256="0" * 64)), "schema_mismatch")
        self.assertEqual(self.reason(receipt(status="success")), "schema_mismatch")
        self.assertEqual(self.reason(receipt(evidence=[{"kind": "failure", "quote": "1 passed"}])), "unverifiable_quote")
        self.assertEqual(self.reason(receipt(evidence=[{"kind": "failure", "quote": QUOTE}] * 13)), "schema_mismatch")
        self.assertEqual(self.reason(receipt(evidence=[{"kind": "summary", "quote": "cleanup"}])), "missing_failure_evidence")


class ReduceTests(unittest.TestCase):
    ok = staticmethod(lambda i, r: (receipt(), "m", 10))

    def test_short_log_and_secret_are_never_sent(self):
        sent = []
        ask = lambda i, r: sent.append(r) or (receipt(), "m", 1)
        self.assertEqual(clr.reduce("short\n", True, ask), (None, "under_min_bytes"))
        self.assertEqual(clr.reduce(LOG + "token=ghp_" + "a" * 36 + "\n", True, ask), (None, "likely_secret"))
        self.assertEqual(sent, [])

    def test_failed_ask_and_bloated_receipt_return_a_reason(self):
        def boom(i, r): raise RuntimeError("no key")
        self.assertEqual(clr.reduce(LOG, True, boom), (None, "reducer_unavailable"))
        # Quotes of bare newlines cost two characters each once escaped, so the receipt outgrows the log.
        big = "\n" * 8200 + "FAILED x\n"
        ev = [{"kind": "failure", "quote": "FAILED x"}] + [{"kind": "summary", "quote": "\n" * (490 + i)} for i in range(11)]
        many = json.dumps({"schema": clr.SCHEMA, "source_sha256": clr.sha256(big), "status": "failure",
                           "uncertain": False, "evidence": ev})
        self.assertEqual(clr.reduce(big, True, lambda i, r: (many, "m", 1)), (None, "receipt_not_smaller"))
        self.assertIsNone(clr.reduce(LOG, True, self.ok)[1])

    def test_instructions_call_the_log_untrusted(self):
        self.assertIn("untrusted", clr.instructions())
        self.assertIn(f"source_sha256={clr.sha256(LOG)}", clr.request(LOG, True))


class SurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="xe027-")); self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "app"; self.repo.mkdir()
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()
        g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("remote", "add", "origin", "https://github.com/acme/app.git")
        (self.repo / "a.py").write_text("x = 1\n"); g("add", "."); g("commit", "-qm", "base"); base = g("rev-parse", "HEAD")
        (self.repo / "a.py").write_text("x = 2\n"); g("commit", "-qam", "head"); self.head = g("rev-parse", "HEAD")
        self.repos = [{"path": str(self.repo), "base": base, "head": self.head}]
        head = self.head
        def get(name, path):
            if "/jobs?" in path:
                return {"total_count": 2, "jobs": [
                    {"id": 41, "name": "unit", "conclusion": "failure", "steps": []},
                    {"id": 42, "name": "lint", "conclusion": "success", "steps": []}]}
            return {"head_sha": head, "conclusion": "failure"}
        self.patch("github_get", get)

    def patch(self, attr, value):
        orig = getattr(pr, attr); setattr(pr, attr, value); self.addCleanup(setattr, pr, attr, orig)

    def surface(self):
        out = self.tmp / "round"; out.mkdir(exist_ok=True)
        return pr.build_surface(self.repos, out, ci_runs=[{"repo": "app", "run_id": 7}])

    def test_failed_job_gets_a_checked_receipt(self):
        self.patch("github_job_log", lambda name, job_id: LOG)
        self.patch("reducer_ask", lambda i, r: (receipt(), "cheap/model", 321))
        surf, stats = self.surface()
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        unit = rec["jobs"][0]; self.assertNotIn("log", rec["jobs"][1], "a passing job's log is not read")
        self.assertEqual(unit["log"]["receipt"], "applied"); self.assertEqual(unit["log"]["sha256"], clr.sha256(LOG))
        text = (surf / "evidence" / "ci-7-job-41.receipt.txt").read_text()
        self.assertIn(json.dumps(QUOTE), text); self.assertIn("reducer_model=cheap/model", text)
        self.assertEqual(Path(unit["log"]["archive"]).read_text(), LOG, "the full log is kept")
        self.assertEqual({k: stats["evidence"][k] for k in ("failed_jobs", "logs_read", "receipts_applied")},
                         {"failed_jobs": 1, "logs_read": 1, "receipts_applied": 1})
        self.assertIn("checked byte for byte by the dispatcher", (surf / "SURFACE.md").read_text())

    def test_failed_reducer_sends_the_capped_log(self):
        self.patch("github_job_log", lambda name, job_id: LOG * 10)
        def boom(i, r): raise RuntimeError("no key")
        self.patch("reducer_ask", boom)
        surf, stats = self.surface()
        shown = (surf / "evidence" / "ci-7-job-41.log").read_text()
        self.assertTrue(shown.startswith("[cut: showing the last"))
        self.assertLessEqual(len(shown.encode()), clr.TAIL_BYTES + 200)
        self.assertIn("no receipt: reducer_unavailable", (surf / "SURFACE.md").read_text())
        self.assertEqual(stats["evidence"]["receipts_applied"], 0)
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        self.assertEqual(rec["jobs"][0]["log"]["reducer_error"], "no key", "why the reducer failed is kept")

    def test_refused_log_is_recorded_not_raised(self):
        def refuse(name, job_id): raise pr.ReviewError("release_unavailable", "HTTP 403")
        self.patch("github_job_log", refuse)
        surf, stats = self.surface()
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        self.assertFalse(rec["jobs"][0]["log"]["read"]); self.assertIn("403", rec["jobs"][0]["log"]["error"])
        self.assertEqual(stats["evidence"]["logs_read"], 0)
        self.assertIn("log could not be read", (surf / "SURFACE.md").read_text())


class RedirectTests(unittest.TestCase):
    """The token goes to GitHub, never to the log store GitHub redirects to."""
    def test_token_is_not_sent_to_the_redirect_target(self):
        seen = {}
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                seen[self.path] = self.headers.get("Authorization")
                if self.path.endswith("/logs"):
                    self.send_response(302); self.send_header("Location", f"http://127.0.0.1:{srv.server_port}/blob/log.txt"); self.end_headers()
                else:
                    self.send_response(200); self.end_headers(); self.wfile.write(b"the log\n")
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start(); self.addCleanup(srv.shutdown)
        env = {"GITHUB_TOKEN": "secret-token", "GSTACK_GITHUB_API": f"http://127.0.0.1:{srv.server_port}"}
        old = {k: os.environ.get(k) for k in env}; os.environ.update(env)
        try:
            self.assertEqual(pr.github_job_log("acme/app", 41), "the log\n")
        finally:
            for k, v in old.items():
                os.environ.pop(k) if v is None else os.environ.__setitem__(k, v)
        self.assertEqual(seen["/repos/acme/app/actions/jobs/41/logs"], "token secret-token")
        self.assertIsNone(seen["/blob/log.txt"])


if __name__ == "__main__":
    unittest.main()
