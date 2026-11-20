#!/usr/bin/env python3
"""DC-003.3/4 black-box tests; only loopback HTTP and temporary fixture files.

Run with python3 plugins/council/scripts/test_dc003_pricing.py.
The budget and ledger fixtures use CONTRACT.md's public formats.
"""
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest


SCRIPT = Path(__file__).resolve().with_name("decider_council.py")
MODELS = (
    "typesafe-ai/jev",
    "perplexity/pplx-decider-v1.2",
    "openai/gpt-6-luna-decisions",
)
KEY = "dc003-pricing-offline-test-key"


class PricingStub(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.gets.append(self.path)
        self.send_json(503, {"error": {"message": "pricing unavailable"}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.posts.append((self.path, body))
        self.send_json(200, {
            "model": body["model"],
            "answers": [
                {"type": "predicate", "name": q["name"], "probability": 0.2}
                for q in body["questions"]
            ],
            "usage": {"input_tokens": 10, "output_tokens": 0},
            "provider_metadata": {"gateway": {"cost": "0.00001"}},
        })

    def send_json(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class DC003Pricing(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dc003-pricing-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), PricingStub)
        self.server.posts, self.server.gets = [], []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"
        self.ledger = self.root / "reviews" / "decisions"
        self.ledger.mkdir(parents=True)
        self.pricing = self.root / "pricing.json"
        self.budget = self.root / "budget.json"
        self.key_file = self.root / "council.env"
        self.key_file.write_text(f"AI_GATEWAY_API_KEY={KEY}\n")
        self.budget.write_text(json.dumps({
            "run": "pricing-test", "limit_usd": 1.0,
            "key_id": "offline-key-id",
            "key_sha256": hashlib.sha256(KEY.encode()).hexdigest(),
            "reservations": [],
        }))
        (self.root / "input.txt").write_text("A small offline decision.")
        (self.root / "questions.json").write_text(json.dumps([
            {"type": "predicate", "name": "risky", "instructions": "Is it risky?"},
        ]))
        self.write_prices()

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def write_prices(self, overrides=None, missing=()):
        overrides = overrides or {}
        self.pricing.write_text(json.dumps({"data": [
            {"id": model, "pricing": overrides.get(model, {
                "input": "0.000001", "output": "0.000002",
            })}
            for model in MODELS if model not in missing
        ]}))

    def history(self, filename, rows):
        """Append ledger history, including legacy rows with only a cost field."""
        with (self.ledger / filename).open("a") as stream:
            for index, voices in enumerate(rows):
                stream.write(json.dumps({
                    "id": f"history-{filename}-{index}",
                    "ts": "2026-10-18T00:00:00+00:00",
                    "caller": "other-caller", "ref": "historical",
                    "questions": [], "answers": {}, "voices": voices,
                    "quorum": "full", "outcome": None,
                }) + "\n")

    def ask(self, expected_exit=0):
        # An allowlist keeps real credentials, proxies, and pause hooks out.
        env = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(self.root), "TMPDIR": str(self.root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GSTACK_COUNCIL_AIGATEWAY_ENV": str(self.key_file),
            "GSTACK_AIGATEWAY_ENV": str(self.root / "missing.env"),
            "GSTACK_PEER_REVIEW_DIR": str(self.root / "reviews"),
            "GSTACK_DECIDERS": ",".join(MODELS),
            "JEV_ENDPOINT": self.endpoint,
        }
        result = subprocess.run([
            sys.executable, str(SCRIPT), "ask", "--caller", "pricing-test",
            "--ref", "fixture", "--input", str(self.root / "input.txt"),
            "--questions", str(self.root / "questions.json"),
            "--budget", str(self.budget), "--run", "pricing-test",
            "--pricing", str(self.pricing), "--timeout-ms", "1500",
        ], cwd=self.root, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, expected_exit,
                         f"stdout={result.stdout}\nstderr={result.stderr}")
        return json.loads(result.stdout)

    def assert_ceilings(self, output, expected):
        self.assertCountEqual(
            [body["model"] for _, body in self.server.posts], MODELS)
        rows = {row["model"]: row for row in output["voices"]}
        for model, amount in expected.items():
            self.assertAlmostEqual(float(rows[model]["reserved_usd"]), amount)
        ledger_rows = [
            json.loads(line)
            for path in self.ledger.glob("*.jsonl")
            for line in path.read_text().splitlines() if line.strip()
        ]
        saved = [row for row in ledger_rows if row["id"] == output["id"]]
        self.assertEqual(len(saved), 1)
        saved_voices = {row["model"]: row for row in saved[0]["voices"]}
        for model, amount in expected.items():
            self.assertAlmostEqual(float(saved_voices[model]["reserved_usd"]), amount)

    def assert_voice_refused(self, output, model, reason):
        rows = {row["model"]: row for row in output["voices"]}
        self.assertEqual(rows[model]["unavailable"], reason)
        self.assertEqual(rows[model]["reserved_usd"], 0)
        self.assertCountEqual(
            [body["model"] for _, body in self.server.posts],
            [other for other in MODELS if other != model],
        )

    def test_c3_ceiling_twice_largest_settled_charge_per_model(self):
        self.history("202609.jsonl", [[
            {"model": MODELS[0], "settled_usd": 0.03, "cost": "0.4"},
            {"model": MODELS[1], "cost": "0.012"},
            {"model": MODELS[2], "settled_usd": 0.018, "cost": None},
            {"model": "unselected/model", "cost": "0.4"},
        ]])
        self.history("202610.jsonl", [[
            {"model": MODELS[0], "settled_usd": 0.02, "cost": "0.02"},
            {"model": MODELS[1], "cost": 0.006},
            {"model": MODELS[2], "cost": "0.010"},
        ], [
            {"model": model, "cost": "0.3", "unavailable": "no_price"}
            for model in MODELS
        ]])
        self.assert_ceilings(self.ask(), dict(zip(MODELS, (0.06, 0.024, 0.036))))

    def test_c3_ceiling_has_one_cent_floor_including_zero_history(self):
        self.history("202610.jsonl", [[
            {"model": model, "cost": cost}
            for model, cost in zip(MODELS, (0, "0.001", 0.005))
        ]])
        self.assert_ceilings(self.ask(), dict.fromkeys(MODELS, 0.01))

    def test_c3_kept_unknown_history_does_not_raise_the_ceiling(self):
        # spec review DC-003 A1: a voice kept at its full ceiling is a stand-in, not a charge
        self.history("202610.jsonl", [[
            {"model": MODELS[0], "settled_usd": 0.4, "reserved_usd": 0.4, "budget_state": "kept_unknown", "cost": None},
            {"model": MODELS[0], "settled_usd": 0.004, "budget_state": "settled", "cost": "0.004"},
        ]])
        self.assert_ceilings(self.ask(), {MODELS[0]: 0.01, MODELS[1]: 0.05, MODELS[2]: 0.05})

    def test_c3_ceiling_defaults_to_five_cents_without_settled_history(self):
        self.history("202610.jsonl", [[
            {"model": MODELS[1], "cost": invalid}
            for invalid in (None, -1, True, "not-a-cost", {}, "NaN", "Infinity")
        ], [
            {"model": MODELS[2], "cost": "0.3", "unavailable": "no_price"},
        ]])
        self.assert_ceilings(self.ask(), dict.fromkeys(MODELS, 0.05))

    def test_c3_ceiling_reads_new_ledger_history_at_call_time(self):
        self.assert_ceilings(self.ask(), dict.fromkeys(MODELS, 0.05))
        self.history("202609.jsonl", [[
            {"model": model, "settled_usd": charge, "cost": charge}
            for model, charge in zip(MODELS, (0.02, 0.03, 0.04))
        ]])
        self.server.posts.clear()
        self.assert_ceilings(self.ask(), dict(zip(MODELS, (0.04, 0.06, 0.08))))

    def test_c3_missing_model_is_no_price_and_not_sent(self):
        self.write_prices(missing=(MODELS[1],))
        self.assert_voice_refused(self.ask(), MODELS[1], "no_price")

    def test_c3_malformed_pricing_is_no_price_and_not_sent(self):
        for malformed in (None, [], "invalid", {}, {"output": "0.000002"},
                          {"input": "not-a-number"}, {"input": None}):
            with self.subTest(pricing=malformed):
                self.server.posts.clear()
                self.write_prices(overrides={MODELS[1]: malformed})
                self.assert_voice_refused(self.ask(), MODELS[1], "no_price")

    def test_c4_web_search_fee_is_unbounded_and_voice_not_sent(self):
        self.write_prices(overrides={MODELS[1]: {
            "input": "0.000001", "output": "0.000002", "web_search": "0.005",
        }})
        self.assert_voice_refused(self.ask(), MODELS[1], "unbounded_fee:web_search")

    def test_c4_unreadable_pricing_and_failed_models_endpoint_refuse_call(self):
        self.pricing.unlink()
        output = self.ask(expected_exit=4)
        self.assertEqual(output["refused"], "pricing_unavailable")
        self.assertEqual(self.server.posts, [], "pricing failure must prevent dispatch")
        self.assertIn("/v1/models", self.server.gets)


if __name__ == "__main__":
    unittest.main()
