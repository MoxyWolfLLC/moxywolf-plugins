#!/usr/bin/env python3
"""DC-001.9: decider_council.py runs as a subprocess against a stub /v1/decisions server that
answers per model slug, the way the host calls it. Nothing here imports the script's functions to
assert on them except the outcome rule table, which is data."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "decider_council.py"
V = ["typesafe-ai/jev", "perplexity/pplx-decider-v1.2", "openai/gpt-6-luna-decisions"]

QS = [{"type": "predicate", "name": "risky", "instructions": "Is it risky?"},
      {"type": "choice", "name": "lane", "instructions": "Which lane?", "choices": [{"value": "a"}, {"value": "b"}, {"value": "c"}]},
      {"type": "score", "name": "size", "instructions": "How big?", "levels": [{"label": "s"}, {"label": "m"}, {"label": "l"}]}]


class Stub(http.server.BaseHTTPRequestHandler):
    """answers[slug] = {question: value}; a slug missing from `answers` returns 500; a slug in `slow`
    sleeps a second; a slug in `refuse` returns a refusal for every question."""
    answers, slow, refuse, seen, raw = {}, set(), set(), [], []
    envelope = {}        # slug -> a literal JSON value to send instead of the documented shape (F4)
    stream = set()       # slugs that send a valid body one byte every 0.2 s for 3 s (F5)

    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        body = json.loads(data)
        Stub.seen.append((self.path, body)); Stub.raw.append((body["model"], data))
        m = body["model"]
        if m in Stub.slow:
            time.sleep(1)
        if m in Stub.envelope:
            return self._send(200, Stub.envelope[m])
        if m in Stub.stream:
            raw = json.dumps({"model": m, "answers": [{"type": "predicate", "name": "risky", "probability": 0.5}]}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw) + 40)); self.end_headers()
            for _ in range(15):
                self.wfile.write(b" "); self.wfile.flush(); time.sleep(0.2)
            self.wfile.write(raw); return
        if m not in Stub.answers:
            return self._send(500, {"error": {"message": "down"}})
        out = []
        for q in body["questions"]:
            v = Stub.answers[m].get(q["name"])
            if m in Stub.refuse or v is None:
                out.append({"type": "refusal", "name": q["name"]})
            elif q["type"] == "predicate":
                out.append({"type": "predicate", "name": q["name"], "probability": v})
            elif q["type"] == "choice":
                out.append({"type": "choice", "name": q["name"], "choice": v, "confidence": 0.9})
            else:
                out.append({"type": "score", "name": q["name"], "score": v, "confidence": 0.9})
        self._send(200, {"model": m, "answers": out, "usage": {"input_tokens": 10, "output_tokens": 0},
                         "provider_metadata": {"gateway": {"cost": "0.00001"}}})

    def _send(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def log_message(self, *a):
        pass


def same(v):
    return {m: dict(v) for m in V}


class DeciderCouncil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dc001-"))
        (self.root / "in.txt").write_text("the thing under decision")
        (self.root / "q.json").write_text(json.dumps(QS))
        Stub.answers, Stub.slow, Stub.refuse, Stub.seen, Stub.raw = {}, set(), set(), [], []
        Stub.envelope, Stub.stream = {}, set()

    def run_dc(self, *args, **env):
        e = {k: v for k, v in os.environ.items() if k not in {"AI_GATEWAY_API_KEY", "GSTACK_AIGATEWAY_ENV", "JEV_ENDPOINT", "GSTACK_DECIDERS"}}
        e.update(AI_GATEWAY_API_KEY="k-test", JEV_ENDPOINT=self.endpoint, GSTACK_PEER_REVIEW_DIR=str(self.root / "reviews"), **env)
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=e)

    def ask(self, **env):
        r = self.run_dc("ask", "--caller", "fx", "--ref", "r1", "--input", str(self.root / "in.txt"), "--questions", str(self.root / "q.json"), **env)
        self.assertIn(r.returncode, (0, 1), r.stderr)
        return r, json.loads(r.stdout)

    def ledger_lines(self):
        return [json.loads(l) for f in (self.root / "reviews" / "decisions").glob("*.jsonl") for l in f.read_text().splitlines() if l]

    # ---- DC-001.1 and .9: one body to each slug, byte-identical but for `model`; concurrent ----

    def test_three_voices_agree_and_each_slug_received_the_same_body(self):
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2})
        r, out = self.ask()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(b["model"] for _, b in Stub.seen), sorted(V))
        # F9: the raw bytes are identical after the leading `"model": "<slug>", ` member
        tails = set()
        for m, data in Stub.raw:
            head = b'{"model": ' + json.dumps(m).encode() + b", "
            self.assertTrue(data.startswith(head), data[:60])
            tails.add(data[len(head):])
        self.assertEqual(len(tails), 1, "the request bytes differ between slugs beyond the model member")
        self.assertTrue(all(p == "/v1/decisions" for p, _ in Stub.seen))
        self.assertEqual(out["quorum"], "full")
        self.assertEqual((out["answers"]["lane"]["majority"], out["answers"]["lane"]["agreed"], out["answers"]["lane"]["tie"]), ("b", True, False))
        self.assertEqual((out["answers"]["risky"]["majority"], out["answers"]["risky"]["agreed"]), (0.8, True))
        self.assertEqual((out["answers"]["size"]["majority"], out["answers"]["size"]["agreed"]), (2, True))
        self.assertEqual(len(out["voices"]), 3)
        self.assertTrue(all(v["cost"] == "0.00001" for v in out["voices"]))

    def test_the_three_calls_run_concurrently(self):
        Stub.answers = same({"risky": 0.5, "lane": "a", "size": 1}); Stub.slow = set(V)
        t = time.time(); r, out = self.ask(); dt = time.time() - t
        self.assertEqual(out["quorum"], "full")
        self.assertLess(dt, 2.0, f"three one-second voices took {dt:.2f}s: not concurrent")

    # ---- DC-001.3: majority both ways, tie, median ----

    def test_a_two_to_one_choice_split_returns_the_majority_in_both_directions(self):
        Stub.answers = {V[0]: {"risky": 0.1, "lane": "a", "size": 0}, V[1]: {"risky": 0.9, "lane": "b", "size": 2}, V[2]: {"risky": 0.9, "lane": "b", "size": 2}}
        _, out = self.ask()
        self.assertEqual((out["answers"]["lane"]["majority"], out["answers"]["lane"]["agreed"], out["answers"]["lane"]["tie"]), ("b", False, False))
        Stub.answers = {V[0]: {"risky": 0.9, "lane": "a", "size": 2}, V[1]: {"risky": 0.9, "lane": "a", "size": 2}, V[2]: {"risky": 0.1, "lane": "c", "size": 0}}
        _, out = self.ask()
        self.assertEqual(out["answers"]["lane"]["majority"], "a")

    def test_a_three_way_choice_split_is_a_tie_and_numbers_take_the_median(self):
        Stub.answers = {V[0]: {"risky": 0.2, "lane": "a", "size": 0}, V[1]: {"risky": 0.5, "lane": "b", "size": 1}, V[2]: {"risky": 0.9, "lane": "c", "size": 2}}
        _, out = self.ask()
        lane = out["answers"]["lane"]
        self.assertEqual((lane["majority"], lane["tie"], lane["agreed"]), (None, True, False))
        self.assertEqual((out["answers"]["risky"]["majority"], out["answers"]["risky"]["agreed"]), (0.5, False))
        self.assertEqual(out["answers"]["size"]["majority"], 1)

    # ---- DC-001.2: unavailable voices are named and excluded ----

    def test_one_voice_down_is_recorded_and_excluded(self):
        Stub.answers = {V[0]: {"risky": 0.8, "lane": "b", "size": 2}, V[2]: {"risky": 0.8, "lane": "b", "size": 2}}
        r, out = self.ask()
        self.assertEqual(out["quorum"], "full")
        down = [v for v in out["voices"] if v["model"] == V[1]][0]
        self.assertIn("unavailable", down)
        self.assertEqual(out["answers"]["lane"]["by_voice"][V[1]], {"unavailable": "HTTP 500"})
        self.assertEqual((out["answers"]["lane"]["majority"], out["answers"]["lane"]["available"]), ("b", 2))

    def test_a_refusal_is_unavailable_for_that_question(self):
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2}); Stub.refuse = {V[2]}
        _, out = self.ask()
        self.assertEqual(out["answers"]["risky"]["by_voice"][V[2]], {"unavailable": "refusal"})
        self.assertEqual(out["answers"]["risky"]["available"], 2)
        self.assertEqual(out["answers"]["risky"]["majority"], 0.8)

    def test_three_refusals_are_unavailable_not_a_full_quorum(self):
        # F1: availability is a property of answers; HTTP 200 with refusals is no quorum
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2}); Stub.refuse = set(V)
        r, out = self.ask()
        self.assertEqual((r.returncode, out["quorum"]), (1, "unavailable"))
        self.assertTrue(all(v["unavailable"] == "refusal" and v["answered"] == 0 for v in out["voices"]))
        Stub.refuse = {V[1], V[2]}
        r, out = self.ask()
        self.assertEqual((r.returncode, out["quorum"]), (0, "degraded"))

    def test_a_malformed_envelope_is_unavailable_and_the_ledger_is_still_written(self):
        # F4: answers=7 and a top-level array are unavailable voices, not crashes
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2})
        Stub.envelope = {V[1]: {"answers": 7}, V[2]: [1, 2, 3]}
        r, out = self.ask()
        self.assertEqual((r.returncode, out["quorum"]), (0, "degraded"), r.stderr)
        self.assertEqual([v for v in out["voices"] if v["model"] == V[1]][0]["unavailable"], "malformed response: answers is not a list of objects")
        self.assertEqual([v for v in out["voices"] if v["model"] == V[2]][0]["unavailable"], "malformed response: not an object")
        self.assertEqual(out["answers"]["lane"]["by_voice"][V[0]]["choice"], "b")
        self.assertEqual(len(self.ledger_lines()), 1)

    def test_a_slow_stream_is_cut_at_the_deadline(self):
        # F5: the deadline covers the body read, not only the connection
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2}); Stub.stream = {V[1]}
        t = time.time()
        r = self.run_dc("ask", "--caller", "fx", "--ref", "r1", "--input", str(self.root / "in.txt"), "--questions", str(self.root / "q.json"), "--timeout-ms", "700")
        dt = time.time() - t
        out = json.loads(r.stdout)
        slow = [v for v in out["voices"] if v["model"] == V[1]][0]
        self.assertIn("unavailable", slow); self.assertEqual(slow["status"], "timeout")
        self.assertLess(dt, 2.5, f"a voice streaming for 3 s held the call for {dt:.1f}s")
        self.assertEqual(out["answers"]["lane"]["majority"], "b")

    def test_concurrent_asks_and_outcomes_lose_nothing(self):
        # F3: appends and read-modify-replace share one lock
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2})
        _, first = self.ask()
        errors = []

        def asker():
            for _ in range(6):
                r = self.run_dc("ask", "--caller", "fx", "--ref", "c", "--input", str(self.root / "in.txt"), "--questions", str(self.root / "q.json"), "--compact")
                if r.returncode != 0: errors.append(r.stderr)

        def writer(i):
            for k in range(6):
                r = self.run_dc("outcome", "--line", first["id"], "--result", json.dumps({"w": i, "k": k}))
                if r.returncode != 0: errors.append(r.stderr)
        ts = [threading.Thread(target=asker), threading.Thread(target=asker), threading.Thread(target=writer, args=(1,)), threading.Thread(target=writer, args=(2,))]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(errors, [])
        lines = self.ledger_lines()
        self.assertEqual(len(lines), 13, "an append was lost")
        self.assertEqual(len({l["id"] for l in lines}), 13)
        self.assertIn([l for l in lines if l["id"] == first["id"]][0]["outcome"]["w"], (1, 2))
        self.assertFalse(list((self.root / "reviews" / "decisions").glob("*.tmp")), "a temp file was left behind")

    def test_a_malformed_answer_is_unavailable(self):
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2}); Stub.answers[V[1]] = {"risky": 1.7, "lane": "zzz", "size": 9}
        _, out = self.ask()
        self.assertEqual(out["answers"]["risky"]["by_voice"][V[1]], {"unavailable": "malformed probability"})
        self.assertEqual(out["answers"]["lane"]["by_voice"][V[1]], {"unavailable": "choice not offered"})
        self.assertEqual(out["answers"]["size"]["by_voice"][V[1]], {"unavailable": "score outside levels"})

    def test_one_voice_left_is_degraded_and_none_is_unavailable(self):
        Stub.answers = {V[0]: {"risky": 0.8, "lane": "b", "size": 2}}
        r, out = self.ask()
        self.assertEqual((r.returncode, out["quorum"]), (0, "degraded"))
        self.assertEqual((out["answers"]["lane"]["majority"], out["answers"]["lane"]["tie"]), (None, True))
        Stub.answers = {}
        r, out = self.ask()
        self.assertEqual((r.returncode, out["quorum"]), (1, "unavailable"))
        self.assertEqual(len(self.ledger_lines()), 2, "both calls were ledgered")

    def test_a_timed_out_voice_is_unavailable_and_the_others_answer(self):
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2}); Stub.slow = {V[1]}
        _, out = self.ask()
        r = self.run_dc("ask", "--caller", "fx", "--ref", "r1", "--input", str(self.root / "in.txt"), "--questions", str(self.root / "q.json"), "--timeout-ms", "300")
        out = json.loads(r.stdout)
        self.assertIn("unavailable", [v for v in out["voices"] if v["model"] == V[1]][0])
        self.assertEqual(out["answers"]["lane"]["majority"], "b")

    def test_voices_override_and_no_key_are_honest(self):
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2})
        _, out = self.ask(GSTACK_DECIDERS=f"{V[0]},{V[2]}")
        self.assertEqual([v["model"] for v in out["voices"]], [V[0], V[2]])
        Stub.seen = []
        e = {k: v for k, v in os.environ.items() if k not in {"AI_GATEWAY_API_KEY", "GSTACK_AIGATEWAY_ENV"}}
        e.update(GSTACK_AIGATEWAY_ENV=str(self.root / "missing.env"), JEV_ENDPOINT=self.endpoint, GSTACK_PEER_REVIEW_DIR=str(self.root / "reviews"))
        r = subprocess.run([sys.executable, str(SCRIPT), "ask", "--caller", "fx", "--ref", "r", "--input", str(self.root / "in.txt"), "--questions", str(self.root / "q.json")], capture_output=True, text=True, env=e)
        out = json.loads(r.stdout)
        self.assertEqual((r.returncode, out["quorum"]), (1, "unavailable"))
        self.assertIn("missing.env", out["voices"][0]["unavailable"])
        self.assertEqual(Stub.seen, [], "no key, so no call")

    # ---- DC-001.4: the ledger line is written before output; outcome fills it and keeps the answers ----

    def test_the_ledger_line_is_written_and_outcome_fills_it(self):
        Stub.answers = same({"risky": 0.8, "lane": "b", "size": 2})
        _, out = self.ask()
        lines = self.ledger_lines()
        self.assertEqual((len(lines), lines[0]["id"], lines[0]["outcome"], lines[0]["caller"], lines[0]["ref"]), (1, out["id"], None, "fx", "r1"))
        self.assertTrue(Path(out["ledger"]).exists())
        r = self.run_dc("outcome", "--line", out["id"], "--result", json.dumps({"rounds_used": 1, "blocking_findings": 0}))
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.ledger_lines()
        self.assertEqual(lines[0]["outcome"], {"rounds_used": 1, "blocking_findings": 0})
        self.assertEqual(lines[0]["answers"], out["answers"], "answers changed when the outcome was written")
        r = self.run_dc("outcome", "--line", "nope", "--result", "{}")
        self.assertEqual(r.returncode, 2)

    # ---- DC-001.5 and .6: score and gate ----

    def test_score_prints_zeros_on_an_empty_ledger_and_counts_on_a_fixture(self):
        r = self.run_dc("score", "--caller", "model_select")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 lines for caller model_select", r.stdout)
        self.assertIn("model_select: 0 calls, 0 with outcome, 0 of 0 questions agreed, 0 ties; majority 0 right of 0 scored", r.stdout)
        self.write_fixture(n=3, cleared=1)
        r = self.run_dc("score", "--caller", "model_select")
        self.assertIn("model_select: 3 calls, 3 with outcome, 15 of 15 questions agreed, 0 ties; outcome rule registered", r.stdout)
        self.assertIn(f"{V[0]}: 3 calls, 15 answers, 0 unavailable answers, agreed with the majority 15 of 15 (rate 1.000), in a tie 0 of 15 (rate 0.000), 1 right of 3 scored (rate 0.333)", r.stdout)
        self.assertIn("majority: 1 right of 3 scored (rate 0.333)", r.stdout)
        # F2: a voice that refused every question on one line shows 5 unavailable answers and no agreement for them
        self.write_fixture(n=1, cleared=1, refusing=V[2])
        r = self.run_dc("score", "--caller", "model_select")
        self.assertIn(f"{V[2]}: 4 calls, 15 answers, 5 unavailable answers, agreed with the majority 15 of 15", r.stdout)
        self.assertIn("majority: 2 right of 4 scored (rate 0.500)", r.stdout)

    def test_gate_refuses_at_19_and_below_jev_and_passes_at_20_at_or_above(self):
        self.write_fixture(n=19, cleared=19)
        r = self.run_dc("gate", "--caller", "model_select"); g = json.loads(r.stdout)
        self.assertEqual((r.returncode, g["ok"], g["lines"], g["reason"]), (1, False, 19, "insufficient_history"), r.stdout)
        # Jev abstains (floor, unscored) on two failed lines, so Jev alone reads 10/18 against the majority's 10/20
        self.reset(); self.write_fixture(n=20, cleared=10, jev_abstains=2)
        r = self.run_dc("gate", "--caller", "model_select"); g = json.loads(r.stdout)
        self.assertEqual((r.returncode, g["ok"], g["majority_rate"], g["jev_rate"], g["jev_scored"]), (1, False, 0.5, 0.556, 18), r.stdout)
        self.reset(); self.write_fixture(n=20, cleared=11)
        r = self.run_dc("gate", "--caller", "model_select"); g = json.loads(r.stdout)
        self.assertEqual((r.returncode, g["ok"], g["lines"], g["majority_rate"], g["jev_rate"]), (0, True, 20, 0.55, 0.55), r.stdout)
        # a majority scored over nothing (every voice said floor on every line) examined nothing and does not pass
        self.reset(); self.write_fixture(n=20, cleared=0, floor=True)
        r = self.run_dc("gate", "--caller", "model_select"); g = json.loads(r.stdout)
        self.assertEqual((r.returncode, g["ok"], g["majority_scored"]), (1, False, 0), r.stdout)
        # lines where a question had fewer than two valid answers do not count toward the 20, HTTP 200 or not
        self.reset(); self.write_fixture(n=20, cleared=20, voices_up=1)
        r = self.run_dc("gate", "--caller", "model_select"); g = json.loads(r.stdout)
        self.assertEqual((g["ok"], g["lines"]), (False, 0), r.stdout)
        self.reset(); self.write_fixture(n=19, cleared=19, voices_up=2, refusing=V[1]); self.write_fixture(n=19, cleared=19, voices_up=2, refusing=V[0])
        r = self.run_dc("gate", "--caller", "model_select"); g = json.loads(r.stdout)
        self.assertEqual((g["ok"], g["lines"]), (False, 0), r.stdout)
        self.reset(); self.write_fixture(n=20, cleared=20, voices_up=1)
        r = self.run_dc("gate", "--caller", "model_select"); g = json.loads(r.stdout)
        self.assertEqual((g["ok"], g["lines"]), (False, 0), r.stdout)

    def reset(self):
        for f in (self.root / "reviews" / "decisions").glob("*.jsonl"):
            f.unlink()

    def write_fixture(self, n, cleared, jev_abstains=0, floor=False, voices_up=3, refusing=None):
        """Ledger lines in the model_select shape. The first `cleared` lines cleared review. Every
        voice says a cheap tier (risky 0.1) unless `floor`; Jev says floor (risky 0.9, unscored by the
        rule) on `jev_abstains` of the failed lines, which is the only way two voices on one outcome
        can score differently."""
        d = self.root / "reviews" / "decisions"; d.mkdir(parents=True, exist_ok=True)
        abstain_left = jev_abstains
        with open(d / "202610.jsonl", "a") as fh:
            for i in range(n):
                ok = i < cleared
                base = 0.9 if floor else 0.1
                jev = base
                if not ok and abstain_left:
                    jev, abstain_left = 0.9, abstain_left - 1
                p = lambda v: {"probability": v}
                up = [m for m in V[:voices_up] if m != refusing]
                answers = {}
                for q in ["trust_boundary", "cross_file", "docs_only", "has_tests", "risky"]:
                    bv = {m: p((jev if m == V[0] else base) if q == "risky" else 0.1) for m in up}
                    if refusing in V[:voices_up]:
                        bv[refusing] = {"unavailable": "refusal"}
                    answers[q] = {"type": "predicate", "majority": base if q == "risky" else 0.1, "agreed": True, "tie": len(up) < 2,
                                  "available": len(up), "by_voice": bv, "agrees": {m: True for m in up}}
                vs = [{"model": m, "status": 200, "latency_ms": 500, "cost": "0.00001", "input_tokens": 10, "answered": 0 if m == refusing else 5, "questions": 5,
                       **({"unavailable": "refusal"} if m == refusing else {})} for m in V[:voices_up]]
                vs += [{"model": m, "status": 500, "latency_ms": 5, "cost": None, "input_tokens": None, "unavailable": "HTTP 500"} for m in V[voices_up:]]
                line = {"id": f"fx{i:03d}", "ts": "2026-10-18T00:00:00+00:00", "caller": "model_select", "ref": f"r{i}",
                        "questions": [{"name": q, "type": "predicate"} for q in answers], "voices": vs,
                        "answers": answers, "quorum": "full" if voices_up >= 2 else "degraded", "credential": "env",
                        "outcome": {"rounds_used": 1 if ok else 3, "blocking_findings": 0 if ok else 1}}
                fh.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    unittest.main()
