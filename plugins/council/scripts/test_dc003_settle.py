#!/usr/bin/env python3
"""DC-003 criterion 7: offline subprocess settlement and persisted accounting.

Run with python3 plugins/council/scripts/test_dc003_settle.py.
Only the HTTP gateway is a stub; ask, budget init/show, and files are real.
"""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("decider_council.py")
VOICES = (
    "typesafe-ai/jev",
    "perplexity/pplx-decider-v1.2",
    "openai/gpt-6-luna-decisions",
)
CEILING = 0.05  # Each case starts with an empty ledger.


class SettlementStub(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        model = body["model"]
        if model in self.server.slow:
            self.server.release.wait(5)
        status = 500 if model in self.server.failed else 200
        payload = {"error": {"message": "down"}} if status == 500 else {
            "model": model,
            "answers": [{"type": "predicate", "name": q["name"], "probability": 0.8}
                        for q in body["questions"]],
            "usage": {"input_tokens": 10, "output_tokens": 0},
            "provider_metadata": {"gateway": {"cost": self.server.costs[model]}},
        }
        raw = json.dumps(payload).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A timed-out client has already closed its connection.

    def log_message(self, *args):
        pass


def start_stub():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SettlementStub)
    server.costs = {model: "0.00001" for model in VOICES}
    server.slow = set()
    server.failed = set()
    server.release = threading.Event()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class DC003Settlement(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dc003-settle-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.server, self.thread = start_stub()
        self.addCleanup(self.stop_stub)
        self.budget = self.root / "budget.json"
        self.pricing = self.root / "pricing.json"
        self.run_id = "settlement-test"
        (self.root / "input.txt").write_text("the thing under decision")
        (self.root / "questions.json").write_text(json.dumps([
            {"type": "predicate", "name": "risky", "instructions": "Is it risky?"}
        ]))
        (self.root / "key.env").write_text("AI_GATEWAY_API_KEY=offline-test-key\n")
        self.pricing.write_text(json.dumps({"data": [
            {"id": model, "pricing": {"input": "0.000001", "output": "0.000001"}}
            for model in VOICES
        ]}))
        # Do not inherit real credentials, gateway settings, proxies, or kill-test hooks.
        self.env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT")
                    if key in os.environ}
        self.env.update(
            PYTHONDONTWRITEBYTECODE="1",
            GSTACK_COUNCIL_AIGATEWAY_ENV=str(self.root / "key.env"),
            GSTACK_AIGATEWAY_ENV=str(self.root / "missing.env"),
            GSTACK_PEER_REVIEW_DIR=str(self.root / "reviews"),
            GSTACK_DECIDERS=",".join(VOICES),
            JEV_ENDPOINT=f"http://127.0.0.1:{self.server.server_address[1]}",
            NO_PROXY="127.0.0.1,localhost",
        )

    def stop_stub(self):
        self.server.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def run_dc(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=self.root, env=self.env,
            capture_output=True, text=True, timeout=15,
        )

    def check_settlement(self, cost, state="settled", settled=None, failure=None):
        """Check all three observable records after one budgeted ask."""
        self.server.costs[VOICES[0]] = cost
        if failure == "timeout":
            self.server.slow.add(VOICES[0])
        elif failure == "500":
            self.server.failed.add(VOICES[0])
        init = self.run_dc(
            "budget", "init", "--budget", str(self.budget), "--run", self.run_id,
            "--limit-usd", "1", "--key-id", "offline-key-id",
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        result = self.run_dc(
            "ask", "--caller", "dc003-test", "--ref", "settle",
            "--input", str(self.root / "input.txt"),
            "--questions", str(self.root / "questions.json"),
            "--budget", str(self.budget), "--run", self.run_id,
            "--pricing", str(self.pricing), "--timeout-ms", "500",
        )
        self.assertEqual(result.returncode, 5 if state == "ceiling_exceeded" else 0,
                         result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["answers"]["risky"]["majority"], 0.8,
                         "answers must still be printed after settlement")
        lines = [json.loads(line)
                 for path in (self.root / "reviews" / "decisions").glob("*.jsonl")
                 for line in path.read_text().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        stdout_rows = {row["model"]: row for row in output["voices"]}
        ledger_rows = {row["model"]: row for row in lines[0]["voices"]}
        self.assertEqual(len(output["voices"]), len(VOICES))
        self.assertEqual(len(lines[0]["voices"]), len(VOICES))
        self.assertEqual(set(stdout_rows), set(VOICES))
        self.assertEqual(set(ledger_rows), set(VOICES))
        budget = json.loads(self.budget.read_text())
        self.assertEqual(len(budget["reservations"]), len(VOICES))
        reservations = {row["voice"]: row for row in budget["reservations"]}
        self.assertEqual(set(reservations), set(VOICES))
        target_charge = float(cost) if settled is None else settled
        charges = {model: target_charge if model == VOICES[0] else 0.00001
                   for model in VOICES}
        for model in VOICES:
            with self.subTest(voice=model):
                for row in (stdout_rows[model], ledger_rows[model], reservations[model]):
                    self.assertAlmostEqual(row["reserved_usd"], CEILING)
                    self.assertAlmostEqual(row["settled_usd"], charges[model])
                self.assertEqual(reservations[model]["state"],
                                 state if model == VOICES[0] else "settled")
                if model != VOICES[0] or failure is None:
                    # JSON serialization distinguishes false from 0 and strings from numbers.
                    self.assertEqual(json.dumps(ledger_rows[model]["cost"], sort_keys=True),
                                     json.dumps(self.server.costs[model], sort_keys=True))
        if failure is not None:
            self.assertIn("unavailable", stdout_rows[VOICES[0]])
        total = sum(charges.values())
        shown = self.run_dc("budget", "show", "--budget", str(self.budget),
                            "--run", self.run_id)
        self.assertEqual(shown.returncode, 0, shown.stdout + shown.stderr)
        balance = json.loads(shown.stdout)
        self.assertEqual(balance["run"], self.run_id)
        self.assertAlmostEqual(balance["limit_usd"], 1)
        self.assertAlmostEqual(balance["open_usd"], 0)
        self.assertAlmostEqual(balance["settled_usd"], total)
        self.assertAlmostEqual(balance["left_usd"], 1 - total)
        self.assertEqual(output["budget"]["run"], self.run_id)
        self.assertAlmostEqual(output["budget"]["left_usd"], 1 - total)

    def test_c7_json_number_settles_at_reported_cost(self):
        self.check_settlement(0.0125)

    def test_c7_decimal_string_settles_at_reported_cost(self):
        self.check_settlement("0.00001")

    def test_c7_null_kept_unknown_at_full_ceiling(self):
        self.check_settlement(None, "kept_unknown", CEILING)

    def test_c7_negative_number_kept_unknown_at_full_ceiling(self):
        self.check_settlement(-0.001, "kept_unknown", CEILING)

    def test_c7_negative_string_kept_unknown_at_full_ceiling(self):
        self.check_settlement("-0.001", "kept_unknown", CEILING)

    def test_c7_boolean_kept_unknown_at_full_ceiling(self):
        self.check_settlement(True, "kept_unknown", CEILING)

    def test_c7_non_numeric_string_kept_unknown_at_full_ceiling(self):
        self.check_settlement("not-a-price", "kept_unknown", CEILING)

    def test_c7_object_kept_unknown_at_full_ceiling(self):
        self.check_settlement({"amount": "0.00001"}, "kept_unknown", CEILING)

    def test_c7_timeout_voice_kept_unknown_at_full_ceiling(self):
        self.check_settlement("0.00001", "kept_unknown", CEILING, failure="timeout")

    def test_c7_http_500_voice_kept_unknown_at_full_ceiling(self):
        self.check_settlement("0.00001", "kept_unknown", CEILING, failure="500")

    def test_c7_ceiling_exceeded_exits_5_and_prints_answers(self):
        self.check_settlement(0.075, "ceiling_exceeded")

    def check_malformed_envelope_cost(self, cost):
        class MalformedEnvelopeStub(SettlementStub):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                raw = json.dumps({
                    "answers": 7,
                    "provider_metadata": {
                        "gateway": {"cost": self.server.costs[body["model"]]},
                    },
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.server.RequestHandlerClass = MalformedEnvelopeStub
        self.server.costs[VOICES[0]] = cost
        init = self.run_dc(
            "budget", "init", "--budget", str(self.budget), "--run", self.run_id,
            "--limit-usd", "1", "--key-id", "offline-key-id",
        )
        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        result = self.run_dc(
            "ask", "--caller", "dc003-test", "--ref", "malformed-envelope",
            "--input", str(self.root / "input.txt"),
            "--questions", str(self.root / "questions.json"),
            "--voices", VOICES[0], "--budget", str(self.budget),
            "--run", self.run_id, "--pricing", str(self.pricing),
            "--timeout-ms", "500",
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        lines = [json.loads(line)
                 for path in (self.root / "reviews" / "decisions").glob("*.jsonl")
                 for line in path.read_text().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        reservations = json.loads(self.budget.read_text())["reservations"]
        self.assertEqual(len(reservations), 1)
        self.assertEqual(reservations[0]["voice"], VOICES[0])
        self.assertEqual(reservations[0]["state"], "settled")
        self.assertAlmostEqual(reservations[0]["settled_usd"], 0.012)
        for source, record in (("stdout", output), ("ledger", lines[0])):
            with self.subTest(source=source):
                self.assertEqual(len(record["voices"]), 1)
                row = record["voices"][0]
                self.assertEqual(row["model"], VOICES[0])
                self.assertEqual(row["status"], 200)
                self.assertIn("unavailable", row)
                self.assertEqual(row["budget_state"], "settled")
                self.assertAlmostEqual(row["reserved_usd"], CEILING)
                self.assertAlmostEqual(row["settled_usd"], 0.012)
                self.assertEqual(json.dumps(row["cost"]), json.dumps(cost))

    def test_rf3_malformed_envelope_preserves_decimal_string_cost(self):
        self.check_malformed_envelope_cost("0.012")

    def test_rf3_malformed_envelope_preserves_numeric_cost(self):
        self.check_malformed_envelope_cost(0.012)

    def test_rf11_score_survives_unusable_raw_costs_kept_on_the_ledger(self):
        # review 20261120-150642 F11: a raw cost kept as received (object, non-numeric string) must not break `score`
        for cost in ({"amount": "0.012"}, "abc"):
            with self.subTest(cost=cost):
                self.server.costs[VOICES[0]] = cost
                self.server.RequestHandlerClass = self._malformed_stub()
                self.budget.unlink(missing_ok=True)
                init = self.run_dc("budget", "init", "--budget", str(self.budget), "--run", self.run_id,
                                   "--limit-usd", "1", "--key-id", "offline-key-id")
                self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
                ask = self.run_dc("ask", "--caller", "dc003-test", "--ref", "f11", "--input", str(self.root / "input.txt"),
                                  "--questions", str(self.root / "questions.json"), "--voices", VOICES[0],
                                  "--budget", str(self.budget), "--run", self.run_id, "--pricing", str(self.pricing),
                                  "--timeout-ms", "500")
                self.assertEqual(ask.returncode, 1, ask.stdout + ask.stderr)
                row = json.loads(ask.stdout)["voices"][0]
                self.assertEqual(json.dumps(row["cost"]), json.dumps(cost))
                self.assertEqual(row["budget_state"], "kept_unknown")
                score = self.run_dc("score", "--caller", "dc003-test")
                self.assertEqual(score.returncode, 0, score.stdout + score.stderr)
                self.assertNotIn("Traceback", score.stderr)

    def _malformed_stub(self):
        class MalformedEnvelopeStub(SettlementStub):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                raw = json.dumps({"answers": 7, "provider_metadata": {"gateway": {"cost": self.server.costs[body["model"]]}}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        return MalformedEnvelopeStub

    def test_rr1_oversized_integer_cost_is_unknown_not_a_crash(self):
        # review 20261120-161648 F1: float() of a 401-digit JSON integer overflows; it must be kept_unknown
        for cost in (-(10 ** 400), 10 ** 400):
            with self.subTest(sign="negative" if cost < 0 else "positive"):
                self.server.costs[VOICES[0]] = cost
                self.server.RequestHandlerClass = self._malformed_stub()
                self.budget.unlink(missing_ok=True)
                init = self.run_dc("budget", "init", "--budget", str(self.budget), "--run", self.run_id,
                                   "--limit-usd", "1", "--key-id", "offline-key-id")
                self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
                args = ("ask", "--caller", "dc003-test", "--ref", "rr1", "--input", str(self.root / "input.txt"),
                        "--questions", str(self.root / "questions.json"), "--voices", VOICES[0],
                        "--budget", str(self.budget), "--run", self.run_id, "--pricing", str(self.pricing), "--timeout-ms", "500")
                first = self.run_dc(*args)          # the response carries the oversized cost
                self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
                self.assertNotIn("Traceback", first.stderr)
                row = json.loads(first.stdout)["voices"][0]
                self.assertEqual(row["budget_state"], "kept_unknown")
                self.assertEqual(row["cost"], cost)
                second = self.run_dc(*args)         # now the ledger history carries it too
                self.assertNotIn("Traceback", second.stderr)
                self.assertEqual(second.returncode, 1, second.stdout + second.stderr)


if __name__ == "__main__":
    unittest.main()
