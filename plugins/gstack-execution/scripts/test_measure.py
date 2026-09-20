#!/usr/bin/env python3
"""XE-012 acceptance: a gstack run records what it cost, and the report scores the predictions.

The failures these pin are the quiet ones. A token field that reads 0 when nothing was measured
looks like a cheap run. A transcript counted per entry instead of per message looks like an
expensive one (the first hand count of 2026-09-19 overstated cache reads 1.9x). A human's verdict
overwritten by a re-record looks like the machine agreeing with itself.
"""
import json, os, subprocess, sys, tempfile, unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr
import measure
import test_evidence_links as _tel   # not imported by name: unittest would re-run its tests here

CLEAN = {"verdict": "no_blocking_findings",
         "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
         "findings": [], "blocker_resolutions": []}


def usage(i=1, o=10, cw=100, cr=1000):
    return {"input_tokens": i, "output_tokens": o, "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr}


class RunRecord(unittest.TestCase):
    _L = _tel.LinkTests
    setUp = _L.setUp
    sh, write, ns, open_review, fake_round = _L.sh, _L.write, _L.ns, _L.open_review, _L.fake_round

    def transcript(self, rows):
        p = self.tmp / "session.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows))
        return p

    def passed_review(self):
        rid = self.open_review()
        self.assertEqual(self.fake_round(rid, CLEAN), "no_blocking_findings")
        return rid

    def test_record_carries_the_run_and_its_window(self):
        rid = self.passed_review()
        start = self.sh("log", "--reverse", "--format=%cI", f"{self.base}..{self.head}").splitlines()[0]
        tr = self.transcript([{"type": "assistant", "timestamp": "2099-01-01T00:00:00Z",
                               "message": {"id": "late", "model": "m", "usage": usage(), "content": []}}])
        rec = measure.build_record(rid, transcript=tr, until="2099-12-31T00:00:00Z")
        self.assertEqual(rec["review_id"], rid)
        self.assertEqual(rec["outcome"], "no_blocking_findings")
        self.assertEqual(rec["rounds"], 1)
        self.assertEqual(rec["vocabulary_version"], pr.VOCAB_VERSION)
        self.assertEqual(measure._ts(rec["window_start"]), measure._ts(start))
        self.assertEqual(rec["builder_turns"], 1)
        self.assertEqual(rec["correct"], "pending")
        # the fixture reviewer reports no usage, so the reviewer total is unknown, not zero
        self.assertIsNone(rec["reviewer_tokens"])
        self.assertEqual(rec["reviewer_tokens_per_round"], ["not_reported"])
        self.assertIn("not reported", rec["reviewer_tokens_reason"])

    def test_an_unreadable_transcript_is_null_with_a_reason_not_zero(self):
        rid = self.passed_review()
        rec = measure.build_record(rid, transcript=self.tmp / "gone.jsonl")
        for k in ("builder_total_tokens", "builder_cache_read_tokens", "builder_turns"):
            self.assertIsNone(rec[k], k)
        self.assertIn("not readable", rec["builder_tokens_reason"])

    def test_one_message_logged_as_several_entries_is_counted_once(self):
        tr = self.transcript([
            {"type": "assistant", "timestamp": "2026-09-19T10:00:00Z", "message": {"id": "a", "usage": usage(), "content": [{"type": "text"}]}},
            {"type": "assistant", "timestamp": "2026-09-19T10:00:01Z", "message": {"id": "a", "usage": usage(), "content": [{"type": "tool_use", "id": "t"}]}}])
        got, _ = measure.transcript_usage(tr, "2026-09-19T09:00:00Z", "2026-09-19T11:00:00Z")
        self.assertEqual((got["builder_turns"], got["builder_tool_calls"], got["builder_cache_read_tokens"]), (1, 1, 1000))

    def test_release_writes_the_note_or_says_it_did_not(self):
        rid = self.passed_review()
        vault = self.tmp / "vault"
        os.environ["GSTACK_MEASURE_DIR"] = str(vault)
        try:
            with redirect_stderr(StringIO()) as err, self.assertRaises(pr.ReviewError):
                pr.cmd_release(self.ns(review_id=rid, target="main", observation=[]))
        finally:
            os.environ.pop("GSTACK_MEASURE_DIR")
        notes = list(vault.glob(f"*-{rid}.md"))
        self.assertEqual(len(notes), 1, err.getvalue())
        self.assertEqual(measure.read_note(notes[0])["type"], "gstack-run")
        self.assertTrue((vault / "gstack-runs.base").exists())
        self.assertIn("measurement recorded", err.getvalue())
        with redirect_stderr(StringIO()) as err2:
            self.assertIsNone(pr.record_measurement(rid))
        self.assertIn("GSTACK_MEASURE_DIR is unset", err2.getvalue())

    def test_a_rerecord_keeps_the_humans_verdict(self):
        rid = self.passed_review()
        vault = self.tmp / "vault"
        note = measure.write_note(vault, measure.build_record(rid, transcript=self.tmp / "none"))
        note.write_text(note.read_text().replace('correct: "pending"', "correct: true")
                                         .replace('defect_traced: "pending"', "defect_traced: false"))
        measure.write_note(vault, measure.build_record(rid, transcript=self.tmp / "none"))
        got = measure.read_note(note)
        self.assertIs(got["correct"], True)
        self.assertIs(got["defect_traced"], False)
        self.assertEqual(len(list(vault.glob(f"*-{rid}.md"))), 1)


def run(v, correct=True, tokens=1000, cache=950, rounds=1, vocab_repeat=0, thin=False, outcome="no_blocking_findings", traced=False, model="m1"):
    return {"type": "gstack-run", "vocabulary_version": v, "correct": correct, "builder_total_tokens": tokens,
            "builder_cache_read_tokens": cache, "rounds": rounds, "repeat_findings": vocab_repeat, "repeat_findings_vocab": vocab_repeat,
            "thin_review": thin, "outcome": outcome, "defect_traced": traced, "builder_models": [model], "reviewer_tokens": 5}


class Predictions(unittest.TestCase):
    def test_nothing_recorded_is_insufficient_data_everywhere(self):
        _, _, preds = measure.score([])
        self.assertEqual({v for v, _ in preds.values()}, {"insufficient data"})
        self.assertIn("examined nothing", measure.report_text([], "n/a"))

    def test_p1_compares_the_first_two_qualifying_versions_and_counts_only_correct_runs(self):
        runs = [run("1.0.0", tokens=1000) for _ in range(10)] + [run("1.1.0", tokens=800) for _ in range(10)]
        self.assertEqual(measure.score(runs)[2]["P1"][0], "supported")
        runs += [run("1.1.0", correct="pending", tokens=5000) for _ in range(3)]
        # F1 (review 20260919-213145): criterion 5 counts only runs marked true, numerator included
        self.assertEqual(measure.score(runs)[2]["P1"][0], "supported")
        self.assertEqual(measure.score(runs)[1]["1.1.0"]["builder_tokens"], 800 * 10 + 5000 * 3)   # still visible in total
        runs += [run("1.1.0", tokens=3000) for _ in range(10)]
        self.assertEqual(measure.score(runs)[2]["P1"][0], "refuted")
        few = [run("1.0.0") for _ in range(10)] + [run("1.1.0") for _ in range(9)]
        self.assertEqual(measure.score(few)[2]["P1"][0], "insufficient data")

    def test_p1_names_a_model_change(self):
        runs = [run("1.0.0", tokens=1000) for _ in range(10)] + [run("1.1.0", tokens=800, model="m2") for _ in range(10)]
        self.assertIn("model change", measure.score(runs)[2]["P1"][1])

    def test_p2_needs_nine_in_ten_runs_at_ninety_percent(self):
        runs = [run("1.0.0", cache=950) for _ in range(9)] + [run("1.0.0", cache=100)]
        self.assertEqual(measure.score(runs)[2]["P2"][0], "supported")
        runs[0] = run("1.0.0", cache=100)
        self.assertEqual(measure.score(runs)[2]["P2"][0], "refuted")

    def test_no_prediction_is_scored_from_a_version_short_of_ten_correct_runs(self):
        """F3 (review 20260919-212511): P2-P4 had counted runs across versions, ignoring criterion 6."""
        runs = [run("1.0.0", correct="pending") for _ in range(30)]
        self.assertEqual({v for v, _ in measure.score(runs)[2].values()}, {"insufficient data"})

    def test_report_carries_cache_share_reviewer_per_correct_and_upkeep(self):
        """F1, F2 (review 20260919-212511)."""
        runs = [run("1.0.0") for _ in range(10)]
        runs[0]["touches_vocabulary"] = True
        text = measure.report_text(runs, "n/a")
        self.assertIn("cache-read share of builder tokens 95.0%", text)
        self.assertIn("reviewer tokens 50 (reported rounds only); per correct run 5", text)
        self.assertIn("vocabulary upkeep (correct runs that changed vocabulary.json) 1,000 builder tokens", text)

    def test_report_measures_its_own_cost_only_from_a_named_transcript(self):
        """F2 (review 20260919-213145)."""
        import tempfile
        os.environ.pop("GSTACK_TRANSCRIPT", None)
        with tempfile.TemporaryDirectory() as t:
            out, _ = measure.cmd_report(t)
            self.assertIn("no transcript named", Path(out).read_text())

    def test_p3_and_p4(self):
        runs = [run("1.0.0") for _ in range(10)]
        self.assertEqual(measure.score(runs)[2]["P3"][0], "supported")
        runs[0]["repeat_findings_vocab"] = runs[1]["repeat_findings_vocab"] = 1
        self.assertEqual(measure.score(runs)[2]["P3"][0], "refuted")
        self.assertEqual(measure.score(runs)[2]["P4"][0], "insufficient data")
        passing = [run("1.0.0", thin=i < 5, traced=i < 5) for i in range(20)]
        self.assertEqual(measure.score(passing)[2]["P4"][0], "supported")


class ReviewerUsage(unittest.TestCase):
    def test_each_cli_or_not_reported(self):
        g = json.dumps({"response": "{}", "stats": {"models": {"x": {"tokens": {"prompt": 10, "candidates": 5, "thoughts": 1, "cached": 3, "total": 16}}}}})
        self.assertEqual(pr.reviewer_usage("gemini", g, "")["total"], 16)
        c = json.dumps({"modelUsage": {"m": {"inputTokens": 2, "outputTokens": 3, "cacheReadInputTokens": 4, "cacheCreationInputTokens": 1}}})
        self.assertEqual(pr.reviewer_usage("claude", c, "")["total"], 10)
        self.assertEqual(pr.reviewer_usage("codex", "", "tokens used\n1,234")["total"], 1234)
        self.assertEqual(pr.reviewer_usage("gemini", "plain text", ""), "not_reported")


if __name__ == "__main__":
    unittest.main()
