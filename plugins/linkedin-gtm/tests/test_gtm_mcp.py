#!/usr/bin/env python3
"""gtm_mcp.py with a mocked transport (and one real local HTTP server): reads pass, outward calls
need an approved item, preview then confirm, and limits are reported, never looped."""
import datetime as dt
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import batch_ledger as bl  # noqa: E402
import gtm_mcp as g  # noqa: E402

SID = "ln_ac_test"
OWNER = "Dorian Cougias"
TEXT = ("The crosswalk problem is rarely the mapping itself. It is keeping the mapping current when the "
        "source control changes and nobody owns the diff. Who owns that on your team?")


def ok(structured):
    return {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(structured)}],
                                                 "structuredContent": structured}}


def tool_err(code, context=None, message="no"):
    sc = {"success": False, "error": {"code": code, "message": message, "context": context or {}},
          "meta": {"trace_id": "t"}}
    return {"jsonrpc": "2.0", "id": 1, "result": {"isError": True,
                                                 "content": [{"type": "text", "text": json.dumps(sc)}],
                                                 "structuredContent": sc}}


class FakeTransport:
    """Scripted responses; records every payload and header set."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, endpoint, payload, headers, timeout=None):
        self.calls.append((payload, dict(headers)))
        resp = self.responses.pop(0)
        if isinstance(resp, tuple):
            return resp
        return 200, "application/json", json.dumps(resp)

    def inner(self, i):
        return self.calls[i][0]["params"]["arguments"]


def preview_for(args):
    return ok({"preview": True, "tool": "create_linkedin_comment", "dangerous": True, "summary": "comment",
               "arguments": args, "validated": {"post": "ok"}, "commit_token": "tok123",
               "expires_in_seconds": 300})


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["LINKEDIN_GTM_TODAY"] = "2026-11-10"
        os.environ.pop("GTM_AUTH_VIA_PROXY", None)
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "2026-11-10.json"
        lg = bl.new_ledger("2026-11-10", SID, OWNER)
        bl.add_item(lg, "comment", {"entity_urn": "urn:li:activity:1", "text": TEXT}, "C", "r1")
        bl.add_item(lg, "comment", {"entity_urn": "urn:li:activity:2", "text": TEXT}, "C", "r2")
        bl.add_item(lg, "connect", {"public_identifier": "jane", "note": "Read your STIG post. Good one."}, "B", "r3")
        bl.present(lg)
        bl.decide(lg, ["20261110-001", "20261110-002"], "approve", OWNER, "DC")
        bl.save(lg, self.path)
        self.args = dict(bl.load(self.path)["items"][0]["args"])

    def tearDown(self):
        os.environ.pop("LINKEDIN_GTM_TODAY", None)
        self.tmp.cleanup()

    def client(self, responses, **kw):
        t = FakeTransport(responses)
        return g.GtmClient(api_key="gtm_live_secret", transport=t, **kw), t


class Classify(unittest.TestCase):
    def test_lists(self):
        self.assertEqual(g.classify("get_linkedin_account"), "read")
        self.assertEqual(g.classify("search_linkedin_account_smart_limits"), "read")
        self.assertEqual(g.classify("create_linkedin_comment"), "gated")
        self.assertEqual(g.classify("send_linkedin_connection_request"), "gated")
        for bad in ("create_mass_action", "update_linkedin_account_smart_limit", "send_linkedin_inmail",
                    "made_up_tool", "create_webhook"):
            self.assertEqual(g.classify(bad), "refused", bad)


class Reads(Base):
    def test_read_sends_bearer_and_meta_call(self):
        c, t = self.client([ok({"success": True, "item": {"status": "active"}})])
        r = c.read("get_linkedin_account", {"sid": SID})
        self.assertTrue(r.ok)
        self.assertEqual(r.data["item"]["status"], "active")
        payload, headers = t.calls[0]
        self.assertEqual(payload["method"], "tools/call")
        self.assertEqual(payload["params"]["name"], "call_tool")
        self.assertEqual(payload["params"]["arguments"], {"name": "get_linkedin_account", "arguments": {"sid": SID}})
        self.assertEqual(headers["Authorization"], "Bearer gtm_live_secret")

    def test_proxy_mode_sends_no_header(self):
        c, t = self.client([ok({"success": True})], proxy_auth=True)
        c.read("get_linkedin_account", {"sid": SID})
        self.assertNotIn("Authorization", t.calls[0][1])

    def test_no_credential_refused(self):
        os.environ.pop("GTM_API_KEY", None)
        with self.assertRaises(g.Refused):
            g.GtmClient(api_key=None, proxy_auth=False, transport=FakeTransport([]))

    def test_read_refuses_outward_tools(self):
        c, t = self.client([])
        for name in ("create_linkedin_comment", "create_mass_action", "send_linkedin_message"):
            with self.assertRaises(g.Refused):
                c.read(name, {})
        self.assertEqual(t.calls, [])

    def test_sse_body(self):
        body = "event: message\ndata: " + json.dumps(ok({"success": True, "n": 3})) + "\n\n"
        c, _ = self.client([(200, "text/event-stream", body)])
        self.assertEqual(c.read("get_linkedin_account", {"sid": SID}).data["n"], 3)

    def test_cli_read_rate_limited_exit_3_no_retry(self):
        t = FakeTransport([tool_err("rate_limited", {"retry_after": 900, "reason": "bucket_saturated",
                                                     "cause": "daily_saturation"})])
        os.environ["GTM_API_KEY"] = "gtm_live_secret"
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = g.main(["read", "scrape_linkedin_search_posts", "--args", '{"url": "x"}'], transport=t)
        finally:
            os.environ.pop("GTM_API_KEY", None)
        self.assertEqual(code, g.EXIT_STOPPED)
        self.assertEqual(len(t.calls), 1)
        self.assertNotIn("gtm_live_secret", buf.getvalue())

    def test_cli_refuses_write_through_read(self):
        os.environ["GTM_API_KEY"] = "k"
        try:
            with redirect_stderr(io.StringIO()):
                code = g.main(["read", "create_linkedin_post", "--args", "{}"], transport=FakeTransport([]))
        finally:
            os.environ.pop("GTM_API_KEY", None)
        self.assertEqual(code, g.EXIT_REFUSED)


class Execute(Base):
    def test_preview_then_confirm_with_token(self):
        c, t = self.client([preview_for(self.args), ok({"success": True, "item": {"urn": "urn:li:comment:9"}})])
        code, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual(code, g.EXIT_OK)
        self.assertEqual(rep["outcome"], "executed")
        self.assertEqual(len(t.calls), 2)
        first, second = t.inner(0), t.inner(1)
        self.assertEqual(first["name"], "create_linkedin_comment")
        self.assertNotIn("commit_token", first["arguments"])
        self.assertEqual(second["arguments"]["commit_token"], "tok123")
        self.assertEqual({k: v for k, v in second["arguments"].items() if k != "commit_token"}, self.args)
        item = bl.load(self.path)["items"][0]
        self.assertEqual(item["status"], "executed")
        self.assertEqual(item["execution"]["result_ref"], {"urn": "urn:li:comment:9"})

    def test_unapproved_item_sends_nothing(self):
        c, t = self.client([])
        with self.assertRaises(g.Refused):
            g.execute_item(c, self.path, "20261110-003")  # drafted, never decided
        self.assertEqual(t.calls, [])

    def test_second_run_refused(self):
        c, _ = self.client([preview_for(self.args), ok({"success": True})])
        g.execute_item(c, self.path, "20261110-001")
        c2, t2 = self.client([])
        with self.assertRaises(g.Refused):
            g.execute_item(c2, self.path, "20261110-001")
        self.assertEqual(t2.calls, [])

    def test_preview_argument_mismatch_not_confirmed(self):
        changed = dict(self.args, text="something else")
        c, t = self.client([preview_for(changed)])
        code, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual(code, g.EXIT_FAIL)
        self.assertEqual(len(t.calls), 1)

    def test_rate_limited_on_confirm_stops_bucket(self):
        c, t = self.client([preview_for(self.args),
                            tool_err("rate_limited", {"retry_after": 1800, "reason": "bucket_saturated",
                                                      "cause": "delay_not_elapsed", "send_outcome": "not_sent"})])
        code, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual(code, g.EXIT_STOPPED)
        self.assertEqual(rep["retry_after"], 1800)
        self.assertEqual(len(t.calls), 2)  # no retry
        c2, t2 = self.client([])
        with self.assertRaises(g.Refused):  # same bucket, stopped for the day
            g.execute_item(c2, self.path, "20261110-002")
        self.assertEqual(t2.calls, [])

    def test_quota_hit_cause(self):
        c, _ = self.client([preview_for(self.args),
                            tool_err("rate_limited", {"reason": "bucket_saturated", "cause": "linkedin_quota_hit"})])
        _, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual(rep["outcome"], "quota_hit")

    def test_send_outcome_unknown_is_uncertain(self):
        c, _ = self.client([preview_for(self.args),
                            tool_err("conflict", {"send_outcome": "unknown"}, "send_outcome_unknown")])
        code, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual(code, g.EXIT_UNCERTAIN)
        self.assertEqual(bl.load(self.path)["items"][0]["status"], "uncertain")

    def test_target_blocked(self):
        c, _ = self.client([preview_for(self.args), tool_err("target_blocked", {"send_outcome": "not_sent"})])
        code, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual((code, rep["outcome"]), (g.EXIT_STOPPED, "blocked"))

    def test_checkpoint_stops_all(self):
        c, _ = self.client([preview_for(self.args),
                            tool_err("forbidden", {"reason": "login_issue"}, "browser login_issue")])
        code, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual(rep["outcome"], "checkpoint")
        self.assertTrue(bl.load(self.path)["stops"]["all"])

    def test_no_preview_from_server_is_uncertain(self):
        c, t = self.client([ok({"success": True, "item": {"urn": "x"}})])
        code, rep = g.execute_item(c, self.path, "20261110-001")
        self.assertEqual(code, g.EXIT_UNCERTAIN)
        self.assertEqual(len(t.calls), 1)


class _Handler(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Handler.seen.append((body, self.headers.get("Authorization")))
        out = json.dumps(ok({"success": True, "toolsets": ["linkedin.messaging"]})).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class RealHttp(unittest.TestCase):
    def test_urllib_transport_against_local_server(self):
        srv = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            c = g.GtmClient(endpoint=f"http://127.0.0.1:{srv.server_port}/mcp", api_key="gtm_live_x")
            r = c.list_toolsets()
            self.assertTrue(r.ok)
            self.assertEqual(r.data["toolsets"], ["linkedin.messaging"])
            body, auth = _Handler.seen[-1]
            self.assertEqual(body["params"]["name"], "list_toolsets")
            self.assertEqual(auth, "Bearer gtm_live_x")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
