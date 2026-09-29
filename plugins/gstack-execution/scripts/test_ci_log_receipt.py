#!/usr/bin/env python3
"""XE-027 acceptance: a failed CI job reaches the reviewer as a receipt of quotes the dispatcher
checked against the log, or as the log itself; never as a summary nobody checked."""
import hashlib, http.server, json, os, shutil, subprocess, sys, tempfile, threading, unittest
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


class FakeGitHub:
    """A local GitHub: run 7 with a failed job 41 and a passing job 42. The job log answers with a
    redirect to a log store on the same server, as GitHub does, so the test sees both requests."""
    def __init__(self, test, log_bytes=None, refuse=False):
        self.seen, self.log_bytes, self.refuse = [], log_bytes if log_bytes is not None else LOG.encode(), refuse
        fake = self
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                fake.seen.append((self.path, self.headers.get("Authorization")))
                if self.path.endswith("/actions/jobs/41/logs"):
                    if fake.refuse:
                        return self.reply(403, b'{"message": "Resource not accessible"}')
                    self.send_response(302); self.send_header("Location", f"{fake.url}/blob/41.log"); self.end_headers()
                elif self.path == "/blob/41.log":
                    self.reply(200, fake.log_bytes)
                elif "/actions/runs/7/jobs" in self.path:
                    self.reply(200, json.dumps({"total_count": 2, "jobs": [
                        {"id": 41, "name": "unit", "conclusion": "failure", "steps": []},
                        {"id": 42, "name": "lint", "conclusion": "success", "steps": []}]}).encode())
                elif self.path.endswith("/actions/runs/7"):
                    self.reply(200, json.dumps({"head_sha": test.head, "conclusion": "failure"}).encode())
                else:
                    self.reply(404, b"{}")
            def reply(self, code, body):
                self.send_response(code); self.end_headers(); self.wfile.write(body)
        self.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start(); test.addCleanup(self.srv.shutdown)
        for k, v in {"GITHUB_TOKEN": "secret-token", "GSTACK_GITHUB_API": self.url}.items():
            old = os.environ.get(k); os.environ[k] = v
            test.addCleanup(lambda k=k, old=old: os.environ.pop(k) if old is None else os.environ.__setitem__(k, old))

    def auth(self, path):
        return [a for p, a in self.seen if p == path]


class SurfaceTests(unittest.TestCase):
    """build_surface end to end over HTTP; only the reducer model is stubbed."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="xe027-")); self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "app"; self.repo.mkdir()
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()
        g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("remote", "add", "origin", "https://github.com/acme/app.git")
        (self.repo / "a.py").write_text("x = 1\n"); g("add", "."); g("commit", "-qm", "base"); base = g("rev-parse", "HEAD")
        (self.repo / "a.py").write_text("x = 2\n"); g("commit", "-qam", "head"); self.head = g("rev-parse", "HEAD")
        self.repos = [{"path": str(self.repo), "base": base, "head": self.head}]

    def reducer(self, fn):
        orig = pr.reducer_ask; pr.reducer_ask = fn; self.addCleanup(setattr, pr, "reducer_ask", orig)

    def surface(self):
        out = self.tmp / "round"; out.mkdir(exist_ok=True)
        return pr.build_surface(self.repos, out, ci_runs=[{"repo": "app", "run_id": 7}], archive_dir=self.tmp / "review" / "ci-logs")

    def test_failed_job_gets_a_checked_receipt_and_a_durable_archive(self):
        gh = FakeGitHub(self)
        self.reducer(lambda i, r: (receipt(), "cheap/model", 321))
        surf, stats = self.surface()
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        unit = rec["jobs"][0]; self.assertNotIn("log", rec["jobs"][1], "a passing job's log is not read")
        self.assertEqual(unit["log"]["receipt"], "applied"); self.assertEqual(unit["log"]["sha256"], clr.sha256(LOG))
        text = (surf / "evidence" / "ci-7-job-41.receipt.txt").read_text()
        self.assertIn(json.dumps(QUOTE), text); self.assertIn("reducer_model=cheap/model", text)
        archive = self.tmp / "review" / "ci-logs" / "7-41.log"
        self.assertEqual(archive.read_bytes(), LOG.encode(), "the full log is kept outside the surface")
        self.assertEqual(stats["ci_logs"][0]["archive"], str(archive)); self.assertEqual(stats["ci_logs"][0]["job_id"], 41)
        self.assertEqual({k: stats["evidence"][k] for k in ("failed_jobs", "logs_read", "receipts_applied")},
                         {"failed_jobs": 1, "logs_read": 1, "receipts_applied": 1})
        self.assertIn("checked byte for byte by the dispatcher", (surf / "SURFACE.md").read_text())
        self.assertEqual(gh.auth("/repos/acme/app/actions/jobs/41/logs"), ["token secret-token"])
        self.assertEqual(gh.auth("/blob/41.log"), [None], "the token never reaches the log store")

    def test_failed_reducer_sends_the_capped_log(self):
        FakeGitHub(self, log_bytes=(LOG * 10).encode())
        def boom(i, r): raise RuntimeError("no key")
        self.reducer(boom)
        surf, stats = self.surface()
        shown = (surf / "evidence" / "ci-7-job-41.log").read_bytes()
        self.assertTrue(shown.startswith(b"[cut: showing the last"))
        self.assertLessEqual(len(shown), clr.TAIL_BYTES + 200)
        self.assertIn("no receipt: reducer_unavailable", (surf / "SURFACE.md").read_text())
        self.assertEqual(stats["evidence"]["receipts_applied"], 0)
        self.assertEqual(stats["ci_logs"][0]["reducer_error"], "no key", "why the reducer failed is kept")

    def test_refused_log_is_recorded_not_raised(self):
        FakeGitHub(self, refuse=True)
        self.reducer(lambda i, r: self.fail("nothing to reduce"))
        surf, stats = self.surface()
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        self.assertFalse(rec["jobs"][0]["log"]["read"]); self.assertIn("403", rec["jobs"][0]["log"]["error"])
        self.assertEqual(stats["evidence"]["logs_read"], 0)
        self.assertIn("log could not be read", (surf / "SURFACE.md").read_text())

    def test_crlf_and_invalid_utf8_survive_byte_for_byte(self):
        raw = LOG.replace("\n", "\r\n").encode() + b"bad byte \xff here\r\n"
        FakeGitHub(self, log_bytes=raw)
        crlf_quote = QUOTE + "\r"
        text = clr.as_text(raw)
        good = json.dumps({"schema": clr.SCHEMA, "source_sha256": clr.sha256(text), "status": "failure",
                           "uncertain": False, "evidence": [{"kind": "failure", "quote": crlf_quote}]})
        self.reducer(lambda i, r: (good, "m", 1))
        surf, stats = self.surface()
        log = stats["ci_logs"][0]
        self.assertEqual((self.tmp / "review" / "ci-logs" / "7-41.log").read_bytes(), raw)
        self.assertEqual(log["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(log["sha256"], clr.sha256(text), "the receipt's hash is the hash of the bytes GitHub sent")
        self.assertEqual(log["receipt"], "applied")


if __name__ == "__main__":
    unittest.main()
