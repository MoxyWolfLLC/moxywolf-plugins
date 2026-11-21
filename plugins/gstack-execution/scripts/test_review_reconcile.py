import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_reconcile as rr  # noqa: E402

H1, H2 = "a" * 64, "b" * 64


def f(fid, lane, clause, cls, evidence, fix="change it"):
    return {"finding_id": fid, "lane": lane, "claim": "c", "cited_clause": clause, "class": cls,
            "evidence": evidence, "smallest_fix": fix}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def lane(self, name, rows):
        d = self.root / "run" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "findings.json").write_text(json.dumps(rows))

    def file(self, name, obj):
        p = self.root / name
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj))
        return str(p)

    def run_dir(self):
        return str(self.root / "run")


class Dedupe(Base):
    def test_same_clause_and_class_merge_keeping_lanes(self):
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", [H1])])
        self.lane("b", [f("B1", "claude", "x.py:1", "behavior_gap", [H2])])
        d = rr.dedupe(self.run_dir())
        self.assertEqual(len(d["merged"]), 1)
        self.assertEqual(d["merged"][0]["lanes"], ["claude", "codex"])
        self.assertEqual(d["merged"][0]["evidence"], sorted([H1, H2]))
        self.assertEqual(d["split_by_class"], [])

    def test_same_clause_different_class_stays_split_and_listed(self):
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", []),
                        f("A2", "codex", "x.py:1", "wording_defect", [])])
        d = rr.dedupe(self.run_dir())
        self.assertEqual(len(d["merged"]), 2)
        self.assertEqual(d["split_by_class"], ["x.py:1"])

    def test_unknown_class_refused_and_named(self):
        self.lane("a", [f("A1", "codex", "x.py:1", "nitpick", [])])
        with self.assertRaises(rr.Refused) as c:
            rr.dedupe(self.run_dir())
        self.assertIn("nitpick", str(c.exception))
        self.assertIn("A1", str(c.exception))

    def test_missing_field_and_bad_json_refused(self):
        self.lane("a", [{"finding_id": "A1"}])
        with self.assertRaises(rr.Refused):
            rr.dedupe(self.run_dir())
        d = self.root / "run" / "b"
        d.mkdir(parents=True)
        (d / "findings.json").write_text("{not json")
        with self.assertRaises(rr.Refused):
            rr.read_findings(self.run_dir())


class Score(Base):
    def key(self, entries):
        return self.file("key.json", entries)

    def entry(self, kid, cls, req):
        return {"key_id": kid, "class": cls, "condition": "words", "evidence_required": req}

    def score(self, key):
        return rr.score(self.run_dir(), key, self.file("manifest.json", "{}"))

    def test_clause_and_class_alone_do_not_match(self):
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", [])])
        r = self.score(self.key([self.entry("K1", "behavior_gap", [H1])]))
        self.assertEqual(r["counts"], {"matches": 0, "repeats": 0, "misses": 1, "false_blockers": 1})

    def test_all_required_evidence_matches_and_one_missing_does_not(self):
        key = self.key([self.entry("K1", "behavior_gap", [H1, "x.py:1"])])
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", [H1, "x.py:1"])])
        self.assertEqual(self.score(key)["counts"]["matches"], 1)
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", [H1])])
        self.assertEqual(self.score(key)["counts"]["matches"], 0)

    def test_second_equivalent_finding_is_a_repeat(self):
        key = self.key([self.entry("K1", "behavior_gap", [H1])])
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", [H1]),
                        f("A2", "codex", "y.py:2", "behavior_gap", [H1])])
        self.assertEqual(self.score(key)["counts"], {"matches": 1, "repeats": 1, "misses": 0, "false_blockers": 0})

    def test_unmatched_blocker_is_false_blocker_unmatched_entry_is_miss(self):
        key = self.key([self.entry("K1", "behavior_gap", [H1]), self.entry("K2", "false_premise", [H2])])
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", [H1]),
                        f("A2", "codex", "z.py:3", "false_premise", ["nope"]),
                        f("A3", "codex", "w.py:4", "wording_defect", ["nope"]),
                        f("A4", "codex", "v.py:5", "behavior_gap", ["nope"], fix="")])
        r = self.score(key)
        self.assertEqual(r["counts"], {"matches": 1, "repeats": 0, "misses": 1, "false_blockers": 1})
        self.assertEqual(r["false_blockers"], ["A2"])
        self.assertEqual(r["misses"], ["K2"])

    def test_same_inputs_same_bytes_and_hashes_recorded(self):
        key = self.key([self.entry("K1", "behavior_gap", [H1])])
        self.lane("a", [f("A1", "codex", "x.py:1", "behavior_gap", [H1])])
        man = self.file("manifest.json", "{}")
        a = rr.dump(rr.score(self.run_dir(), key, man))
        b = rr.dump(rr.score(self.run_dir(), key, man))
        self.assertEqual(a, b)
        r = json.loads(a)
        self.assertEqual(r["key_sha256"], rr.sha(key))
        self.assertEqual(r["manifest_sha256"], rr.sha(man))


def report(width, seconds, misses=0, blockers=0, dorian=0, manifest="m", budget=1, deadline=5400, decision="ok"):
    return {"counts": {"matches": 3, "repeats": 0, "misses": misses, "false_blockers": blockers},
            "manifest_sha256": manifest,
            "meta": {"width": width, "budget": budget, "deadline_seconds": deadline, "decision": decision,
                     "decisions_to_dorian": dorian, "draft_to_decision_seconds": seconds}}


class Compare(unittest.TestCase):
    def test_faster_with_no_new_misses_passes(self):
        ok, _ = rr.compare(report(3, 600), report(5, 400))
        self.assertTrue(ok)

    def test_each_regression_fails_and_names_its_clause(self):
        for kw, word in (({"misses": 1}, "misses"), ({"blockers": 1}, "false_blockers"),
                         ({"dorian": 1}, "Dorian"), ({"decision": "other"}, "decision")):
            ok, clause = rr.compare(report(3, 600), report(5, 400, **kw))
            self.assertFalse(ok, kw)
            self.assertIn(word, clause)

    def test_not_faster_fails(self):
        ok, clause = rr.compare(report(3, 600), report(5, 600))
        self.assertFalse(ok)
        self.assertIn("draft-to-decision", clause)

    def test_order_of_arguments_does_not_matter(self):
        self.assertTrue(rr.compare(report(5, 400), report(3, 600))[0])

    def test_different_manifest_or_limits_or_equal_width_refused(self):
        for other in (report(5, 400, manifest="n"), report(5, 400, budget=2), report(5, 400, deadline=1),
                      report(3, 400)):
            with self.assertRaises(rr.Refused):
                rr.compare(report(3, 600), other)

    def test_cli_exit_codes_and_output(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t, "a.json"), Path(t, "b.json")
            a.write_text(json.dumps(report(3, 600)))
            b.write_text(json.dumps(report(5, 400)))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(rr.main(["compare", str(a), str(b)]), 0)
            self.assertEqual(json.loads(out.getvalue())["result"], "pass")
            b.write_text(json.dumps(report(5, 400, misses=1)))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rr.main(["compare", str(a), str(b)]), 2)
            b.write_text(json.dumps(report(5, 400, manifest="n")))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rr.main(["compare", str(a), str(b)]), 1)


class Council(unittest.TestCase):
    def test_closed_gate_leaves_finding_open_in_packet_and_asks_nothing(self):
        asked, packet = [], []
        r = rr.council_dispute({"finding_id": "A1"}, lambda: False, asked.append, packet)
        self.assertEqual((r, asked), ("open", []))
        self.assertEqual(packet[0]["finding_id"], "A1")
        self.assertEqual(packet[0]["disposition"], "open")

    def test_ask_is_called_only_after_the_ledger_accepts(self):
        order = []
        r = rr.council_dispute({"finding_id": "A1"}, lambda: order.append("accept") or True,
                               lambda fnd: order.append("ask"), [])
        self.assertEqual((r, order), ("asked", ["accept", "ask"]))


if __name__ == "__main__":
    unittest.main()
