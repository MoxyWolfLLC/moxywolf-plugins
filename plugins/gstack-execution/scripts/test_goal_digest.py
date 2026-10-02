"""GO-006: Dorian hears from the run at milestones and on escalation, and nothing else."""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_run as gr  # noqa: E402
import test_goal_run as tgr  # noqa: E402  its runner fixture

VOTE = lambda model, role, choice: {"model": model, "role": role, "choice": choice, "reason": "because"}


class Digests(tgr.RunnerFixture):
    def msgs(self, kind=None):
        return [m for m in gr.load("g1").get("messages", []) if kind in (None, m["kind"])]

    def escalations(self):
        return [m["trigger"] for m in self.msgs("escalation")]

    # ---- criterion 1 and 4: a digest per item, one at the end, and neither blocks ----

    def test_a_digest_per_item_answers_the_three_questions_and_doesnt_block(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# an item\n"), 1, unsure="whether scaffold covers b")
        d = self.msgs("digest")
        self.assertEqual(len(d), 1)
        self.assertEqual((d[0]["item"], d[0]["waits"]), (1, False))
        for part in ("Item 1 merged", "Close calls: none", "Least sure of: whether scaffold covers b",
                     "Against the brief: 1 of 3 items merged; 1 of 2 goal tests passing (tests/test_g.py::G.test_done still failing)"):
            self.assertIn(part, d[0]["text"])
        ok, step = self.next()
        self.assertEqual((ok, step["step"], step["item"]["n"]), (True, "build", 2))   # the digest gated nothing

    def test_a_close_call_and_its_dissent_are_in_the_digest(self):
        self.start()
        sha = self.item("done = False\nsafe = True\n# an item\n")
        gr.open_call(self.repo, "g1", "Which cache?", ["lru", "custom"], "claude/opus", "gpt/gpt-6", sha, base="main")
        gr.council_votes("g1", 1, [VOTE("gpt/gpt-6", "for", "lru"), VOTE("gemini/g3", "against", "custom")])
        gr.dorian_answers("g1", 1, "lru", "lru is fine")
        gr.merged(self.repo, "g1", sha, 1, unsure="x")
        text = self.msgs("digest")[-1]["text"]
        self.assertIn("#1 Which cache? (decided, lru)", text)
        self.assertIn("dissent on #1: gemini/g3 (against): custom - because", text)

    def test_one_digest_at_the_end_whatever_the_outcome(self):
        self.start()
        gr.stop("g1", "test")
        d = self.msgs("digest")
        self.assertEqual(len(d), 1)
        self.assertIn("Run stopped", d[0]["text"])
        self.assertIn("outcome stopped: test", d[0]["text"])

    # ---- criterion 2 and 4: each escalation trigger, with a stub run ----

    def test_the_review_cap_escalates(self):
        self.start()
        gr.failed("g1", 1, "rounds_exhausted after 2 rounds")
        self.assertEqual(self.escalations(), ["review_cap"])
        self.assertEqual(gr.load("g1")["outcome"], "stopped")

    def test_an_item_ending_another_way_doesnt_escalate_but_the_end_is_reported(self):
        self.start()
        gr.failed("g1", 1, "review_unavailable")
        self.assertEqual(self.escalations(), [])
        self.assertEqual(len(self.msgs("digest")), 1)

    def test_spend_at_eighty_percent_escalates(self):
        self.start()
        Path(os.environ["GSTACK_GOAL_RUN_DIR"], "g1", "spend.jsonl").write_text(
            json.dumps({"provider": "openrouter", "cost": "2.40", "transport": "openrouter"}) + "\n")
        self.next()
        self.assertEqual(self.escalations(), ["spend"])
        self.assertIn("openrouter spent $2.40", self.msgs("escalation")[0]["text"])

    def test_a_change_outside_the_envelope_escalates(self):
        self.start()
        self.git("switch", "-q", "goal/g1")
        sha = self.commit("outside", {"lib/x.py": "x = 1\n"})
        self.git("switch", "-q", "main")
        gr.open_call(self.repo, "g1", "Keep lib/x.py?", ["keep", "drop"], "claude/opus", "gpt/gpt-6", sha, base="main")
        self.assertEqual(self.escalations(), ["outside_envelope"])
        self.assertIn("lib/x.py is outside the envelope", self.msgs("escalation")[0]["text"])

    def test_the_same_file_in_blocking_findings_on_consecutive_items_escalates_and_waits(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# 1\n"), 1, unsure="x", review_files=["goalmod.py"])
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# 2\n"), 2, unsure="y", review_files=["goalmod.py", "helper.py"])
        self.assertEqual(self.escalations(), ["repeat_finding"])
        e = self.msgs("escalation")[0]
        self.assertIn("goalmod.py on items 1 and 2 in a row", e["text"])
        ok, out = self.next()
        self.assertIsNone(ok)                                     # it holds the run
        self.assertEqual(out["escalations"][0]["trigger"], "repeat_finding")
        with self.assertRaisesRegex(gr.Refused, "own words"):
            gr.acknowledge("g1", e["n"], " ")
        gr.acknowledge("g1", e["n"], "seen it, go on")
        ok, step = self.next()
        self.assertEqual((ok, step["item"]["n"]), (True, 3))

    def test_different_files_or_a_gap_dont_escalate(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# 1\n"), 1, unsure="x", review_files=["goalmod.py"])
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# 2\n"), 2, unsure="y", review_files=["helper.py"])
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# 3\n"), 3, unsure="z", review_files=["goalmod.py"])
        self.assertEqual(self.escalations(), [])

    def test_a_goal_test_regression_escalates(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 1, unsure="x")
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# an item\n"), 2, unsure="y")
        self.assertEqual(self.escalations(), ["regression"])
        self.assertIn("passed before and is now failed", self.msgs("escalation")[0]["text"])
        heads = [m["text"].splitlines()[0] for m in self.msgs("digest")]
        self.assertEqual(heads, ["Item 1 merged", "Item 2 merged", "Run stopped"])   # the item that regressed has its digest

    def test_spend_crossing_its_stop_inside_an_item_escalates_at_the_next_action(self):
        self.start()
        self.assertEqual(gr.act(self.repo, "g1", "review.send_code", "codex", self.envs, base="main")["allowed"], "review.send_code")
        Path(os.environ["GSTACK_GOAL_RUN_DIR"], "g1", "spend.jsonl").write_text(
            json.dumps({"provider": "openrouter", "cost": "2.40", "transport": "openrouter"}) + "\n")
        with self.assertRaisesRegex(gr.Refused, "the run stopped"):
            gr.act(self.repo, "g1", "external.model_call", "openai/gpt-6-astra", self.envs, base="main")
        self.assertEqual((self.escalations(), gr.load("g1")["outcome"]), (["spend"], "stopped"))

    def test_a_ledger_refusal_thats_dorians_escalates_and_holds(self):
        self.start()
        with self.assertRaisesRegex(gr.Refused, "Dorian's call"):
            gr.act(self.repo, "g1", "net.connect", "api.unknown.example", self.envs, base="main")
        self.assertEqual(self.escalations(), ["dorian_call"])
        n = self.msgs("escalation")[0]["n"]
        self.assertIsNone(self.next()[0])
        with self.assertRaisesRegex(gr.Refused, "holds the run"):
            gr.act(self.repo, "g1", "vcs.push", "build/GX-1-a", self.envs, base="main")
        gr.acknowledge("g1", n, "not that host; carry on")
        self.assertEqual(gr.act(self.repo, "g1", "vcs.push", "build/GX-1-a", self.envs, base="main")["allowed"], "vcs.push")
        self.assertTrue(self.next()[0])

    def test_a_resync_outside_the_envelope_escalates_and_holds(self):
        self.start()
        self.origin()
        gr.merged(self.repo, "g1", self.item("done = True\nsafe = True\n"), 1, unsure="x")
        self.git("switch", "-q", "goal/g1")
        final = self.commit("run record", {"goal-runs/g1/RESULT.md": "record\n"})
        self.git("switch", "-q", "main")
        st = gr.load("g1"); st.update(finalize_pr=8, final_pr=9, finalized_head=final); gr.save(st)
        m = self.commit("main moves", {"other/m.py": "m = 1\n"})
        self.git("switch", "-q", "goal/g1")
        self.git("merge", "-q", "--no-ff", "--no-commit", m)
        (self.repo / "lib").mkdir(); (self.repo / "lib/x.py").write_text("x = 1\n")
        self.git("add", "-A"); self.git("commit", "-q", "-m", "sync main")
        head = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "main")
        with self.assertRaisesRegex(gr.Refused, "envelope check refuses"):
            gr.resync(self.repo, "g1", head, base="main")
        e = self.msgs("escalation")[-1]
        self.assertEqual((e["trigger"], e["status"]), ("outside_envelope", "open"))
        with self.assertRaisesRegex(gr.Refused, "holds the run"):
            gr.resync(self.repo, "g1", head, base="main")

    def test_a_holdout_failure_escalates(self):
        self.start()
        out = gr.holdout_failed("g1", "2 of 5 holdout tests failed")
        self.assertEqual(out["outcome"], "stopped")
        self.assertEqual(self.escalations(), ["holdout"])

    def test_a_call_thats_dorians_escalates(self):
        self.start()
        self.git("switch", "-q", "goal/g1")
        sha = self.commit("dep", {"requirements.txt": "requests\n"})
        self.git("switch", "-q", "main")
        gr.open_call(self.repo, "g1", "Add requests?", ["yes", "no"], "claude/opus", "gpt/gpt-6", sha, base="main")
        self.assertEqual(self.escalations(), ["dorian_call"])

    def test_a_split_council_escalates_and_a_unanimous_one_doesnt(self):
        self.start()
        sha = self.item("done = False\nsafe = True\n# an item\n")
        for n, against in ((1, "lru"), (2, "custom")):
            gr.open_call(self.repo, "g1", f"Q{n}", ["lru", "custom"], "claude/opus", "gpt/gpt-6", sha, base="main")
            gr.council_votes("g1", n, [VOTE("gpt/gpt-6", "for", "lru"), VOTE("gemini/g3", "against", against)])
        self.assertEqual(self.escalations(), ["dorian_call"])
        self.assertIn("The council split on call #2", self.msgs("escalation")[0]["text"])

    # ---- criterion 3: every message is in the run record, and printed once ----

    def test_every_digest_and_escalation_is_in_the_record(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# an item\n"), 1, unsure="x")
        gr.holdout_failed("g1", "boom")
        rec = gr.record("g1")
        self.assertIn("## Digests and escalations", rec)
        for m in self.msgs():
            self.assertIn(f"{m['n']}. {m['at']} {m['kind']}", rec)
        self.assertIn("escalation (holdout)", rec)

    def test_the_cli_prints_new_messages_once(self):
        self.start()
        gr.merged(self.repo, "g1", self.item("done = False\nsafe = True\n# an item\n"), 1, unsure="x")
        first = [m["n"] for m in gr.outbox("g1")]
        self.assertEqual(first, [1])
        self.assertEqual(gr.outbox("g1"), [])
        self.assertTrue(all(m["delivered"] for m in self.msgs()))


if __name__ == "__main__":
    unittest.main()
