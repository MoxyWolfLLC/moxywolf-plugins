#!/usr/bin/env python3
"""SR-003.1-5/9 (Budget): a spec review reserves its worst case before it calls, settles once, and the
spend ledger never lets a run commit past stop_usd. No network and no paid call: the real-transport
path runs with urllib.request.urlopen replaced by a counting stub, spec_review.headers replaced so no
credential is read, and GSTACK_ANTHROPIC_ENV unset. Prices come from a temp file, never the real rates.

Interface assumed (frozen by DESIGN.md SR-003; the implementation must provide it):
  spec_review.worst_case_usd(body_bytes, executor, advisor, prices) -> float, criterion 3's formula with
      N=10, R=8, O=20000, A=3, M=4096, K=4160, m=200, F_e=F_a=10000, each input priced at
      max(input, cache_write) of its model; `prices` is what load_prices returns.
  spec_review.load_prices(path=None) -> the prices dict (path None = spec_review_prices.json beside the
      script). run looks prices up through the module attribute, so patching it injects the temp file.
  spec_review.cmd_run(doc, items=None, post=post, constraints=False, ledger=None); the real-transport
      path is `post is spec_review.post`; ledger None means $GSTACK_SPEND_LEDGER, default
      ~/.gstack/spend-ledger.json.
  CLI: main(["budget", "init", "--stop-usd", N, "--ledger", P]), main(["budget", "show", "--ledger", P])
      printing stop_usd, spent_usd, held_usd and remaining_usd each followed by its number, and
      main(["run", doc, "--items", X, "--ledger", P]).
  Ledger (criterion 1): {"schema": "spend-ledger/1", "stop_usd", "spent_usd", "reservations": [{"id",
      "scope", "doc", "reserved_usd", "actual_usd", "state" held|settled, "reserved_at", "settled_at"}]},
      every read and write under review_run.locked(<ledger path>).
  Refusals raise spec_review.Refused; budget ones start "budget_refused:" / "budget_overrun:"; CLI exit 1.
"""
import contextlib
import io
import json
import math
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spec_review as sr  # noqa: E402

DESIGN = """# Fixture

## Goal

Change the value.

## Constraints and settled decisions

- The value is a word.

### FX-001 — The value changes

**Status:** planned.

1. value is after

### FX-002 — Another value

1. other is after
"""

EX, ADV = sr.EXECUTOR, sr.ADVISOR
# fake rates: the executor's cache_write and the advisor's input are the higher input rate, so the
# bound's max(input, cache_write) is exercised both ways
RATES = {EX: {"input": 1e-6, "output": 5e-6, "cache_read": 1e-7, "cache_write": 3e-6},
         ADV: {"input": 4e-6, "output": 2e-5, "cache_read": 2e-7, "cache_write": 2e-6}}
CLEAN = {"contradictions": [], "ambiguities": []}
N, R, O, A, M, K, m, F_E, F_A = 10, 8, 20000, 3, 4096, 4160, 200, 10000, 10000


def prices_file(path, models=(EX, ADV)):
    data = {"schema": "spec-review-prices/1", "verified": "2026-11-21",
            "models": {k: {**RATES[k], "source": "https://platform.claude.com/docs/en/about-claude/pricing"}
                       for k in models}}
    Path(path).write_text(json.dumps(data))
    return path


def bound(b):
    """Criterion 3, written out from DESIGN.md with the test rates."""
    pe_in = max(RATES[EX]["input"], RATES[EX]["cache_write"])
    pa_in = max(RATES[ADV]["input"], RATES[ADV]["cache_write"])
    e_in = N * R * (b + F_E + m) + N * O * R * (R + 1) // 2 + N * R * A * K
    a_in = A * (F_A + b + F_E + m + R * O + A * K)
    return pe_in * e_in + RATES[EX]["output"] * R * O + pa_in * a_in + RATES[ADV]["output"] * A * M


def it(model, inp=0, out=0, cr=0, cw=0, kind="message"):
    return {"type": kind, "model": model, "input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw}


def cost(entries):
    return sum(RATES[e["model"]]["input"] * e["input_tokens"] + RATES[e["model"]]["output"] * e["output_tokens"]
               + RATES[e["model"]]["cache_read"] * e["cache_read_input_tokens"]
               + RATES[e["model"]]["cache_write"] * e["cache_creation_input_tokens"] for e in entries)


def usage(entries):
    """Top-level fields are the executor iterations' sums, as the advisor docs say; settlement must not
    add them on top of `iterations`."""
    ex = [e for e in entries if e["type"] == "message"]
    top = {k: sum(e.get(k, 0) for e in ex) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                              "cache_creation_input_tokens")}
    return {**top, "iterations": entries}


def pause(entries=None):
    r = {"stop_reason": "pause_turn", "content": [{"type": "server_tool_use", "id": "s1", "name": "advisor", "input": {}}]}
    if entries is not None:
        r["usage"] = usage(entries)
    return r


def end(entries=None, text="Looked.\n```json\n" + json.dumps(CLEAN) + "\n```"):
    r = {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}
    if entries is not None:
        r["usage"] = usage(entries)
    return r


class Resp:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Urlopen:
    """Counting stand-in for urllib.request.urlopen. `script` is a list of response dicts, exceptions,
    or callables taking (n, first_body_bytes) and returning either."""

    def __init__(self, script=()):
        self.script, self.calls = list(script), []

    def __call__(self, req, timeout=None):
        self.calls.append(req)
        n = len(self.calls)
        step = self.script[n - 1] if n <= len(self.script) else end()
        if callable(step):
            step = step(n, len(self.calls[0].data))
        if isinstance(step, BaseException):
            raise step
        return Resp(step)


def shown(out):
    """The four numbers `budget show` prints, read loosely: each label followed by its number."""
    got = {}
    for k in ("stop_usd", "spent_usd", "held_usd", "remaining_usd"):
        mt = re.search(k + r"[^0-9\-]*(-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)", out)
        if mt:
            got[k] = float(mt.group(1))
    return got


# A child process: imports spec_review with the same stubs and runs one scope, holds the ledger lock,
# or hangs inside its first request. argv: scripts_dir mode doc ledger prices scratch
CHILD = r'''
import json, os, sys, time, urllib.request
sys.path.insert(0, sys.argv[1])
import spec_review as sr
mode, doc, ledger, prices, scratch = sys.argv[2:7]
real = sr.load_prices
sr.load_prices = lambda path=None: real(prices)
sr.headers = lambda: {"content-type": "application/json"}
n = [0]
class Resp:
    def __init__(s, b): s.b = json.dumps(b).encode()
    def read(s): return s.b
    def __enter__(s): return s
    def __exit__(s, *a): return False
def fake(req, timeout=None):
    n[0] += 1
    with open(os.path.join(scratch, "requests"), "a") as f:
        f.write("%d\n" % os.getpid())
    if mode == "hang":
        open(os.path.join(scratch, "entered"), "w").close()
        time.sleep(120)
    time.sleep(1.0)   # keep the scope open while the other process decides
    if n[0] == 1:   # no usage: the scope settles at its reservation
        return Resp({"stop_reason": "pause_turn", "content": [{"type": "server_tool_use", "id": "s", "name": "advisor", "input": {}}]})
    return Resp({"stop_reason": "end_turn", "content": [{"type": "text", "text": "```json\n{\"contradictions\": [], \"ambiguities\": []}\n```"}]})
urllib.request.urlopen = fake
if mode == "hold":
    from review_run import locked
    with locked(ledger):
        open(os.path.join(scratch, "locked"), "w").close()
        time.sleep(120)
if mode == "race":
    while not os.path.exists(os.path.join(scratch, "go")):
        time.sleep(0.005)
try:
    sr.cmd_run(doc, ["FX-001"], ledger=ledger)
    print("ran")
except Exception as e:
    print("refused: %s" % e)
'''


class Budget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.doc = self.d / "DESIGN.md"
        self.doc.write_text(DESIGN)
        self.ledger = self.d / "ledger.json"
        self.prices = prices_file(self.d / "prices.json")
        # an operator's ledger, home and credential are never reached
        env = mock.patch.dict(os.environ, {"GSTACK_SPEND_LEDGER": str(self.d / "no-ledger.json"),
                                           "HOME": str(self.d / "home")})
        env.start(); self.addCleanup(env.stop)
        os.environ.pop("GSTACK_ANTHROPIC_ENV", None)
        real = sr.load_prices
        for p in (mock.patch.object(sr, "load_prices", lambda path=None: real(self.prices)),
                  mock.patch.object(sr, "headers", lambda: {"content-type": "application/json"})):
            p.start(); self.addCleanup(p.stop)
        self.net = Urlopen()
        self.use_net(self.net)
        # the smallest any reservation can be: b is at least the scope text's own bytes
        self.r_low = bound(len(sr.scope(DESIGN, "FX-001")[1].encode()))

    def use_net(self, net):
        self.net = net
        p = mock.patch.object(urllib.request, "urlopen", net)
        p.start(); self.addCleanup(p.stop)
        return net

    def main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sr.main([str(a) for a in args])
        return code, out.getvalue() + err.getvalue()

    def init(self, stop, ledger=None):
        code, out = self.main("budget", "init", "--stop-usd", stop, "--ledger", ledger or self.ledger)
        self.assertEqual(code, 0, out)

    def write_ledger(self, data, path=None):
        path = path or self.ledger
        Path(path).write_text(json.dumps(data))
        return path

    def read(self):
        return json.loads(self.ledger.read_text())

    def run_real(self, items=("FX-001",), ledger=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return sr.cmd_run(self.doc, list(items), ledger=str(ledger or self.ledger))

    def assertRefusedBeforeAnyRequest(self, prefix=None, ledger=None):
        with self.assertRaises(sr.Refused) as cm:
            self.run_real(ledger=ledger)
        if prefix:
            self.assertTrue(str(cm.exception).startswith(prefix), str(cm.exception))
        self.assertEqual(len(self.net.calls), 0, "a request was sent")
        return str(cm.exception)

    def settled_row(self):
        (row,) = self.read()["reservations"]
        self.assertEqual(row["state"], "settled", row)
        self.assertIsNotNone(row["settled_at"])
        self.assertFalse([r for r in self.read()["reservations"] if r["state"] == "held"])
        return row

    # --- criterion 3: the bound ---

    def test_worst_case_usd_is_criterion_3s_formula(self):
        prices = sr.load_prices(self.prices)
        for b in (0, 1234, 20000, 60000):
            self.assertAlmostEqual(sr.worst_case_usd(b, EX, ADV, prices), bound(b), places=9)
        self.assertGreater(sr.worst_case_usd(2000, EX, ADV, prices), sr.worst_case_usd(1000, EX, ADV, prices))

    # --- criterion 2: no ledger, no stop_usd, not enough room ---

    def test_no_ledger_refuses_with_no_request(self):
        self.assertRefusedBeforeAnyRequest(ledger=self.d / "absent.json")

    def test_unset_env_uses_the_default_ledger_and_refuses_when_it_is_absent(self):
        os.environ.pop("GSTACK_SPEND_LEDGER")   # HOME is the temp dir, so the default is ours
        with self.assertRaises(sr.Refused), contextlib.redirect_stdout(io.StringIO()):
            sr.cmd_run(self.doc, ["FX-001"])
        self.assertEqual(len(self.net.calls), 0)

    def test_a_ledger_without_stop_usd_is_malformed_and_refuses(self):
        self.write_ledger({"schema": "spend-ledger/1", "spent_usd": 0, "reservations": []})
        before = self.ledger.read_bytes()
        self.assertRefusedBeforeAnyRequest()
        self.assertEqual(self.ledger.read_bytes(), before)
        code, out = self.main("budget", "show", "--ledger", self.ledger)
        self.assertEqual(code, 1, out)

    def test_remaining_below_the_reservation_refuses_exit_1_nothing_reserved(self):
        self.init(self.r_low * 0.5)
        before = self.read()
        code, out = self.main("run", self.doc, "--items", "FX-001", "--ledger", self.ledger)
        self.assertEqual(code, 1, out)
        self.assertIn("refused: budget_refused:", out)
        self.assertEqual(len(self.net.calls), 0)
        self.assertEqual(self.read(), before, "a refused run changed the ledger")
        self.assertEqual(self.read()["reservations"], [])
        os.environ["GSTACK_SPEND_LEDGER"] = str(self.ledger)   # same refusal through the env variable
        with self.assertRaises(sr.Refused) as cm, contextlib.redirect_stdout(io.StringIO()):
            sr.cmd_run(self.doc, ["FX-001"])
        self.assertTrue(str(cm.exception).startswith("budget_refused:"), str(cm.exception))
        self.assertEqual(len(self.net.calls), 0)

    def test_unlisted_model_refuses_before_any_request(self):
        for only in (EX, ADV):
            prices_file(self.prices, models=(only,))
            self.init(self.r_low * 10, ledger=self.d / f"l-{only}.json")
            self.assertRefusedBeforeAnyRequest(ledger=self.d / f"l-{only}.json")
            self.assertEqual(json.loads((self.d / f"l-{only}.json").read_text())["reservations"], [])

    def test_an_injected_transport_needs_no_ledger_and_no_prices(self):
        def no_prices(path=None):
            raise AssertionError("an injected transport read prices")
        with mock.patch.object(sr, "load_prices", no_prices):
            paths = sr.seed_clean(self.doc, ["FX-001"])
            self.assertTrue(paths[0].exists())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sr.cmd_run(self.doc, ["FX-002"], post=sr.stub_post(CLEAN)), 0)
        self.assertEqual(len(self.net.calls), 0)
        self.assertFalse((self.d / "no-ledger.json").exists(), "an injected transport touched the ledger")
        self.assertFalse((self.d / "home" / ".gstack").exists())

    # --- criteria 3 and 4: settlement never above the reservation under anything the bound allows ---

    def adversarial(self, split):
        """The most the bound allows: 8 requests (a reminder, then six resumptions), 10 executor
        iterations each re-reading the first body, framing, every earlier request's full output and all
        three advices, O output per request, and three advisor calls reading the whole transcript."""
        def tokens(n_in):
            if split == "input":
                return {"inp": n_in}
            if split == "cache_write":
                return {"cw": n_in}
            third = n_in // 3
            return {"inp": third, "cr": third, "cw": n_in - 2 * third}

        def request(r):
            def make(n, b):
                ex = [it(EX, out=O // N, **tokens(b + F_E + m + r * O + A * K)) for _ in range(N)]
                adv = ([it(ADV, out=M, kind="advisor_message", **tokens(F_A + b + F_E + m + R * O + A * K))]
                       if 2 <= r <= 4 else [])
                if r == 1:
                    return end(ex, text="no findings yet")   # no advisor call: the reminder follows
                return pause(ex + adv) if r < R else end(ex + adv)
            return make
        return Urlopen([request(r) for r in range(1, R + 1)])

    def test_adversarial_usage_never_settles_above_the_reservation(self):
        for split in ("input", "cache_write", "mixed"):
            with self.subTest(split=split):
                ledger = self.d / f"adv-{split}.json"
                self.init(self.r_low * 3, ledger=ledger)
                net = self.use_net(self.adversarial(split))
                self.run_real(ledger=ledger)
                self.assertEqual(len(net.calls), R)
                (row,) = json.loads(ledger.read_text())["reservations"]
                self.assertEqual(row["state"], "settled")
                self.assertLessEqual(row["actual_usd"], row["reserved_usd"] * (1 + 1e-9), row)
                self.assertAlmostEqual(row["reserved_usd"], bound(len(net.calls[0].data)), places=6)

    def test_settlement_sums_iterations_once_per_model_and_class(self):
        self.init(self.r_low * 3)
        first = [it(EX, inp=1000, out=200, cr=50, cw=300), it(ADV, inp=2000, out=100, cr=7, cw=11, kind="advisor_message")]
        second = [it(EX, inp=500, out=900, cr=4000), it(EX, inp=60, out=5, cw=70)]
        net = self.use_net(Urlopen([pause(first), end(second)]))
        self.assertEqual(self.run_real(), 0)
        self.assertEqual(len(net.calls), 2)
        row, led = self.settled_row(), self.read()
        expect = cost(first + second)
        self.assertAlmostEqual(row["actual_usd"], expect, places=12, msg="top-level usage counted twice, or a class mispriced")
        self.assertAlmostEqual(led["spent_usd"], expect, places=12)
        self.assertAlmostEqual(row["reserved_usd"], bound(len(net.calls[0].data)), places=6)
        self.assertEqual((row["scope"], row["doc"]), ("FX-001", self.doc.name))
        self.assertTrue(sr.record_path(self.doc, "FX-001").exists())

    def test_uncertain_usage_settles_at_least_the_reservation(self):
        good = pause([it(EX, inp=10, out=10)])
        bad_field = it(EX, inp=10, out=10)
        del bad_field["output_tokens"]
        http = lambda n, b: urllib.error.HTTPError(sr.API_URL, 529, "overloaded", {}, io.BytesIO(b'{"error": {"message": "overloaded"}}'))
        cases = {"missing usage": [good, end()],
                 "missing iterations": [good, {**end(), "usage": {"input_tokens": 5, "output_tokens": 5}}],
                 "missing field": [good, end([bad_field])],
                 "unlisted entry model": [good, end([it("claude-unlisted-9", inp=10, out=10)])],
                 "timeout": [good, socket.timeout("timed out")],
                 "http error": [good, http]}
        for name, script in cases.items():
            with self.subTest(case=name):
                ledger = self.d / f"u-{name.replace(' ', '-')}.json"
                self.init(self.r_low * 3, ledger=ledger)
                net = self.use_net(Urlopen(script))
                try:
                    self.run_real(ledger=ledger)
                except Exception:
                    pass   # a timeout or HTTP error may end the run; the ledger must still be settled
                self.assertEqual(len(net.calls), 2)
                led = json.loads(ledger.read_text())
                (row,) = led["reservations"]
                self.assertEqual(row["state"], "settled", row)
                self.assertGreaterEqual(row["actual_usd"], row["reserved_usd"], row)
                self.assertGreaterEqual(led["spent_usd"], row["reserved_usd"])

    def test_max_tokens_and_pause_cap_refusals_still_settle_what_was_sent(self):
        step = [it(EX, inp=100, out=20, cw=5), it(ADV, inp=50, out=9, kind="advisor_message")]
        for name, script, n in (("max_tokens", [pause(step), {**end(step), "stop_reason": "max_tokens"}], 2),
                                ("pause cap", [pause(step)] * 7, 7)):
            with self.subTest(case=name):
                ledger = self.d / f"r-{name.replace(' ', '-')}.json"
                self.init(self.r_low * 3, ledger=ledger)
                net = self.use_net(Urlopen(script))
                with self.assertRaises(sr.Refused):
                    self.run_real(ledger=ledger)
                self.assertEqual(len(net.calls), n)
                led = json.loads(ledger.read_text())
                (row,) = led["reservations"]
                self.assertEqual(row["state"], "settled", row)
                self.assertAlmostEqual(row["actual_usd"], cost(step) * n, places=12)
                self.assertAlmostEqual(led["spent_usd"], cost(step) * n, places=12)

    def test_an_actual_above_the_reservation_writes_the_record_then_stops_with_budget_overrun(self):
        self.init(self.r_low * 10)
        huge = [it(EX, inp=10 ** 10, out=10)]
        net = self.use_net(Urlopen([pause(huge), end([it(EX, inp=1, out=1)])]))
        code, out = self.main("run", self.doc, "--items", "FX-001,FX-002", "--ledger", self.ledger)
        self.assertEqual(code, 1, out)
        self.assertIn("refused: budget_overrun:", out)
        self.assertEqual(len(net.calls), 2, "the next scope sent a request after an overrun")
        self.assertTrue(sr.record_path(self.doc, "FX-001").exists(), "the overrun scope's record was not written")
        self.assertFalse(sr.record_path(self.doc, "FX-002").exists())
        actual = cost(huge + [it(EX, inp=1, out=1)])
        led = self.read()
        (row,) = led["reservations"]
        self.assertAlmostEqual(row["actual_usd"], actual, delta=actual * 1e-9)
        self.assertAlmostEqual(led["spent_usd"], actual, delta=actual * 1e-9)
        self.assertGreater(led["spent_usd"], led["stop_usd"])   # a valid ledger after an overrun
        # a second process reads the full actual
        p = subprocess.run([sys.executable, "-B", str(HERE / "spec_review.py"), "budget", "show", "--ledger", str(self.ledger)],
                           capture_output=True, text=True, env=self.child_env(), timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        got = shown(p.stdout)
        self.assertAlmostEqual(got.get("spent_usd", -1), actual, delta=actual * 1e-3, msg=p.stdout)
        self.assertEqual(got.get("remaining_usd"), 0.0, p.stdout)
        # and the next run is refused before any request
        net2 = self.use_net(Urlopen())
        with self.assertRaises(sr.Refused) as cm:
            self.run_real(("FX-002",))
        self.assertTrue(str(cm.exception).startswith("budget_refused:"), str(cm.exception))
        self.assertEqual(len(net2.calls), 0)

    # --- concurrency: two processes, and a lock holder killed with SIGKILL ---

    def child_env(self):
        env = {k: v for k, v in os.environ.items() if k != "GSTACK_ANTHROPIC_ENV"}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    def child(self, mode, scratch):
        return subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(HERE), mode, str(self.doc), str(self.ledger),
                                 str(self.prices), str(scratch)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, env=self.child_env())

    def wait_for(self, path, procs, secs=30):
        t = time.monotonic()
        while not path.exists():
            if time.monotonic() - t > secs or any(p.poll() is not None for p in procs):
                for p in procs:
                    p.kill()
                self.fail(f"{path.name} never appeared: " + " | ".join((p.communicate()[0] or "") for p in procs))
            time.sleep(0.01)

    def test_two_processes_with_room_for_one_reservation_let_exactly_one_scope_send(self):
        self.init(self.r_low * 1.5)   # one reservation fits; two never do
        scratch = self.d / "race"; scratch.mkdir()
        procs = [self.child("race", scratch) for _ in range(2)]
        time.sleep(1.5)   # both imported and waiting
        (scratch / "go").touch()
        outs = [p.communicate(timeout=90)[0] for p in procs]
        reqs = (scratch / "requests").read_text().split() if (scratch / "requests").exists() else []
        self.assertEqual(len(set(reqs)), 1, f"processes that sent a request: {set(reqs)}; {outs}")
        self.assertEqual(sum("budget_refused:" in o for o in outs), 1, outs)
        led = self.read()
        self.assertEqual(len(led["reservations"]), 1, led)
        held = sum(r["reserved_usd"] for r in led["reservations"] if r["state"] == "held")
        self.assertLessEqual(led["spent_usd"] + held, led["stop_usd"], led)

    def test_kill_9_of_the_lock_holder_releases_the_lock_and_its_held_row_still_counts(self):
        self.init(self.r_low * 1.5)
        scratch = self.d / "kill"; scratch.mkdir()
        hang = self.child("hang", scratch)       # reserves, then dies inside its first request
        self.wait_for(scratch / "entered", [hang])
        hang.send_signal(signal.SIGKILL); hang.wait(timeout=10)
        (row,) = self.read()["reservations"]
        self.assertEqual(row["state"], "held", row)
        holder = self.child("hold", scratch)     # takes review_run.locked(ledger), then is killed holding it
        self.wait_for(scratch / "locked", [holder])
        holder.send_signal(signal.SIGKILL); holder.wait(timeout=10)
        t = time.monotonic()
        with self.assertRaises(sr.Refused) as cm:
            self.run_real()
        self.assertLess(time.monotonic() - t, 1.0, "the next reservation waited on a dead holder's lock")
        self.assertTrue(str(cm.exception).startswith("budget_refused:"), str(cm.exception))
        self.assertEqual(len(self.net.calls), 0)
        led = self.read()
        self.assertEqual([r["state"] for r in led["reservations"]], ["held"], "a dead process's held row was released")
        code, out = self.main("budget", "show", "--ledger", self.ledger)
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(shown(out).get("held_usd", -1), row["reserved_usd"], delta=0.01, msg=out)

    # --- criterion 1: budget init and show, and values that refuse ---

    def test_budget_init_creates_the_ledger_and_refuses_an_existing_one(self):
        self.init(50)
        led = self.read()
        self.assertEqual((led["schema"], led["stop_usd"], led["spent_usd"], led["reservations"]),
                         ("spend-ledger/1", 50, 0, []))
        before = self.ledger.read_bytes()
        for stop in (50, 10, 500):   # never lowers (or raises) a recorded commitment
            code, out = self.main("budget", "init", "--stop-usd", stop, "--ledger", self.ledger)
            self.assertEqual(code, 1, out)
            self.assertEqual(self.ledger.read_bytes(), before)

    def test_budget_init_refuses_nan_negative_and_infinite(self):
        for bad in ("nan", "-1", "inf", "-inf"):
            with self.subTest(stop=bad):
                path = self.d / f"init-{bad}.json"
                code, out = self.main("budget", "init", "--stop-usd", bad, "--ledger", path)
                self.assertEqual(code, 1, out)
                self.assertFalse(path.exists() and json.loads(path.read_text()).get("stop_usd") is not None, out)

    def test_budget_show_matches_the_ledger_and_clamps_remaining_at_zero(self):
        held = {"id": "h", "scope": "FX-001", "doc": "DESIGN.md", "reserved_usd": 3.0, "actual_usd": None,
                "state": "held", "reserved_at": "2026-11-21T00:00:00+00:00", "settled_at": None}
        settled = {**held, "id": "s", "reserved_usd": 5.0, "actual_usd": 4.0, "state": "settled",
                   "settled_at": "2026-11-21T00:01:00+00:00"}
        for name, spent, stop, rows, expect in (
                ("normal", 4.0, 10.0, [held, settled], {"held_usd": 3.0, "remaining_usd": 3.0}),
                ("overrun", 12.0, 10.0, [{**held, "reserved_usd": 1.0}], {"held_usd": 1.0, "remaining_usd": 0.0})):
            with self.subTest(case=name):
                path = self.write_ledger({"schema": "spend-ledger/1", "stop_usd": stop, "spent_usd": spent,
                                          "reservations": rows}, self.d / f"show-{name}.json")
                before = path.read_bytes()
                code, out = self.main("budget", "show", "--ledger", path)
                self.assertEqual(code, 0, out)
                got = shown(out)
                for k, v in {"stop_usd": stop, "spent_usd": spent, **expect}.items():
                    self.assertAlmostEqual(got.get(k, -99), v, delta=0.005, msg=f"{k}: {out}")
                self.assertEqual(path.read_bytes(), before, "budget show wrote the ledger")

    def test_nan_negative_or_infinite_ledger_values_refuse(self):
        ok_row = {"id": "h", "scope": "FX-001", "doc": "DESIGN.md", "reserved_usd": 1.0, "actual_usd": None,
                  "state": "held", "reserved_at": "2026-11-21T00:00:00+00:00", "settled_at": None}
        base = {"schema": "spend-ledger/1", "stop_usd": self.r_low * 10, "spent_usd": 0.0, "reservations": [ok_row]}
        bads = {"stop nan": {**base, "stop_usd": math.nan}, "stop negative": {**base, "stop_usd": -1.0},
                "stop inf": {**base, "stop_usd": math.inf}, "spent nan": {**base, "spent_usd": math.nan},
                "spent negative": {**base, "spent_usd": -0.5}, "spent inf": {**base, "spent_usd": math.inf},
                "held negative": {**base, "reservations": [{**ok_row, "reserved_usd": -1.0}]},
                "held inf": {**base, "reservations": [{**ok_row, "reserved_usd": math.inf}]},
                "settled nan": {**base, "reservations": [{**ok_row, "state": "settled", "actual_usd": math.nan,
                                                         "settled_at": "2026-11-21T00:01:00+00:00"}]}}
        for name, data in bads.items():
            with self.subTest(case=name):
                path = self.d / f"bad-{name.replace(' ', '-')}.json"
                path.write_text(json.dumps(data))   # Python writes NaN/Infinity literals
                before = path.read_bytes()
                self.assertRefusedBeforeAnyRequest(ledger=path)
                code, out = self.main("budget", "show", "--ledger", path)
                self.assertEqual(code, 1, out)
                self.assertEqual(path.read_bytes(), before, "a malformed ledger was rewritten")


if __name__ == "__main__":
    unittest.main()
