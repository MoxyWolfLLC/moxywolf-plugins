#!/usr/bin/env python3
"""DC-003 criterion 8: SIGKILL and recovery through the public budget CLI.

Run with python3 plugins/council/scripts/test_dc003_crash.py. Only a loopback
HTTP stub, temporary files, saved pricing, and a synthetic key are used.
"""
import http.server
import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("decider_council.py")
VOICES = ("typesafe-ai/jev", "openai/gpt-6-luna-decisions")
CEILING = 0.05
COST = 0.012
LIMIT = 0.20


class Stub(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with self.server.seen_lock:
            self.server.seen.append(body["model"])
            if set(self.server.seen) == set(VOICES):
                self.server.dispatched.set()
        raw = json.dumps({
            "model": body["model"],
            "answers": [{"type": "predicate", "name": q["name"],
                         "probability": 0.8} for q in body["questions"]],
            "usage": {"input_tokens": 10, "output_tokens": 0},
            "provider_metadata": {"gateway": {"cost": str(COST)}},
        }).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass  # SIGKILL may close an in-flight response.

    def log_message(self, *args):
        pass


class CrashRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        cls.server.seen_lock = threading.Lock()
        cls.server.seen = []
        cls.server.dispatched = threading.Event()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dc003-crash-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.budget = self.root / "budget.json"
        self.run_id = "crash-run"
        self.key = self.root / "key.env"
        self.key.write_text("AI_GATEWAY_API_KEY=synthetic-offline-key\n")
        (self.root / "input.txt").write_text("A local crash recovery fixture.")
        (self.root / "questions.json").write_text(json.dumps([
            {"type": "predicate", "name": "risky", "instructions": "Is it risky?"}
        ]))
        self.pricing = self.root / "pricing.json"
        self.pricing.write_text(json.dumps({"data": [
            {"id": voice, "pricing": {"input": "0.000001", "output": "0"}}
            for voice in VOICES
        ]}))
        # Whitelist the subprocess environment so host credentials and proxies
        # cannot leak into this offline fixture; HOME also points to the fixture.
        self.env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT") if k in os.environ}
        self.env.update(
            HOME=str(self.root), TMPDIR=str(self.root),
            PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
            JEV_ENDPOINT=self.endpoint, GSTACK_DECIDERS=",".join(VOICES),
            GSTACK_COUNCIL_AIGATEWAY_ENV=str(self.key),
            GSTACK_AIGATEWAY_ENV=str(self.key),
            GSTACK_PEER_REVIEW_DIR=str(self.root / "reviews"),
        )
        with self.server.seen_lock:
            self.server.seen.clear()
        self.server.dispatched.clear()
        self.cli("init", "--limit-usd", str(LIMIT), "--key-id", "offline-key-id")

    def cli(self, operation, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "budget", operation,
             "--budget", str(self.budget), "--run", self.run_id, *args],
            env=self.env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        if operation != "init":
            return json.loads(result.stdout)

    def kill_at(self, phase):
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), "ask", "--caller", "dc003-crash",
             "--ref", phase, "--input", str(self.root / "input.txt"),
             "--questions", str(self.root / "questions.json"),
             "--budget", str(self.budget), "--run", self.run_id,
             "--pricing", str(self.pricing)],
            env={**self.env, "GSTACK_DC003_PAUSE": phase},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stderr = b""
        try:
            deadline = time.monotonic() + 15
            marker = f"paused:{phase}".encode()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stderr, selectors.EVENT_READ)
                while marker not in stderr.splitlines():
                    remaining = deadline - time.monotonic()
                    self.assertGreater(remaining, 0, f"Pause not reached: {stderr!r}")
                    if not selector.select(timeout=remaining):
                        self.fail(f"Pause not reached: {stderr!r}")
                    chunk = os.read(process.stderr.fileno(), 4096)
                    self.assertTrue(chunk, f"ask exited before pause: {stderr!r}")
                    stderr += chunk
            if phase != "after_reserve":
                self.assertTrue(self.server.dispatched.wait(5),
                                "Both voices must reach the stub before the dispatch crash")
            process.send_signal(signal.SIGKILL)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, -signal.SIGKILL)
            return process.pid
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
            process.stdout.close()
            process.stderr.close()

    def reservations(self):
        budget = json.loads(self.budget.read_text())
        self.assertEqual(budget["run"], self.run_id)
        self.assertEqual(budget["limit_usd"], LIMIT)
        rows = budget["reservations"]
        self.assertEqual(len(rows), len(VOICES), "Charge was lost or duplicated")
        by_id = {(r["line"], r["voice"]): r for r in rows}
        self.assertEqual(len(by_id), len(rows), "Duplicate reservation identities")
        return by_id

    def assert_accounting(self, rows, expected_open, expected_settled):
        open_sum = sum(r["reserved_usd"] for r in rows.values() if r["state"] == "open")
        settled_sum = sum(r["settled_usd"] for r in rows.values() if r["state"] != "open")
        self.assertAlmostEqual(open_sum, expected_open)
        self.assertAlmostEqual(settled_sum, expected_settled)
        shown = self.cli("show")
        self.assertEqual(shown["run"], self.run_id)
        self.assertEqual(shown["limit_usd"], LIMIT)
        self.assertAlmostEqual(shown["open_usd"], open_sum)
        self.assertAlmostEqual(shown["settled_usd"], settled_sum)
        self.assertAlmostEqual(shown["left_usd"], LIMIT - open_sum - settled_sum)
        self.assertAlmostEqual(shown["open_usd"] + shown["settled_usd"] +
                               shown["left_usd"], LIMIT)
        return shown

    def check_crash(self, phase, settled_count=0):
        pid = self.kill_at(phase)
        if phase == "after_reserve":
            with self.server.seen_lock:
                self.assertEqual(self.server.seen, [])
        before = self.reservations()
        open_count = len(VOICES) - settled_count
        self.assertEqual(sum(r["state"] == "open" for r in before.values()), open_count)
        self.assertEqual(sum(r["state"] == "settled" for r in before.values()), settled_count)
        for row in before.values():
            self.assertEqual(row["pid"], pid)
            self.assertEqual(row["reserved_usd"], CEILING)
            if row["state"] == "open":
                self.assertIsNone(row["settled_usd"])
            else:
                self.assertAlmostEqual(row["settled_usd"], COST)
        shown_before = self.assert_accounting(before, open_count * CEILING, settled_count * COST)
        recovered = self.cli("recover")
        self.assertEqual(recovered["run"], self.run_id)
        self.assertEqual(recovered["recovered"], open_count)
        after = self.reservations()
        self.assertEqual(set(after), set(before))
        for identity, old in before.items():
            new = after[identity]
            self.assertEqual(new["reserved_usd"], old["reserved_usd"])
            if old["state"] == "open":
                self.assertEqual(new["state"], "kept_unknown")
                self.assertEqual(new["settled_usd"], old["reserved_usd"])
            else:
                self.assertEqual(new["state"], "settled")
                self.assertEqual(new["settled_usd"], old["settled_usd"])
        total = open_count * CEILING + settled_count * COST
        shown_after = self.assert_accounting(after, 0, total)
        self.assertAlmostEqual(shown_after["left_usd"], shown_before["left_usd"],
                               msg="Recovery released or double-counted a charge")
        second = self.cli("recover")
        self.assertEqual(second["run"], self.run_id)
        self.assertEqual(second["recovered"], 0)
        again = self.reservations()
        self.assertEqual(set(again), set(after))
        for identity, row in after.items():
            for field in ("line", "voice", "pid", "reserved_usd", "settled_usd", "state"):
                self.assertEqual(again[identity][field], row[field])
        shown_again = self.assert_accounting(again, 0, total)
        for field in ("run", "limit_usd", "open_usd", "settled_usd", "left_usd"):
            self.assertEqual(shown_again[field], shown_after[field])

    def test_c8_kill_after_reserve_keeps_full_ceilings_and_recovery_is_idempotent(self):
        self.check_crash("after_reserve")

    def test_c8_kill_after_dispatch_keeps_full_ceilings_and_recovery_is_idempotent(self):
        self.check_crash("after_dispatch")

    def test_c8_kill_during_settle_preserves_settled_voice_and_recovers_only_open(self):
        self.check_crash("during_settle", settled_count=1)


if __name__ == "__main__":
    unittest.main()
