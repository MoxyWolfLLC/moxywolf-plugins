#!/usr/bin/env python3
"""The probe is the deterministic layer: direct tool calls and REST calls,
no model. It is also the step that sends traffic, so these tests pin the
gates (named approver for production, drafts never on production, token from
the environment) and run a full plan against a local fake server."""
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fixtures as F  # noqa: E402
from _fixtures import dl  # noqa: E402
import probe  # noqa: E402


class Fake(BaseHTTPRequestHandler):
    seen: list = []

    def log_message(self, *a):
        pass

    def _send(self, code, body, headers=None, sse=False):
        raw = (f"event: message\ndata: {json.dumps(body)}\n\n" if sse else json.dumps(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/event-stream" if sse else "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        Fake.seen.append(("POST", self.path, body.get("method"), self.headers.get("Authorization"), self.headers.get("mcp-session-id")))
        if self.path != "/api/mcp":
            return self._send(404, {"error": "no"})
        m = body.get("method")
        if m == "initialize":
            return self._send(200, {"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2025-06-18"}}, {"mcp-session-id": "s1"})
        if m == "notifications/initialized":
            return self._send(202, {})
        if self.headers.get("mcp-session-id") != "s1":
            return self._send(400, {"error": "no session"})
        if m == "tools/call" and body["params"]["name"] == "widgets_plan":
            return self._send(200, {"jsonrpc": "2.0", "id": body["id"], "result": {"content": [{"type": "text", "text": "{\"roles\": [\"sysadmin\"]}"}]}}, sse=True)
        return self._send(200, {"jsonrpc": "2.0", "id": body["id"], "result": {"content": [{"type": "text", "text": "not_held"}]}})

    def do_GET(self):
        Fake.seen.append(("GET", self.path, None, self.headers.get("Authorization"), None))
        if self.path.startswith("/api/v1/items/42/download"):
            return self._send(200, {"id": "42", "rules": []})
        return self._send(404, {"error": "not_held"})


class Plan(unittest.TestCase):
    def test_plan_separates_payload_and_rest_checks(self):
        b = F.bank()
        qs = {x["id"]: x for x in b["questions"]}
        qs["Q-0005"]["rest"] = {"calls": [{"method": "POST", "path": "/api/v1/plan", "body": {}}], "must_contain": ["rest-only-needle"]}
        qs["Q-0005"]["surfaces"] = ["mcp", "rest"]
        cmap = {"mcp": {"tools": [], "tool_names": []}, "rest": {"routes": []}}
        b["questions"][6].update({"surfaces": ["rest"], "rest": {"calls": [{"method": "GET", "path": "/api/v1/batch"}]}})
        plan = probe.build_plan(b, cmap)
        items = {i["bank_id"]: i for i in plan["items"]}
        self.assertEqual(items["Q-0005"]["checks"]["must_contain"], ["roles"])
        self.assertEqual(items["Q-0005"]["rest_checks"]["must_contain"], ["rest-only-needle"])
        self.assertIn("Q-0006", items)
        self.assertNotIn("Q-0007", items, "drafts are not planned by default")
        drafted = {i["bank_id"]: i for i in probe.build_plan(b, cmap, include_drafts=True)["items"]}
        self.assertTrue(drafted["Q-0007"]["draft"])

    def test_grade_excuses_only_explained_absence(self):
        checks = {"must_contain": ["terminals"], "absence_acceptable": True}
        self.assertTrue(all(c["passed"] for c in probe.grade('{"error":"not_held"}', checks, ["not_held"])))
        self.assertFalse(all(c["passed"] for c in probe.grade('{"results":[]}', checks, ["not_held"])))
        self.assertFalse(probe.grade("", checks, ["not_held"])[0]["passed"], "an empty result is never excused")
        bad = probe.grade("You are compliant.", {"must_not_match": [r"\byou are compliant\b"]}, [])
        self.assertFalse(bad[0]["passed"])


class Run(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Fake)
        cls.port = cls.srv.server_address[1]
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        Fake.seen = []
        self.w = F.Workspace()
        prof = dl.load_json(self.w.profile)
        base = f"http://127.0.0.1:{self.port}"
        prof["targets"]["staging"] = {"mcp_url": base + "/api/mcp", "rest_base": base}
        prof["targets"]["production"] = {"mcp_url": base + "/api/mcp", "rest_base": base, "requires_named_approval": True}
        F.write_json(prof, self.w.profile)
        self.plan = self.w.path("plan.json")
        rc, _, err = F.run("probe.py", "plan", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--out", self.plan)
        self.assertEqual(rc, 0, err)
        self.env = dict(os.environ, WIDGETS_TOKEN="test-token")

    def tearDown(self):
        self.w.close()

    def _run(self, *extra, env=None):
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(F.SCRIPTS, "probe.py"), "run", "--plan", self.plan, "--profile", self.w.profile,
                            "--out", self.w.path("probe.json"), *extra], capture_output=True, text=True, env=env or self.env)
        return r.returncode, r.stdout, r.stderr

    def test_staging_run_end_to_end(self):
        rc, out, err = self._run()
        self.assertEqual(rc, 0, out + err)
        res = {r["bank_id"]: r for r in dl.load_json(self.w.path("probe.json"))["results"]}
        self.assertTrue(res["Q-0005"]["passed"], "payload needle found through SSE framing")
        self.assertTrue(res["Q-0006"]["passed"], "REST call and needle")
        methods = [s[2] for s in Fake.seen if s[0] == "POST"]
        self.assertEqual(methods[:2], ["initialize", "notifications/initialized"], "handshake first, like verify-eval.ts")
        self.assertTrue(all(s[3] == "Bearer test-token" for s in Fake.seen))
        self.assertFalse(any(s[0] in ("PUT", "PATCH", "DELETE") for s in Fake.seen))

    def test_production_needs_named_person(self):
        rc, _, err = self._run("--target", "production")
        self.assertEqual(rc, 3)
        rc, _, err = self._run("--target", "production", "--approver", "claude")
        self.assertEqual(rc, 3)
        self.assertEqual(Fake.seen, [], "nothing is sent before the gate passes")
        rc, out, err = self._run("--target", "production", "--approver", "Dorian Cougias")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(dl.load_json(self.w.path("probe.json"))["approved_by"], "Dorian Cougias")

    def test_drafts_never_reach_production(self):
        b = self.w.load_bank()
        b["questions"][6].update({"surfaces": ["rest"], "rest": {"calls": [{"method": "GET", "path": "/api/v1/items/42/download"}]}})
        self.w.save_bank(b)
        rc, _, err = F.run("probe.py", "plan", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--out", self.plan, "--include-drafts")
        self.assertEqual(rc, 0, err)
        rc, _, err = self._run("--target", "production", "--approver", "Dorian Cougias")
        self.assertEqual(rc, 3)
        self.assertIn("draft", err)

    def test_missing_token_stops_before_sending(self):
        env = {k: v for k, v in self.env.items() if k != "WIDGETS_TOKEN"}
        rc, _, err = self._run(env=env)
        self.assertEqual(rc, 2)
        self.assertEqual(Fake.seen, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
