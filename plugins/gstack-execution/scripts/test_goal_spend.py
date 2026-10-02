"""GO-004.2: the runner counts what a goal run spends and stops near the cap. Stub server only;
no provider is called."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_spend as gs  # noqa: E402
import peer_review as pr  # noqa: E402
import test_openrouter_transport as tot  # noqa: E402  its stub server and canned replies

BRIEF = "## Spend cap\n$5\n\n## Provider budgets\n- openrouter: $3\n- gemini: $2\n\n## Max calls\n10\n"


class Status(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name, "spend.jsonl")
        self.ledger.write_text("")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, provider, cost, transport="openrouter", n=1):
        with open(self.ledger, "a") as f:
            for _ in range(n):
                f.write(json.dumps({"provider": provider, "cost": cost, "transport": transport}) + "\n")

    def test_under_eighty_percent_continues(self):
        self.add("openrouter", "1.00"); self.add("gemini", "0.50"); self.add("codex", None, "subscription", 3)
        stop, reasons, t = gs.status(self.ledger, BRIEF)
        self.assertEqual((stop, reasons), (False, []))
        self.assertEqual((t["entries"], t["total"], t["calls"]), (5, "1.50", 3))

    def test_an_empty_ledger_continues_and_says_so(self):
        self.assertEqual(gs.status(self.ledger, BRIEF)[:2], (False, []))

    def test_each_provider_stops_at_its_own_budget(self):
        self.add("gemini", "1.59")
        self.assertFalse(gs.status(self.ledger, BRIEF)[0])
        self.add("gemini", "0.01")                                         # $1.60 of $2 is 80%
        stop, reasons, _ = gs.status(self.ledger, BRIEF)
        self.assertTrue(stop)
        self.assertEqual(reasons, ["gemini spent $1.60 of its $2 budget (stop at 80%)"])
        self.ledger.write_text("")
        self.add("openrouter", "2.40")
        self.assertEqual(gs.status(self.ledger, BRIEF)[1], ["openrouter spent $2.40 of its $3 budget (stop at 80%)"])

    def test_max_calls_counts_subscriptions_and_unpriced_calls(self):
        self.add("codex", None, "subscription", 7)
        self.assertFalse(gs.status(self.ledger, BRIEF)[0])
        self.add("openrouter", None)                                       # metered, no cost reported
        stop, reasons, _ = gs.status(self.ledger, BRIEF)
        self.assertTrue(stop)
        self.assertEqual(reasons, ["8 of 10 Max calls used (stop at 80%)"])

    def test_a_charge_to_a_provider_with_no_budget_stops(self):
        self.add("anthropic", "0.01")
        self.assertEqual(gs.status(self.ledger, BRIEF)[1], ["anthropic was charged $0.01 and has no Provider budget"])

    def test_a_ledger_that_cant_be_read_stops(self):
        for text in ("not json\n", json.dumps({"provider": "openrouter"}) + "\n",
                     json.dumps({"provider": "openrouter", "cost": "-1", "transport": "openrouter"}) + "\n",
                     json.dumps({"provider": "openrouter", "cost": "NaN", "transport": "openrouter"}) + "\n"):
            with self.subTest(text=text):
                self.ledger.write_text(text)
                stop, reasons, _ = gs.status(self.ledger, BRIEF)
                self.assertTrue(stop)
                self.assertIn("can't be read", reasons[0])
        self.ledger.unlink()
        self.assertTrue(gs.status(self.ledger, BRIEF)[0])

    def test_cli_exit_zero_is_the_only_continue(self):
        brief = Path(self.tmp.name, "GOAL.md"); brief.write_text(BRIEF)
        run = lambda *a: subprocess.run([sys.executable, gs.__file__, "status", *a], capture_output=True, text=True)
        self.assertEqual(run(str(self.ledger), str(brief)).returncode, 0)
        self.add("gemini", "1.60")
        r = run(str(self.ledger), str(brief))
        self.assertEqual(r.returncode, 1)
        self.assertIn("STOP: gemini spent", r.stdout)
        self.assertEqual(run(str(self.ledger), str(brief) + ".missing").returncode, 1)


class Recording(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), tot.Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        key = Path(cls.tmp.name, "key.env"); key.write_text('OPENROUTER_API_KEY="sk-test-not-a-real-key"\n')
        cls.saved = {k: os.environ.get(k) for k in ("GSTACK_OPENROUTER_ENV", gs.LEDGER_ENV)}
        os.environ["GSTACK_OPENROUTER_ENV"] = str(key)
        cls.url, pr.OPENROUTER_URL = pr.OPENROUTER_URL, f"http://127.0.0.1:{cls.srv.server_port}/v1/chat/completions"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        pr.OPENROUTER_URL = cls.url
        for k, v in cls.saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        cls.tmp.cleanup()

    def setUp(self):
        self.ledger = Path(self.tmp.name, f"{self.id()}.jsonl")
        os.environ[gs.LEDGER_ENV] = str(self.ledger)

    def surface(self):
        d = Path(tempfile.mkdtemp(dir=self.tmp.name))
        (d / "CHANGE.diff").write_text("--- a/x\n+++ b/x\n+one\n")
        return d

    def lines(self):
        return [json.loads(x) for x in self.ledger.read_text().splitlines()]

    def test_an_openrouter_review_records_its_reported_cost(self):
        tot.NEXT.update(status=200, body=tot.ok('{"x": 1}', usage={"total_tokens": 3, "cost": 0.0123}))
        pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(tot.SEEN.get("usage"), {"include": True})
        self.assertEqual(self.lines(), [{"provider": "openrouter", "cost": "0.0123", "transport": "openrouter"}])

    def test_a_reply_with_no_cost_is_recorded_as_unpriced(self):
        tot.NEXT.update(status=200, body=tot.ok('{"x": 1}'))
        pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(self.lines()[0]["cost"], None)

    def test_a_refused_reply_is_still_counted(self):
        tot.NEXT.update(status=200, body={"error": {"message": "nope"}, "usage": {"cost": 0.002}})
        with self.assertRaises(pr.ReviewError):
            pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(self.lines()[0]["cost"], "0.002")

    def test_the_reducer_records_and_cant_swallow_a_ledger_failure(self):
        tot.NEXT.update(status=200, body=tot.ok('{"r": 1}', usage={"total_tokens": 3, "cost": 0.001}))
        pr.reducer_ask("i", "r")
        self.assertEqual(self.lines()[0]["cost"], "0.001")
        os.environ[gs.LEDGER_ENV] = self.tmp.name                       # a directory: the write fails
        with self.assertRaises(gs.LedgerError):
            pr.reducer_ask("i", "r")                                     # it catches Exception, not this

    def test_a_cli_reviewer_counts_as_a_subscription_call(self):
        saved, pr._SELFTEST = pr._SELFTEST, True
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "echo '{}'"
        try:
            try:
                pr.run_reviewer("codex", "p", self.surface(), 30)
            except pr.ReviewError:
                pass
        finally:
            pr._SELFTEST = saved
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD")
        self.assertEqual(self.lines(), [{"provider": "codex", "cost": None, "transport": "subscription"}])

    def test_outside_a_goal_run_nothing_is_written(self):
        os.environ.pop(gs.LEDGER_ENV)
        tot.NEXT.update(status=200, body=tot.ok('{"x": 1}', usage={"total_tokens": 3, "cost": 0.5}))
        pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
