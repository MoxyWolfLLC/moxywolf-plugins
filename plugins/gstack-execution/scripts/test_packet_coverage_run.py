#!/usr/bin/env python3
"""XE-014 criteria 10 and 11: execute packet_coverage.mjs as a subprocess, never only the verdict.

A suite green over a producer that had never run once was the defect. So every case here starts
node on the real script and reads what it wrote into the packet. The scorer's dependency must be
installed (`npm ci` in plugins/gstack-execution); when it is not, this file FAILS rather than
skipping, because a skipped scorer test is the gate that is not there (criterion 11).
"""
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "packet_coverage.mjs"
PLUGIN = HERE.parent
DESIGN = """# Fixture design

### FX-001 — A fixture item

**Status:** planned.

1. The value is after.
2. The old value is gone.

### FX-002 — Another item

1. Unrelated.
"""
# Byte-identical in shape to the real aigateway.env: 19 bytes of name and `=`, a 60-character
# `vck_` key, 79 bytes in all, and NO trailing newline (criterion 8).
FAKE_KEY = "vck_" + "x" * 56
NO_NEWLINE = ("AI_GATEWAY_API_KEY=" + FAKE_KEY).encode()


class Stub(http.server.BaseHTTPRequestHandler):
    """The gateway's evaluation-model endpoint, on localhost, reached through JEV_ENDPOINT."""
    status = 200
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        if Stub.status != 200:
            out = {"error": {"message": "invalid api key", "type": "authentication_error"}}
        else:
            out = {"answers": {k: {"type": "boolean", "probability": 0.9} for k in body["questions"]},
                   "usage": {"inputTokens": 42, "outputTokens": 1}}
        raw = json.dumps(out).encode()
        self.send_response(Stub.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


class ScorerRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("node"):
            raise AssertionError("node is not installed; the scorer cannot be tested, and that is a failure, not a skip")
        if not (PLUGIN / "node_modules" / "ai").is_dir():
            raise AssertionError(f"`ai` is not installed; run `npm ci` in {PLUGIN}. A skipped scorer test is not a pass.")
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        Stub.status, Stub.seen = 200, []
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"; self.home.mkdir()      # no vault under it: nothing to find
        (self.tmp / "DESIGN.md").write_text(DESIGN)
        self.packet = self.tmp / "packet.json"
        self.packet.write_text(json.dumps({"items": ["FX-001"], "acceptance_criteria": ["value.txt reads after"]}))

    def run_scorer(self, script=SCRIPT, **env):
        e = {k: v for k, v in os.environ.items()
             if k not in {"AI_GATEWAY_API_KEY", "GSTACK_AIGATEWAY_ENV", "JEV_ENDPOINT"}}
        e.update(HOME=str(self.home), **env)
        r = subprocess.run(["node", str(script), str(self.packet), str(self.tmp / "DESIGN.md")],
                           env=e, capture_output=True, text=True, timeout=60)
        return r, json.loads(self.packet.read_text()).get("coverage")

    def assertNamesWhatItConsulted(self, cov):
        self.assertTrue(cov.get("consulted"), f"a {cov['status']} record must name what it consulted: {cov}")

    def test_checked_against_a_stub_gateway(self):
        r, cov = self.run_scorer(AI_GATEWAY_API_KEY="k-env", JEV_ENDPOINT=self.endpoint)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["status"], "checked")
        self.assertEqual([c["criterion_no"] for c in cov["criteria"]], [1, 2])
        self.assertEqual({c["probability"] for c in cov["criteria"]}, {0.9})
        self.assertEqual(cov["credential_source"], "env AI_GATEWAY_API_KEY")
        self.assertEqual(Stub.seen[0]["path"], "/evaluation-model")

    def test_a_missing_ai_package_records_broken_and_exits_nonzero(self):
        lone = self.tmp / "lone" / "packet_coverage.mjs"; lone.parent.mkdir()
        shutil.copy(SCRIPT, lone)              # no node_modules anywhere above it
        r, cov = self.run_scorer(script=lone, AI_GATEWAY_API_KEY="k")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(cov["status"], "broken", r.stderr)
        self.assertIn("ai", cov["why"])
        self.assertNamesWhatItConsulted(cov)

    def test_no_credential_on_any_path_is_unavailable_and_exits_zero(self):
        r, cov = self.run_scorer()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["status"], "unavailable")
        self.assertNamesWhatItConsulted(cov)
        self.assertTrue(any("aigateway.env" in c for c in cov["consulted"]), cov["consulted"])

    def test_a_named_file_that_does_not_exist_is_unusable(self):
        r, cov = self.run_scorer(GSTACK_AIGATEWAY_ENV=str(self.tmp / "nope.env"))
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(cov["status"], "unusable")
        self.assertIn(str(self.tmp / "nope.env"), cov["consulted"])

    def test_a_file_that_sets_no_key_is_unusable(self):
        f = self.tmp / "empty.env"; f.write_text("OTHER=1\n")
        r, cov = self.run_scorer(GSTACK_AIGATEWAY_ENV=str(f))
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(cov["status"], "unusable")
        self.assertIn(str(f), cov["consulted"])

    def test_a_key_on_a_last_line_with_no_newline_is_read(self):
        f = self.tmp / "aigateway.env"; f.write_bytes(NO_NEWLINE)
        self.assertEqual(len(f.read_bytes()), 79)
        self.assertFalse(f.read_bytes().endswith(b"\n"))
        r, cov = self.run_scorer(GSTACK_AIGATEWAY_ENV=str(f), JEV_ENDPOINT=self.endpoint)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["status"], "checked")
        self.assertEqual(cov["credential_source"], str(f))
        self.assertEqual(Stub.seen[0]["auth"], f"Bearer {FAKE_KEY}")

    def test_the_vault_path_is_found_under_home_on_a_mac(self):
        tail = ["Library", "CloudStorage", "GoogleDrive-someone@example.com", "Shared drives",
                "MoxyWolf Shared Files", "MoxyWolf Vault", "_Shared Knowledge", "Agents and Plugins"]
        d = self.home.joinpath(*tail); d.mkdir(parents=True)
        (d / "aigateway.env").write_bytes(NO_NEWLINE)
        r, cov = self.run_scorer(JEV_ENDPOINT=self.endpoint)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["credential_source"], str(d / "aigateway.env"))

    def test_a_set_variable_beats_a_file_with_a_different_key(self):
        f = self.tmp / "aigateway.env"; f.write_bytes(NO_NEWLINE)
        r, cov = self.run_scorer(AI_GATEWAY_API_KEY="k-env", GSTACK_AIGATEWAY_ENV=str(f), JEV_ENDPOINT=self.endpoint)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["credential_source"], "env AI_GATEWAY_API_KEY")
        self.assertEqual(Stub.seen[0]["auth"], "Bearer k-env")

    def test_a_key_the_gateway_refuses_is_unusable(self):
        Stub.status = 401
        r, cov = self.run_scorer(AI_GATEWAY_API_KEY="k-bad", JEV_ENDPOINT=self.endpoint)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(cov["status"], "unusable", r.stderr)
        self.assertNamesWhatItConsulted(cov)


    # XE-030: a declared criterion the packet carries word for word is covered with no model call.
    def use_criteria(self, crits):
        self.packet.write_text(json.dumps({"items": ["FX-001"], "acceptance_criteria": crits}))

    def test_an_all_verbatim_packet_needs_no_credential_and_no_request(self):
        self.use_criteria(["The value is after.", "The   old value\nis gone."])
        r, cov = self.run_scorer(JEV_ENDPOINT=self.endpoint)       # no key anywhere
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["status"], "checked")
        self.assertEqual((cov["verbatim"], cov["model_scored"], cov["input_tokens"]), (2, 0, 0))
        self.assertIsNone(cov["credential_source"])
        self.assertEqual({c["match"] for c in cov["criteria"]}, {"verbatim"})
        self.assertEqual(Stub.seen, [])

    def test_only_the_criterion_that_is_not_verbatim_reaches_the_model(self):
        self.use_criteria(["The value is after. It is read back from value.txt.", "value.txt no longer says before"])
        r, cov = self.run_scorer(AI_GATEWAY_API_KEY="k", JEV_ENDPOINT=self.endpoint)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([sorted(q["body"]["questions"]) for q in Stub.seen], [["c2"]])
        self.assertEqual([(c["criterion_no"], c["match"]) for c in cov["criteria"]], [(1, "verbatim"), (2, "model")])
        self.assertEqual(cov["criteria"][0]["probability"], 1)

    def test_a_paraphrase_is_not_verbatim(self):
        self.use_criteria(["The value reads after.", "The old value is removed."])
        r, cov = self.run_scorer(AI_GATEWAY_API_KEY="k", JEV_ENDPOINT=self.endpoint)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(Stub.seen[0]["body"]["questions"]), ["c1", "c2"])
        self.assertEqual(cov["verbatim"], 0)

    def test_a_verbatim_packet_still_needs_the_model_when_one_criterion_is_missing(self):
        self.use_criteria(["The value is after."])
        r, cov = self.run_scorer()                                    # no key: the model is needed
        self.assertEqual(cov["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
