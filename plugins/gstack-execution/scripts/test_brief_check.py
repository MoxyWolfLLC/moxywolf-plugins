#!/usr/bin/env python3
"""XE-049.18: brief checks before builders launch, and the "why" after a failure. The model call is stubbed."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief_check  # noqa: E402
import goal_new  # noqa: E402
import goal_run as gr  # noqa: E402
import swarm  # noqa: E402
from test_goal_run import RunnerFixture  # noqa: E402

BRIEF = "Add a `--fast` flag to merge.py and run `widgetctl sync` after it.\nKeep it quick."
REPLY = json.dumps([
    {"kind": "ambiguous", "quote": "Keep it quick.", "question": "Quick to run, or a small diff?"},
    {"kind": "unknown_tool", "quote": "widgetctl sync", "question": "What is widgetctl and what does sync change?"}])


def stub(reply):
    return lambda prompt: reply


class Check(unittest.TestCase):
    def test_an_ambiguous_instruction_and_an_unknown_command_each_produce_an_entry(self):
        entries = brief_check.check(BRIEF, stub(REPLY))
        self.assertEqual([(e["id"], e["kind"], e["settlement"]) for e in entries],
                         [("B1", "ambiguous", "open"), ("B2", "unknown_tool", "open")])
        self.assertTrue(all(e["quote_found"] for e in entries))

    def test_a_clear_brief_has_no_entries(self):
        self.assertEqual(brief_check.check(BRIEF, stub("[]")), [])

    def test_a_reply_that_isnt_a_list_is_refused_not_read_as_clear(self):
        for bad in ("Looks fine to me.", '[{"kind": "vague", "quote": "x", "question": "y"}]'):
            with self.assertRaises(brief_check.Refused):
                brief_check.check(BRIEF, stub(bad))

    def test_each_call_counts_in_the_goal_spend_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d, "spend.jsonl"); ledger.touch()
            os.environ["GSTACK_GOAL_LEDGER"] = str(ledger)
            try:
                brief_check.check(BRIEF, stub("[]"))
            finally:
                del os.environ["GSTACK_GOAL_LEDGER"]
            self.assertEqual(json.loads(ledger.read_text()), {"provider": "anthropic", "cost": None, "transport": "anthropic"})


class AtDraft(unittest.TestCase):
    def test_an_entry_only_dorian_can_answer_lands_in_the_draft_brief(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d, "goals", "g1"); g.mkdir(parents=True)
            (g / "GOAL.md").write_text("# Goal\n\n## Outcome\n\nA thing.\n")
            (g / "PLAN.md").write_text("1. scaffold\n   - helper.py exists\n")
            found = goal_new.cmd_brief_check(g, call=stub(REPLY))
            self.assertEqual(len(found["1"]), 2)
            q = [{"item": 1, "quote": "widgetctl sync", "question": "May the build run widgetctl at all?"}]
            goal_new.cmd_brief_check(g, dorian=q)
            goal_new.cmd_brief_check(g, dorian=q)          # written again, the section is replaced, not doubled
            text = (g / "GOAL.md").read_text()
            self.assertEqual(text.count(goal_new.QUESTIONS), 1)
            self.assertIn("May the build run widgetctl at all?", text)
            self.assertIn("A thing.", text)


class AfterApproval(RunnerFixture):
    def test_an_unchecked_item_isnt_handed_to_a_builder(self):
        self.start(checked=False)
        ok, step = self.next()
        self.assertEqual((ok, step["step"], step["items"]), (True, "brief_check", [1]))
        gr.brief_check("g1", 1, BRIEF, stub("[]"))
        self.assertEqual(self.next()[1]["step"], "build")

    def test_an_entry_settled_from_the_design_is_recorded_and_frees_the_builder(self):
        self.start(checked=False)
        gr.brief_check("g1", 1, BRIEF, stub(REPLY))
        ok, step = self.next()
        self.assertEqual((step["step"], [e["id"] for e in step["entries"]["1"]]), ("settle", ["B1", "B2"]))
        gr.settle("g1", 1, "B1", "settled", "brief now says: a small diff, under 50 lines")
        gr.settle("g1", 1, "B2", "settled", "brief now quotes widgetctl's usage line from DESIGN.md")
        self.assertEqual(self.next()[1]["step"], "build")
        e = gr.load("g1")["brief_checks"]["1"]["entries"][0]
        self.assertEqual((e["settlement"], e["how"]), ("settled", "brief now says: a small diff, under 50 lines"))
        self.assertIn("B1 ambiguous", gr.record("g1"))

    def test_an_entry_only_dorian_can_answer_after_approval_stops_the_launch_and_escalates(self):
        self.start(checked=False)
        gr.brief_check("g1", 1, BRIEF, stub(REPLY))
        gr.settle("g1", 1, "B1", "settled", "a small diff")
        gr.settle("g1", 1, "B2", "needs_dorian", "May the build run widgetctl at all?")
        ok, out = self.next()
        self.assertIsNone(ok)
        self.assertEqual([e["id"] for e in out["waiting_on_brief"]["1"]], ["B2"])
        msg = gr.load("g1")["messages"][-1]
        self.assertEqual((msg["kind"], msg["trigger"]), ("escalation", "brief"))
        gr.settle("g1", 1, "B2", "settled", "Dorian: “yes, sync only”")
        self.assertEqual(self.next()[1]["step"], "build")

    def test_a_failures_report_names_the_answers_path_and_never_embeds_it(self):
        self.start()
        answer = "I read 'quick' as fewer tests, so I skipped the slow suite"
        w = gr.why("g1", "item 1's tests failed: test_slow", answer, item=1)
        self.assertIn("state.json whys[0]", w["at"])
        report = gr.record("g1")
        self.assertIn(w["at"], report)
        self.assertNotIn(answer, report)
        self.assertNotIn(answer, json.dumps(gr.load("g1")["messages"]))
        later = self.next()[1]["whys"]                    # the next attempt's brief: the path, not the text
        self.assertEqual(later, [{"failure": "item 1's tests failed: test_slow", "answer_at": w["at"],
                                  "readable_by_family": "claude"}])      # the builder's family gave it


class Swarm(unittest.TestCase):
    def test_the_coordinator_holds_an_item_whose_brief_isnt_settled(self):
        with tempfile.TemporaryDirectory() as d:
            goal = Path(d, "goal"); goal.mkdir()
            (goal / "PLAN.md").write_text("1. one\n   - a\n2. two\n   - b\n")
            (goal / "DEPS.json").write_text(json.dumps({"version": 1, "max_workers": 2, "items": {
                "1": {"id": "one", "writes": ["a.py"]}, "2": {"id": "two", "writes": ["b.py"]}}}))
            Path(d, "state.json").write_text(json.dumps({"brief_checks": {
                "1": {"entries": []},
                "2": {"entries": [{"id": "B1", "settlement": "needs_dorian"}]}}}))
            run = Path(d, "swarm")
            swarm.init(run, goal, "abc", 10)
            out = swarm.tick(run)
            self.assertEqual([c["id"] for c in out["dispatch"]], ["one"])
            self.assertIn("brief check not settled", next(w["why"] for w in out["waiting"] if w["id"] == "two"))


if __name__ == "__main__":
    unittest.main()
