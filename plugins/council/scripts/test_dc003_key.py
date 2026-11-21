#!/usr/bin/env python3
"""DC-003 criteria 1 and 2: offline CLI compatibility and run-key isolation.

Run with python3 plugins/council/scripts/test_dc003_key.py. The implementation
is exercised only through subprocesses; credentials and pricing are fixtures.
"""
import hashlib
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
SCRIPT = HERE / "decider_council.py"
VOICES = ["typesafe-ai/jev", "openai/gpt-6-luna-decisions"]
RUN = "dc003-key-fixture"
KEY_ID = "fixture-key-id"
RUN_KEY = "fake-only-dc003-dedicated-key-12345"
OTHER_KEY = "fake-only-dc003-replacement-key-67890"
AMBIENT_KEY = "fake-only-dc003-ambient-key-24680"
FALLBACK_KEY = "fake-only-dc003-fallback-key-13579"
QUESTIONS = [
    {"type": "predicate", "name": "risky", "instructions": "Is it risky?"},
    {"type": "choice", "name": "lane", "instructions": "Which lane?",
     "choices": [{"value": "a"}, {"value": "b"}, {"value": "c"}]},
    {"type": "score", "name": "size", "instructions": "How big?",
     "levels": [{"label": "s"}, {"label": "m"}, {"label": "l"}]},
]


class Stub(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with self.server.seen_lock:
            self.server.seen.append((self.path, self.headers.get("Authorization"), body))
        raw = json.dumps({
            "model": body["model"],
            "answers": [
                {"type": "predicate", "name": "risky", "probability": 0.8},
                {"type": "choice", "name": "lane", "choice": "b", "confidence": 0.9},
                {"type": "score", "name": "size", "score": 2, "confidence": 0.9},
            ],
            "usage": {"input_tokens": 10, "output_tokens": 0},
            "provider_metadata": {"gateway": {"cost": "0.00001"}},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        with self.server.seen_lock:
            self.server.seen.append((self.path, self.headers.get("Authorization"), None))
        self.send_error(404, "Use the offline pricing fixture")

    def log_message(self, *args):
        pass


class DC003Key(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dc003-key-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.budget = self.root / "budget.json"
        self.key_file = self.root / "council.env"
        self.key_file.write_text(f"AI_GATEWAY_API_KEY={RUN_KEY}\n")
        fallback = self.root / "fallback.env"
        fallback.write_text(f"AI_GATEWAY_API_KEY={FALLBACK_KEY}\n")
        (self.root / "input.txt").write_text("the thing under decision")
        (self.root / "questions.json").write_text(json.dumps(QUESTIONS))
        self.pricing = self.root / "pricing.json"
        self.pricing.write_text(json.dumps({"data": [
            {"id": model, "pricing": {"input": "0.000001", "output": "0.000002"}}
            for model in VOICES
        ]}))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        self.server.seen = []
        self.server.seen_lock = threading.Lock()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_stub)
        # An explicit child environment prevents inherited credentials, proxy
        # settings, or crash-test hooks from affecting this offline fixture.
        self.env = {
            "PATH": os.defpath,
            "TMPDIR": str(self.root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "AI_GATEWAY_API_KEY": AMBIENT_KEY,
            "GSTACK_AIGATEWAY_ENV": str(fallback),
            "GSTACK_COUNCIL_AIGATEWAY_ENV": str(self.key_file),
            "GSTACK_DECIDERS": ",".join(VOICES),
            "GSTACK_PEER_REVIEW_DIR": str(self.root / "reviews"),
            "JEV_ENDPOINT": f"http://127.0.0.1:{self.server.server_port}",
        }

    def stop_stub(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def run_script(self, script, *args, timeout=30):
        result = subprocess.run(
            [sys.executable, "-B", str(script), *map(str, args)],
            env=self.env, cwd=self.root, capture_output=True, text=True,
            timeout=timeout,
        )
        self.assert_secrets_absent(result)
        return result

    def run_dc(self, *args):
        return self.run_script(SCRIPT, *args)

    def ask(self, *flags):
        return self.run_dc(
            "ask", "--caller", "dc003-key", "--ref", "fixture",
            "--input", self.root / "input.txt",
            "--questions", self.root / "questions.json",
            "--pricing", self.pricing, *flags,
        )

    def budgeted_ask(self):
        return self.ask("--budget", self.budget, "--run", RUN)

    def init_budget(self):
        result = self.run_dc(
            "budget", "init", "--budget", self.budget, "--run", RUN,
            "--limit-usd", "1", "--key-id", KEY_ID,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def assert_secrets_absent(self, result):
        artifacts = {"stdout": result.stdout, "stderr": result.stderr}
        if self.budget.exists():
            artifacts["budget"] = self.budget.read_text()
        for ledger in (self.root / "reviews" / "decisions").glob("*.jsonl"):
            artifacts[str(ledger)] = ledger.read_text()
        for location, content in artifacts.items():
            for key in (RUN_KEY, OTHER_KEY, AMBIENT_KEY, FALLBACK_KEY):
                self.assertNotIn(key, content, f"credential leaked into {location}")

    def assert_refused(self, result, reason):
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["refused"], reason)
        self.assertEqual(self.server.seen, [], "a refused operation sent a request")

    def test_c1_unbudgeted_ask_preserves_existing_answers_and_ledger(self):
        # The dedicated file must be irrelevant to an unbudgeted call.
        self.key_file.unlink()
        result = self.ask()
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["quorum"], "full")
        self.assertEqual(len(out["voices"]), 2)
        for name, majority in (("risky", 0.8), ("lane", "b"), ("size", 2)):
            self.assertEqual(out["answers"][name]["majority"], majority)
            self.assertTrue(out["answers"][name]["agreed"])
        self.assertFalse(out["answers"]["lane"]["tie"])
        self.assertTrue(all(v["cost"] == "0.00001" for v in out["voices"]))
        self.assertEqual(sorted(row[2]["model"] for row in self.server.seen), sorted(VOICES))
        self.assertTrue(all(row[0] == "/v1/decisions" for row in self.server.seen))
        lines = [json.loads(line)
                 for file in (self.root / "reviews" / "decisions").glob("*.jsonl")
                 for line in file.read_text().splitlines() if line]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["id"], out["id"])
        self.assertEqual(lines[0]["answers"], out["answers"])
        self.assertIsNone(lines[0]["outcome"])

    def test_c1_existing_suite_and_jev_selftest_still_pass_as_subprocesses(self):
        for script, args in ((HERE / "test_decider_council.py", ()),
                             (HERE / "jev_route.py", ("--selftest",))):
            with self.subTest(script=script.name):
                result = self.run_script(script, *args, timeout=180)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_c1_budget_and_run_are_required_together(self):
        for flags in (("--budget", self.budget), ("--run", RUN)):
            with self.subTest(flag=flags[0]):
                result = self.ask(*flags)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("error:", result.stderr)
                self.assertEqual(self.server.seen, [])

    def test_c2_missing_council_env_variable_refuses_without_fallback(self):
        self.init_budget()
        del self.env["GSTACK_COUNCIL_AIGATEWAY_ENV"]
        self.assert_refused(self.budgeted_ask(), "budget_key_missing")

    def test_c2_missing_council_env_file_refuses_without_fallback(self):
        self.init_budget()
        self.key_file.unlink()
        self.assert_refused(self.budgeted_ask(), "budget_key_missing")

    def test_c2_council_env_file_without_key_refuses_without_fallback(self):
        self.init_budget()
        self.key_file.write_text("UNRELATED_VARIABLE=fixture\n")
        self.assert_refused(self.budgeted_ask(), "budget_key_missing")

    def test_c2_init_requires_the_dedicated_key(self):
        for case in ("missing_variable", "missing_file", "no_key"):
            with self.subTest(case=case):
                self.env["GSTACK_COUNCIL_AIGATEWAY_ENV"] = str(self.key_file)
                self.key_file.write_text(f"AI_GATEWAY_API_KEY={RUN_KEY}\n")
                self.budget = self.root / f"{case}.json"
                if case == "missing_variable":
                    del self.env["GSTACK_COUNCIL_AIGATEWAY_ENV"]
                elif case == "missing_file":
                    self.key_file.unlink()
                else:
                    self.key_file.write_text("UNRELATED_VARIABLE=fixture\n")
                result = self.run_dc(
                    "budget", "init", "--budget", self.budget, "--run", RUN,
                    "--limit-usd", "1", "--key-id", KEY_ID,
                )
                self.assert_refused(result, "budget_key_missing")

    def test_rf4_init_empty_key_refuses_without_creating_budget(self):
        for case, value in (("double_quotes", '\"\"'), ("single_quotes", "''"),
                            ("spaces", "   ")):
            with self.subTest(case=case):
                self.key_file.write_text(f"AI_GATEWAY_API_KEY={value}\n")
                self.budget = self.root / f"{case}.json"
                result = self.run_dc(
                    "budget", "init", "--budget", self.budget, "--run", RUN,
                    "--limit-usd", "1", "--key-id", KEY_ID,
                )
                self.assert_refused(result, "budget_key_missing")
                self.assertFalse(self.budget.exists(), "refused init created a budget")

    def test_rf4_ask_empty_key_refuses_as_missing_and_sends_nothing(self):
        self.init_budget()
        for case, value in (("double_quotes", '\"\"'), ("single_quotes", "''"),
                            ("spaces", "   ")):
            with self.subTest(case=case):
                self.key_file.write_text(f"AI_GATEWAY_API_KEY={value}\n")
                self.assert_refused(self.budgeted_ask(), "budget_key_missing")

    def test_c2_changed_key_mismatches_the_init_hash_and_sends_nothing(self):
        self.init_budget()
        budget = json.loads(self.budget.read_text())
        self.assertEqual(budget["key_id"], KEY_ID)
        self.assertEqual(budget["key_sha256"], hashlib.sha256(RUN_KEY.encode()).hexdigest())
        self.key_file.write_text(f"AI_GATEWAY_API_KEY={OTHER_KEY}\n")
        self.assert_refused(self.budgeted_ask(), "budget_key_mismatch")

    def test_c2_bearer_token_comes_from_council_file_not_ambient_key(self):
        self.init_budget()
        result = self.budgeted_ask()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sorted(row[2]["model"] for row in self.server.seen), sorted(VOICES))
        for path, authorization, _ in self.server.seen:
            self.assertEqual(path, "/v1/decisions")
            self.assertEqual(authorization, f"Bearer {RUN_KEY}")
            self.assertNotIn(AMBIENT_KEY, authorization)
            self.assertNotIn(FALLBACK_KEY, authorization)

    def test_c2_key_never_appears_in_output_ledger_or_budget(self):
        self.init_budget()
        result = self.budgeted_ask()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        ledgers = list((self.root / "reviews" / "decisions").glob("*.jsonl"))
        self.assertTrue(ledgers, "successful ask must write a ledger")
        self.assertTrue(any(file.read_text().strip() for file in ledgers))
        self.assertTrue(self.budget.exists())
        # run_script checks every command's stdout/stderr and both artifacts,
        # including init and all missing-key/mismatch paths in the other tests.
        self.assert_secrets_absent(result)
        shown = self.run_dc("budget", "show", "--budget", self.budget, "--run", RUN)
        self.assertEqual(shown.returncode, 0, shown.stdout + shown.stderr)


if __name__ == "__main__":
    unittest.main()
