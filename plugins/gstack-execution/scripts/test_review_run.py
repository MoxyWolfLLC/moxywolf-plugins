#!/usr/bin/env python3
"""GR-001: review_run.py against temporary folders and stub workers. No network, no paid call."""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import peer_review  # noqa: E402
import review_run as rr  # noqa: E402

FINDING = ('{"findings":[{"finding_id":"F1","lane":"L","claim":"c","cited_clause":"a:1","class":"behavior_gap",'
           '"evidence":["a:1"],"smallest_fix":"x"}]}')
CODEX = f"""#!/bin/sh
for a; do p="$a"; done
printf '%s\\n' "$@" > argv.txt
echo $$ > pid.txt
env > env.txt
prev=""; last=""
for a; do [ "$prev" = "--output-last-message" ] && last="$a"; prev="$a"; done
case "$p" in
  *SLEEP*) sleep 30;;
  *BAD*) echo 'not json' > "$last";;
  *) echo '{FINDING}' > "$last";;
esac
"""
CLAUDE = f"""#!/bin/sh
env > env.txt
case "$2" in *BAD*) echo 'nope';; *) echo '{FINDING}';; esac
"""


def stub(dirpath, name, body):
    f = Path(dirpath) / name
    f.write_text(body)
    f.chmod(f.stat().st_mode | stat.S_IEXEC)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="review-run-"))
        self.ledger = self.tmp / "ledger.json"
        bins = self.tmp / "bin"
        bins.mkdir()
        stub(bins, "codex", CODEX)
        stub(bins, "claude", CLAUDE)
        p = mock.patch.dict(os.environ, {"PATH": f"{bins}:{os.environ['PATH']}", "OPENAI_API_KEY": "sk-test-not-real"})
        p.start()
        self.addCleanup(p.stop)
        self.prompt = self.tmp / "prompt.txt"
        self.prompt.write_text("review it")

    def run_state(self, run="r1"):
        return json.loads(self.ledger.read_text())["runs"][run]

    def events(self, kind, run="r1"):
        return [e for e in self.run_state(run)["events"] if e["event"] == kind]


class Limits(Base):
    def test_each_limit_refuses_its_own_dispatch(self):
        cases = [
            ("codex_calls", dict(codex_calls=1), [("fanout", "codex", "1", 0)], ("fanout", "codex", "1", 0)),
            ("fanouts", {}, [("fanout", "claude", "1", 0)], ("fanout", "claude", "2", 0)),
            ("rechecks", {}, [("recheck", "claude", "a", 0), ("recheck", "claude", "b", 0)], ("recheck", "claude", "c", 0)),
            ("dollars", {}, [("fanout", "claude", "1", 0.6)], ("fanout", "claude", "1", 0.6)),
        ]
        for counter, flags, before, refused in cases:
            run = f"r-{counter}"
            rr.init(self.ledger, run, **flags)
            for phase, tool, rnd, usd in before:
                rr.reserve(self.ledger, run, phase, "L", tool, rnd, usd)
            used_before = json.dumps(self.run_state(run)["used"])
            phase, tool, rnd, usd = refused
            with self.assertRaises(rr.Refused) as cm:
                rr.reserve(self.ledger, run, phase, "L2", tool, rnd, usd)
            self.assertEqual(cm.exception.counter, counter)
            self.assertEqual(json.dumps(self.run_state(run)["used"]), used_before)
            self.assertEqual(self.events("refused", run)[-1]["counter"], counter)

    def test_disputes_and_deadline_refuse(self):
        rr.init(self.ledger, "d", council_gate_ruling="ruling-ref")
        rr.reserve(self.ledger, "d", "council", "c1", "claude", usd=0.1)
        rr.reserve(self.ledger, "d", "council", "c2", "claude", usd=0.1)
        with self.assertRaises(rr.Refused) as cm:
            rr.reserve(self.ledger, "d", "council", "c3", "claude")
        self.assertEqual(cm.exception.counter, "disputes")
        rr.init(self.ledger, "late")
        past = rr.wall() + 91 * 60
        with mock.patch.object(rr, "wall", lambda: past), self.assertRaises(rr.Refused) as cm:
            rr.reserve(self.ledger, "late", "fanout", "L", "claude")
        self.assertEqual(cm.exception.counter, "deadline")

    def test_refusal_launches_nothing(self):
        rr.init(self.ledger, "r1", codex_calls=1)
        out = self.tmp / "out"
        self.assertEqual(rr.dispatch(self.ledger, "r1", out, "A", "codex", self.prompt), ("ok", None))
        with self.assertRaises(rr.Refused):
            rr.dispatch(self.ledger, "r1", out, "B", "codex", self.prompt, revision=1, attempt=1)
        self.assertFalse((out / "r1" / "B").exists())

    def test_a_flag_cannot_raise_a_limit(self):
        with self.assertRaises(ValueError) as cm:
            rr.init(self.ledger, "r1", codex_calls=11)
        self.assertIn("codex-calls", str(cm.exception))
        rr.init(self.ledger, "r1", codex_calls=5, dollars=0.5)
        self.assertEqual(self.run_state()["limits"]["codex_calls"], 5)

    def test_init_on_an_existing_id_refuses_and_resume_keeps_counters(self):
        rr.init(self.ledger, "r1")
        rr.reserve(self.ledger, "r1", "fanout", "L", "codex", usd=0.2)
        with self.assertRaises(ValueError):
            rr.init(self.ledger, "r1")
        before = rr.counters(self.run_state())
        rr.resume(self.ledger, "r1", draft_sha="f" * 64)
        self.assertEqual(rr.counters(self.run_state())["codex_calls"], before["codex_calls"])
        self.assertEqual(rr.counters(self.run_state())["dollars"], before["dollars"])
        self.assertEqual(self.events("resume")[0]["draft_sha256"], "f" * 64)


class CouncilGate(Base):
    def test_closed_by_default_opened_only_with_a_reference(self):
        rr.init(self.ledger, "r1")
        self.assertEqual(self.run_state()["council_gate"], "closed")
        with self.assertRaises(rr.Refused) as cm:
            rr.reserve(self.ledger, "r1", "council", "c", "claude")
        self.assertEqual(cm.exception.counter, "council_gate")
        self.assertEqual(self.run_state()["used"]["disputes"], 0)
        rr.resume(self.ledger, "r1", council_gate_ruling="Dorian ruling 2026-11-20")
        rr.reserve(self.ledger, "r1", "council", "c", "claude")
        self.assertEqual(self.run_state()["council_gate_ruling"], "Dorian ruling 2026-11-20")
        self.assertEqual(self.run_state()["used"]["disputes"], 1)


class Timeout(Base):
    def test_min_of_ceiling_and_time_left_and_refusal_at_zero(self):
        rr.init(self.ledger, "r1")
        self.assertEqual(rr.reserve(self.ledger, "r1", "fanout", "A", "codex")["timeout"], 900)
        rr.init(self.ledger, "short", deadline_minutes=5)
        self.assertLessEqual(rr.reserve(self.ledger, "short", "fanout", "A", "codex")["timeout"], 300)
        deadline = self.run_state("short")["deadline_at"]
        with mock.patch.object(rr, "wall", lambda: deadline - 0.5):
            t = rr.reserve(self.ledger, "short", "fanout", "B", "codex")
            self.assertAlmostEqual(t["timeout"], 0.5, places=3)
            self.assertTrue(t["deadline_bound"])
        with mock.patch.object(rr, "wall", lambda: deadline), self.assertRaises(rr.Refused) as cm:
            rr.reserve(self.ledger, "short", "fanout", "C", "codex")
        self.assertEqual(cm.exception.counter, "deadline")


class Manifest(Base):
    def files(self, draft="draft"):
        d = self.tmp / "in"
        d.mkdir(exist_ok=True)
        for n, c in {"draft": draft, "ev": "evidence", "pr": "prompt", "ls": "lessons", "key": "key"}.items():
            (d / n).write_text(c if n != "draft" else draft)
        return dict(draft=d / "draft", evidence=[d / "ev"], prompts=[d / "pr"], lessons=d / "ls", key=d / "key")

    def test_written_once_hash_in_ledger_width_only_change_accepted(self):
        rr.init(self.ledger, "r1")
        rr.init(self.ledger, "r2")
        f = self.files()
        m1 = rr.manifest(self.ledger, "r1", self.tmp / "m1.json", width=1, **f)
        self.assertEqual(self.run_state()["manifest"]["sha256"], rr.sha(self.tmp / "m1.json"))
        self.assertEqual(m1["sha256"], rr.sha(self.tmp / "m1.json"))
        with self.assertRaises(ValueError):
            rr.manifest(self.ledger, "r1", self.tmp / "m1b.json", width=1, **f)
        rr.manifest(self.ledger, "r2", self.tmp / "m2.json", width=3, **f)
        self.assertEqual(json.loads((self.tmp / "m2.json").read_text())["width"], 3)

    def test_any_other_change_is_refused(self):
        rr.init(self.ledger, "r1")
        rr.init(self.ledger, "r2")
        rr.manifest(self.ledger, "r1", self.tmp / "m1.json", width=1, **self.files())
        with self.assertRaises(ValueError) as cm:
            rr.manifest(self.ledger, "r2", self.tmp / "m2.json", width=1, **self.files(draft="a different draft"))
        self.assertIn("not the same manifest", str(cm.exception))


class Lanes(Base):
    def test_codex_command_comes_from_peer_reviews_builder(self):
        rr.init(self.ledger, "r1")
        out = self.tmp / "out"
        self.assertEqual(rr.dispatch(self.ledger, "r1", out, "A", "codex", self.prompt), ("ok", None))
        lane = out / "r1" / "A" / "rev1" / "attempt1"
        argv = (lane / "argv.txt").read_text().split("\n")[:-1]
        expect = peer_review.codex_argv(lane, lane / "schema.json", lane / "findings.json", "review it", ephemeral=True)
        self.assertEqual(argv, expect[1:])
        self.assertIn("--ephemeral", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertEqual(peer_review.codex_argv("r", "s", "l", "p")[:3], ["codex", "exec", "-C"])
        self.assertNotIn("--ephemeral", peer_review.codex_argv("r", "s", "l", "p"))

    def test_one_directory_per_lane_revision_and_attempt(self):
        rr.init(self.ledger, "r1")
        out = self.tmp / "out"
        rr.dispatch(self.ledger, "r1", out, "A", "claude", self.prompt)
        rr.dispatch(self.ledger, "r1", out, "A", "claude", self.prompt, revision=2, attempt=1, phase="recheck", rnd="x")
        rr.dispatch(self.ledger, "r1", out, "A", "claude", self.prompt, revision=2, attempt=2, phase="recheck", rnd="x")
        dirs = sorted(str(p.relative_to(out)) for p in out.rglob("findings.json"))
        self.assertEqual(dirs, ["r1/A/rev1/attempt1/findings.json", "r1/A/rev2/attempt1/findings.json", "r1/A/rev2/attempt2/findings.json"])

    def test_a_malformed_findings_file_fails_its_lane(self):
        rr.init(self.ledger, "r1")
        bad = self.tmp / "bad.txt"
        bad.write_text("BAD")
        for tool in ("codex", "claude"):
            status, reason = rr.dispatch(self.ledger, "r1", self.tmp / "out", f"L-{tool}", tool, bad, rnd="1")
            self.assertEqual(status, "failed", tool)
            self.assertEqual(self.run_state()["lanes"][f"L-{tool}/r1/a1"]["status"], "failed")
        self.assertIn("unparseable", reason)

    def test_findings_schema_refuses_a_missing_field_and_a_class_outside_the_four(self):
        f = self.tmp / "f.json"
        for body, word in ((json.dumps({"findings": [{"finding_id": "x"}]}), "missing"),
                           (FINDING.replace("behavior_gap", "style"), "class")):
            f.write_text(body)
            self.assertIn(word, rr.validate_findings(f))
        f.write_text(FINDING)
        self.assertIsNone(rr.validate_findings(f))

    def test_no_api_key_reaches_a_lane(self):
        self.assertFalse([k for k in rr.lane_env() if k.endswith("_API_KEY")])
        self.assertEqual(os.environ["OPENAI_API_KEY"], "sk-test-not-real")
        rr.init(self.ledger, "r1")
        out = self.tmp / "out"
        rr.dispatch(self.ledger, "r1", out, "A", "codex", self.prompt)
        rr.dispatch(self.ledger, "r1", out, "B", "claude", self.prompt)
        for lane in ("A", "B"):
            env = (out / "r1" / lane / "rev1" / "attempt1" / "env.txt").read_text()
            self.assertNotIn("_API_KEY", env)
            self.assertNotIn("sk-test-not-real", env)


class Events(unittest.TestCase):
    def test_peak_wait_and_draft_to_decision_on_a_known_list(self):
        def ev(kind, job, t, **kw):
            return {"event": kind, "job": job, "mono": t, **kw}
        events = [ev("admit", "A", 0), ev("admit", "B", 0), ev("admit", "Q", 0),  # Q is admitted and queued: never started
                  ev("start", "A", 1, admitted=0), ev("start", "B", 2, admitted=0),
                  ev("finish", "A", 5, admitted=0), ev("finish", "B", 6, admitted=0),
                  ev("admit", "D", 4.5), ev("start", "D", 5, admitted=4.5), ev("finish", "D", 8, admitted=4.5),  # starts as A ends: no third overlap
                  ev("disposition", "-", 10)]
        r = rr.compute_report(events)
        self.assertEqual(r["peak"], 2)
        self.assertEqual(r["review_wait_s"], 1 + 2 + 0.5)
        self.assertEqual(r["draft_to_decision_s"], 10)
        self.assertIsNone(rr.compute_report(events[:-1])["draft_to_decision_s"])

    def test_dispatch_writes_start_and_finish_with_admitted_time(self):
        d = Path(tempfile.mkdtemp(prefix="review-run-ev-"))
        stub(d, "claude", CLAUDE)
        prompt = d / "p"
        prompt.write_text("go")
        with mock.patch.dict(os.environ, {"PATH": f"{d}:{os.environ['PATH']}"}):
            rr.init(d / "l.json", "r1")
            rr.dispatch(d / "l.json", "r1", d / "out", "A", "claude", prompt)
        evs = json.loads((d / "l.json").read_text())["runs"]["r1"]["events"]
        start = next(e for e in evs if e["event"] == "start")
        fin = next(e for e in evs if e["event"] == "finish")
        admit = next(e for e in evs if e["event"] == "admit")
        self.assertEqual(start["admitted"], admit["mono"])
        self.assertEqual(fin["admitted"], admit["mono"])
        self.assertLessEqual(start["mono"], fin["mono"])


class Deadline(Base):
    def test_a_sleeping_stub_is_killed_and_its_pid_is_gone(self):
        rr.init(self.ledger, "r1", deadline_minutes=0.05)  # 3 seconds
        slow = self.tmp / "slow.txt"
        slow.write_text("SLEEP")
        out = self.tmp / "out"
        status, reason = rr.dispatch(self.ledger, "r1", out, "A", "codex", slow)
        self.assertEqual((status, reason), ("failed", "deadline_killed"))
        ev = self.events("deadline_killed")[0]
        self.assertTrue(ev["confirmed_gone"])
        pid = int((out / "r1" / "A" / "rev1" / "attempt1" / "pid.txt").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertFalse(rr._alive(ev["pgid"]))

    def test_without_the_timeout_wrapper_the_runner_kills_the_process_group_itself(self):
        rr.init(self.ledger, "r1", deadline_minutes=0.05)
        slow = self.tmp / "slow.txt"
        slow.write_text("SLEEP")
        out = self.tmp / "out"
        with mock.patch.object(rr.shutil, "which", lambda name: None):
            status, reason = rr.dispatch(self.ledger, "r1", out, "A", "codex", slow)
        self.assertEqual((status, reason), ("failed", "deadline_killed"))
        pid = int((out / "r1" / "A" / "rev1" / "attempt1" / "pid.txt").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_a_pid_still_present_is_exit_unconfirmed_and_fails_the_run(self):
        rr.init(self.ledger, "r1")
        with mock.patch.object(rr, "_alive", lambda pgid: True):
            status, reason = rr.dispatch(self.ledger, "r1", self.tmp / "out", "A", "claude", self.prompt)
        self.assertEqual((status, reason), ("failed", "exit_unconfirmed"))
        self.assertEqual(self.run_state()["status"], "failed")
        self.assertTrue(self.events("exit_unconfirmed"))
        with self.assertRaises(rr.Refused) as cm:
            rr.reserve(self.ledger, "r1", "fanout", "B", "claude")
        self.assertEqual(cm.exception.counter, "run_failed")


class Cli(Base):
    def test_cli_refusal_exits_1_naming_the_counter(self):
        self.assertEqual(rr.main(["init", "--run", "r1", "--ledger", str(self.ledger), "--max-codex-calls", "1"]), 0)
        self.assertEqual(rr.main(["reserve", "--run", "r1", "--ledger", str(self.ledger), "--lane", "A"]), 0)
        with mock.patch("sys.stdout") as so:
            code = rr.main(["reserve", "--run", "r1", "--ledger", str(self.ledger), "--lane", "B"])
        self.assertEqual(code, 1)
        self.assertIn("codex_calls", "".join(c.args[0] for c in so.write.call_args_list))


if __name__ == "__main__":
    unittest.main()
