#!/usr/bin/env python3
"""DC-003 criteria 5, 6 and 9, exercised only through the CLI and local HTTP.

Run: python3 plugins/council/scripts/test_dc003_reserve.py
The response gate keeps a reservation open while another CLI inspects or contests it.
"""
import fcntl
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from decimal import Decimal
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("decider_council.py")
MODEL = "typesafe-ai/jev"
RUN = "dc003-reserve-test"


class Stub(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with self.server.seen_lock:
            self.server.seen.append(body)
        self.server.arrived.set()
        self.server.release.wait(20)
        raw = json.dumps({
            "model": body["model"],
            "answers": [{"type": "predicate", "name": "risky", "probability": 0.2}],
            "usage": {"input_tokens": 10, "output_tokens": 1},
            "provider_metadata": {"gateway": {"cost": self.server.cost}},
        }).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


class ReserveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dc003-reserve-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.budget_dir = self.root / "budget"
        self.budget_dir.mkdir()
        self.budget = self.budget_dir / "run.json"
        self.lock = Path(str(self.budget) + ".lock")
        self.reviews = self.root / "reviews"
        self.key = self.root / "key.env"
        self.key.write_text("AI_GATEWAY_API_KEY=offline-dc003-test-key\n")
        (self.root / "input.txt").write_text("An offline budget decision.")
        (self.root / "questions.json").write_text(json.dumps([
            {"type": "predicate", "name": "risky", "instructions": "Is it risky?"}
        ]))
        self.pricing = self.root / "pricing.json"
        self.pricing.write_text(json.dumps({"data": [
            {"id": MODEL, "pricing": {"input": "0.000001", "output": "0.000001"}}
        ]}))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        self.server.seen = []
        self.server.seen_lock = threading.Lock()
        self.server.arrived = threading.Event()
        self.server.release = threading.Event()
        self.server.release.set()
        self.server.cost = "0.02"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.processes = []
        self.addCleanup(self.stop)

    def stop(self):
        self.server.release.set()
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def start(self, *args, reviews=None):
        # A fresh environment keeps real credentials, proxies and pause hooks out.
        env = {
            "PATH": os.defpath, "HOME": str(self.root), "TMPDIR": str(self.root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "JEV_ENDPOINT": f"http://127.0.0.1:{self.server.server_port}",
            "GSTACK_PEER_REVIEW_DIR": str(self.reviews if reviews is None else reviews),
            "GSTACK_DECIDERS": MODEL,
            "GSTACK_COUNCIL_AIGATEWAY_ENV": str(self.key),
            "GSTACK_AIGATEWAY_ENV": str(self.key),
            "AI_GATEWAY_API_KEY": "offline-dc003-test-key",
        }
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), *map(str, args)], env=env,
            cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.processes.append(process)
        return process

    def finish(self, process, code=0):
        stdout, stderr = process.communicate(timeout=15)
        self.assertEqual(process.returncode, code, f"stdout={stdout}\nstderr={stderr}")
        return stdout

    def budget_args(self, operation, run=RUN):
        return ["budget", operation, "--budget", self.budget, "--run", run]

    def init(self, limit="0.05"):
        self.finish(self.start(*self.budget_args("init"), "--limit-usd", limit,
                               "--key-id", "offline-key-id"))

    def ask(self, reviews=None, run=RUN):
        return self.start(
            "ask", "--caller", "dc003_reserve", "--ref", "offline",
            "--input", self.root / "input.txt", "--questions", self.root / "questions.json",
            "--budget", self.budget, "--run", run, "--pricing", self.pricing,
            "--timeout-ms", "12000", reviews=reviews,
        )

    def state(self):
        return json.loads(self.budget.read_text())

    def requests(self):
        with self.server.seen_lock:
            return list(self.server.seen)

    def ledger(self, reviews=None):
        directory = self.reviews if reviews is None else reviews
        return [json.loads(line) for file in (directory / "decisions").glob("*.jsonl")
                for line in file.read_text().splitlines() if line.strip()]

    def refused(self, process, reason):
        result = json.loads(self.finish(process, code=4))
        self.assertEqual(result["refused"], reason)
        return result

    def no_temps(self):
        self.assertEqual({path.name for path in self.budget_dir.iterdir()},
                         {self.budget.name, self.lock.name})

    def show(self, open_usd, settled_usd, left_usd):
        result = json.loads(self.finish(self.start(*self.budget_args("show"))))
        self.assertEqual(result["run"], RUN)
        for field, expected in {"limit_usd": "0.05", "open_usd": open_usd,
                                "settled_usd": settled_usd, "left_usd": left_usd}.items():
            self.assertEqual(Decimal(str(result[field])), Decimal(expected), field)
        self.assertEqual(Decimal(str(self.state()["limit_usd"])), Decimal("0.05"))

    def test_c9_init_refuses_existing_file_without_changing_limit(self):
        self.init()
        before = self.budget.read_bytes()
        process = self.start(*self.budget_args("init"), "--limit-usd", "99",
                             "--key-id", "offline-key-id")
        self.refused(process, "budget_exists")
        self.assertEqual(self.budget.read_bytes(), before)
        self.assertEqual(self.requests(), [])
        self.no_temps()

    def test_c9_show_reports_totals_and_limit_survives_budget_operations(self):
        self.init()
        self.server.cost = "0.01"
        limit = self.state()["limit_usd"]
        self.show("0", "0", "0.05")
        self.server.release.clear()
        process = self.ask()
        self.assertTrue(self.server.arrived.wait(8), "ask never reached the local stub")
        self.show("0.05", "0", "0")
        reservations = self.state()["reservations"]
        self.assertEqual(len(reservations), 1)
        self.assertEqual(reservations[0]["pid"], process.pid)
        self.assertEqual(reservations[0]["state"], "open")
        self.assertEqual(self.state()["limit_usd"], limit)
        self.no_temps()
        self.server.release.set()
        self.finish(process)
        self.show("0", "0.01", "0.04")
        self.assertEqual(self.state()["limit_usd"], limit)
        self.server.arrived.clear()
        self.server.release.clear()
        interrupted = self.ask()
        self.assertTrue(self.server.arrived.wait(8), "second ask never reached the stub")
        self.show("0.02", "0.01", "0.02")
        self.assertEqual(self.state()["limit_usd"], limit)
        interrupted.kill()
        interrupted.communicate(timeout=5)
        self.finish(self.start(*self.budget_args("recover")))
        self.show("0", "0.03", "0.02")
        self.assertEqual(self.state()["limit_usd"], limit)
        self.no_temps()

    def test_c5_missing_budget_is_unreadable_and_sends_nothing(self):
        self.refused(self.ask(), "budget_unreadable")
        self.assertEqual(self.requests(), [])
        self.assertFalse(self.budget.exists())

    def test_c5_corrupt_budget_is_unreadable_and_sends_nothing(self):
        self.budget.write_text('{"run":')
        before = self.budget.read_bytes()
        self.refused(self.ask(), "budget_unreadable")
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.budget.read_bytes(), before)

    def test_c5_run_mismatch_sends_nothing_and_preserves_budget(self):
        self.init()
        before = self.state()
        self.refused(self.ask(run="another-run"), "budget_run_mismatch")
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.state(), before)
        self.no_temps()

    def test_c6_exhausted_sends_and_reserves_nothing_and_ledgers_refusal(self):
        self.init(limit="0.04")
        before = self.state()
        self.refused(self.ask(), "budget_exhausted")
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.state(), before)
        lines = self.ledger()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["refused"], "budget_exhausted")
        self.no_temps()

    def test_c6_two_processes_one_sends_with_different_review_directories(self):
        self.init()
        self.server.cost = "0.05"
        self.server.release.clear()
        directories = [self.root / "reviews-a", self.root / "reviews-b"]
        processes = [self.ask(reviews=directory) for directory in directories]
        self.assertTrue(self.server.arrived.wait(8), "neither process reached the stub")
        deadline = time.monotonic() + 3
        while (all(process.poll() is None for process in processes)
               and len(self.requests()) < 2 and time.monotonic() < deadline):
            time.sleep(0.02)
        self.server.release.set()
        outputs = [process.communicate(timeout=15) for process in processes]
        self.assertEqual(sorted(process.returncode for process in processes), [0, 4], outputs)
        self.assertEqual(len(self.requests()), 1, "both callers spent the same available budget")
        refused_index = next(i for i, process in enumerate(processes) if process.returncode == 4)
        self.assertEqual(json.loads(outputs[refused_index][0])["refused"], "budget_exhausted")
        lines = self.ledger(directories[refused_index])
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["refused"], "budget_exhausted")
        reservations = self.state()["reservations"]
        self.assertEqual(len(reservations), 1, "a refused call left a reservation")
        self.assertEqual(reservations[0]["pid"], processes[1 - refused_index].pid)
        self.assertEqual(Decimal(str(self.state()["limit_usd"])), Decimal("0.05"))
        self.no_temps()

    def test_c5_init_and_reserve_use_budget_dot_lock_and_leave_no_temp_files(self):
        with self.lock.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            process = self.start(*self.budget_args("init"), "--limit-usd", "0.05",
                                 "--key-id", "offline-key-id")
            time.sleep(0.5)
            self.assertIsNone(process.poll(), "init bypassed the budget lock")
            self.assertFalse(self.budget.exists())
            fcntl.flock(lock, fcntl.LOCK_UN)
            self.finish(process)
            self.no_temps()

            fcntl.flock(lock, fcntl.LOCK_EX)
            self.server.release.clear()
            process = self.ask(reviews=self.root / "independent-reviews")
            self.assertFalse(self.server.arrived.wait(0.5), "reserve bypassed the budget lock")
            self.assertIsNone(process.poll())
            self.assertEqual(self.state()["reservations"], [])
            fcntl.flock(lock, fcntl.LOCK_UN)
            self.assertTrue(self.server.arrived.wait(8), "ask never reached the stub")

            self.server.release.set()
            self.finish(process)
            self.no_temps()


if __name__ == "__main__":
    unittest.main()
