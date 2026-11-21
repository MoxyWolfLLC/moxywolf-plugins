#!/usr/bin/env python3
"""SR-003.6/7/9: a disproved contradiction can be recorded beside its record, and `check` honours it
only while it names the record file as it is now. Stub transports only; no network, no ledger.

Interface assumed (frozen by DESIGN.md SR-003; the implementation must provide it):
  spec_review.dispose(doc, cid, by, evidence, items=None, constraints=False, disposition="disproved")
      appends one entry to reviews/spec-review/<scope>.dispositions.json beside the doc, under
      review_run.locked() with an atomic replace; raises spec_review.Refused, writing nothing, on any
      refusal in SR-003.6. With items=[one id] the scope is that item; with neither, the whole file.
  spec_review.py dispose <doc> [--items <id> | --constraints] --id <cid> --by <name> --evidence "<text>"
      main(["dispose", ...]) returns 0 on success and 1 on a refusal.
  Each entry: {"id", "record_sha256", "disposition": "disproved", "by", "evidence", "recorded_at"},
  record_sha256 being the sha256 of the record file's bytes. The file holds a JSON list of entries
  (an object with a "dispositions" list is read the same way here).
  Every record cmd_run writes carries a fresh "review_id".
"""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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
"""

BY = "Dorian C"
EVIDENCE = 'Dorian: "C1 is disproved, the queue view sha256 is the same at both commits"'


def contradiction(cid, req="FX-001.1"):
    return {"id": cid, "requirements": [req, "Constraints"], "scenario": f"scenario {cid}",
            "smallest_change": "drop it"}


def entries(path):
    data = json.loads(Path(path).read_text())
    return data if isinstance(data, list) else data.get("dispositions") or []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Disposition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.doc = Path(self.tmp.name) / "DESIGN.md"
        self.doc.write_text(DESIGN)
        self.rec = sr.record_path(self.doc, "FX-001")
        self.disp = self.rec.parent / "FX-001.dispositions.json"
        # an operator's environment must never be reached
        env = mock.patch.dict(os.environ, {"GSTACK_SPEND_LEDGER": str(Path(self.tmp.name) / "no-ledger.json")})
        env.start(); self.addCleanup(env.stop)
        os.environ.pop("GSTACK_ANTHROPIC_ENV", None)

    def run_review(self, contradictions, items=("FX-001",), doc=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return sr.cmd_run(doc or self.doc, list(items) if items else None,
                              post=sr.stub_post({"contradictions": contradictions, "ambiguities": []}))

    def main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sr.main(list(args))
        return code, out.getvalue() + err.getvalue()

    def dispose_cli(self, cid="C1", by=BY, evidence=EVIDENCE, items="FX-001"):
        args = ["dispose", str(self.doc)] + (["--items", items] if items else []) + ["--id", cid, "--by", by, "--evidence", evidence]
        return self.main(*args)

    def assertWritesNothing(self, fn, before_disp=None):
        rec_before = self.rec.read_bytes() if self.rec.exists() else None
        result = fn()
        self.assertEqual(self.rec.read_bytes() if self.rec.exists() else None, rec_before, "the record was edited")
        if before_disp is None:
            self.assertFalse(self.disp.exists(), "a refused dispose wrote a dispositions file")
        else:
            self.assertEqual(self.disp.read_bytes(), before_disp, "a refused dispose changed the dispositions file")
        return result

    # --- the record is never edited; check honours a current disposition and names it ---

    def test_records_carry_a_review_id(self):
        self.run_review([contradiction("C1")])
        self.assertTrue(json.loads(self.rec.read_text()).get("review_id"), "the record has no review_id")

    def test_dispose_leaves_the_record_sha256_unchanged(self):
        self.run_review([contradiction("C1")])
        before, md = sha(self.rec), self.rec.with_suffix(".md").read_bytes()
        code, out = self.dispose_cli()
        self.assertEqual(code, 0, out)
        self.assertEqual(sha(self.rec), before)
        self.assertEqual(self.rec.with_suffix(".md").read_bytes(), md)
        (e,) = entries(self.disp)
        self.assertEqual(set(e), {"id", "record_sha256", "disposition", "by", "evidence", "recorded_at"})
        self.assertEqual((e["id"], e["record_sha256"], e["disposition"], e["by"], e["evidence"]),
                         ("C1", before, "disproved", BY, EVIDENCE))

    def test_a_record_whose_only_contradiction_is_disposed_passes_and_check_names_it(self):
        self.run_review([contradiction("C1")])
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok); self.assertTrue(why.startswith("spec_review_open"), why)
        sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertTrue(ok, why)
        for s in ("C1", BY, EVIDENCE):
            self.assertIn(s, why)
        code, out = self.main("check", str(self.doc), "--items", "FX-001")
        self.assertEqual(code, 0, out)
        for s in ("C1", BY, EVIDENCE):
            self.assertIn(s, out)

    def test_one_disposed_of_two_still_fails_on_the_other(self):
        self.run_review([contradiction("C1"), contradiction("C2")])
        sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok); self.assertTrue(why.startswith("spec_review_open"), why); self.assertIn("C2", why)

    def test_a_hand_set_resolved_still_clears_nothing(self):
        self.run_review([contradiction("C1"), contradiction("C2")])
        rec = json.loads(self.rec.read_text())
        for c in rec["contradictions"]:
            c["resolved"] = True
        self.rec.write_text(json.dumps(rec))
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok); self.assertTrue(why.startswith("spec_review_open"), why)
        sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])   # bound to the hand-edited file
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok, "resolved cleared C2"); self.assertIn("C2", why)

    # --- a disposition lapses: scope edit, re-run ---

    def test_a_scope_edit_makes_the_record_stale_despite_a_disposition(self):
        self.run_review([contradiction("C1")])
        sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
        self.assertTrue(sr.check(self.doc, ["FX-001"])[0])
        self.doc.write_text(DESIGN.replace("value is after", "value is after, in capitals"))
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok); self.assertTrue(why.startswith("spec_review_stale"), why)

    def test_a_rerun_with_identical_text_and_a_frozen_clock_writes_a_new_review_id_and_reopens(self):
        fixed = datetime(2026, 11, 21, 12, 0, 0, tzinfo=timezone.utc)

        class Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed if tz else fixed.replace(tzinfo=None)

        with mock.patch.object(sr, "datetime", Frozen):
            self.run_review([contradiction("C1")])
            first = json.loads(self.rec.read_text())
            sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
            self.assertTrue(sr.check(self.doc, ["FX-001"])[0])
            self.run_review([contradiction("C1")])
        second = json.loads(self.rec.read_text())
        self.assertEqual(first["reviewed_at"], second["reviewed_at"], "the clock was not frozen")
        self.assertTrue(first.get("review_id") and second.get("review_id"), "records lack review_id")
        self.assertNotEqual(first["review_id"], second["review_id"])
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok, "a disposition survived a re-run"); self.assertTrue(why.startswith("spec_review_open"), why)
        self.assertIn("C1", why)

    # --- dispose refuses, writing nothing ---

    def test_refuses_an_unknown_id(self):
        self.run_review([contradiction("C1")])
        code, out = self.assertWritesNothing(lambda: self.dispose_cli(cid="C9"))
        self.assertEqual(code, 1, out)
        with self.assertRaises(sr.Refused):
            sr.dispose(self.doc, "C9", BY, EVIDENCE, items=["FX-001"])
        self.assertFalse(self.disp.exists())

    def test_refuses_an_id_appearing_twice(self):
        self.run_review([contradiction("C1"), contradiction("C1", "FX-001.2")])
        code, out = self.assertWritesNothing(lambda: self.dispose_cli())
        self.assertEqual(code, 1, out)

    def test_refuses_a_missing_record(self):
        code, out = self.assertWritesNothing(lambda: self.dispose_cli())
        self.assertEqual(code, 1, out)
        with self.assertRaises(sr.Refused):
            sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
        self.assertFalse(self.disp.exists())

    def test_refuses_a_stale_record(self):
        self.run_review([contradiction("C1")])
        self.doc.write_text(DESIGN.replace("value is after", "value is before"))
        code, out = self.assertWritesNothing(lambda: self.dispose_cli())
        self.assertEqual(code, 1, out)

    def test_refuses_a_malformed_record(self):
        self.run_review([contradiction("C1")])
        rec = json.loads(self.rec.read_text()); del rec["ambiguities"]
        self.rec.write_text(json.dumps(rec))
        code, out = self.assertWritesNothing(lambda: self.dispose_cli())
        self.assertEqual(code, 1, out)
        self.rec.write_text("{not json")
        code, out = self.assertWritesNothing(lambda: self.dispose_cli())
        self.assertEqual(code, 1, out)

    def test_refuses_a_no_advisor_record(self):
        self.run_review([contradiction("C1")])
        rec = json.loads(self.rec.read_text()); rec["advisor_calls"] = 0
        self.rec.write_text(json.dumps(rec))
        code, out = self.assertWritesNothing(lambda: self.dispose_cli())
        self.assertEqual(code, 1, out)

    def test_refuses_empty_by_or_evidence(self):
        self.run_review([contradiction("C1")])
        for kw in ({"by": ""}, {"by": "   "}, {"evidence": ""}, {"evidence": "  "}):
            code, out = self.assertWritesNothing(lambda: self.dispose_cli(**kw))
            self.assertEqual(code, 1, f"{kw}: {out}")

    def test_refuses_a_disposition_other_than_disproved(self):
        self.run_review([contradiction("C1")])
        for value in ("accepted", "resolved", "", "Disproved"):
            rec_before = self.rec.read_bytes()
            with self.assertRaises(sr.Refused):
                sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"], disposition=value)
            self.assertEqual(self.rec.read_bytes(), rec_before)
            self.assertFalse(self.disp.exists(), f"{value!r} wrote a dispositions file")

    def test_a_refusal_leaves_an_existing_dispositions_file_unchanged(self):
        self.run_review([contradiction("C1"), contradiction("C2")])
        sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
        before = self.disp.read_bytes()
        code, out = self.assertWritesNothing(lambda: self.dispose_cli(cid="C9"), before_disp=before)
        self.assertEqual(code, 1, out)

    # --- a disposition never clears an earlier check ---

    def test_a_disposition_never_clears_spec_review_missing(self):
        self.run_review([contradiction("C1")])
        sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
        self.rec.unlink()
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok); self.assertTrue(why.startswith("spec_review_missing"), why)

    def test_a_disposition_never_clears_a_no_advisor_record(self):
        self.run_review([contradiction("C1")])
        rec = json.loads(self.rec.read_text()); rec["advisor_calls"] = 0
        self.rec.write_text(json.dumps(rec))
        # an entry bound to this exact file, written by hand since dispose refuses it
        self.disp.write_text(json.dumps([{"id": "C1", "record_sha256": sha(self.rec), "disposition": "disproved",
                                          "by": BY, "evidence": EVIDENCE, "recorded_at": "2026-11-21T12:00:00+00:00"}]))
        ok, why = sr.check(self.doc, ["FX-001"])
        self.assertFalse(ok); self.assertTrue(why.startswith("spec_review_missing"), why)
        self.assertIn("advisor", why)

    # --- concurrency and atomicity ---

    def test_two_concurrent_dispose_processes_both_land(self):
        self.run_review([contradiction("C1"), contradiction("C2")])
        env = {k: v for k, v in os.environ.items() if k != "GSTACK_ANTHROPIC_ENV"}
        procs = [subprocess.Popen([sys.executable, "-B", str(HERE / "spec_review.py"), "dispose", str(self.doc),
                                   "--items", "FX-001", "--id", cid, "--by", BY, "--evidence", EVIDENCE],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                 for cid in ("C1", "C2")]
        for p in procs:
            out, err = p.communicate(timeout=60)
            self.assertEqual(p.returncode, 0, out + err)
        self.assertEqual(sorted(e["id"] for e in entries(self.disp)), ["C1", "C2"])
        self.assertTrue(sr.check(self.doc, ["FX-001"])[0])

    def test_an_interrupted_write_leaves_the_previous_dispositions_file_intact(self):
        self.run_review([contradiction("C1"), contradiction("C2")])
        sr.dispose(self.doc, "C1", BY, EVIDENCE, items=["FX-001"])
        before = self.disp.read_bytes()

        def boom(*a, **k):
            raise OSError("simulated crash during the replace")

        with mock.patch("os.replace", boom), mock.patch("os.rename", boom):
            with self.assertRaises(Exception):
                sr.dispose(self.doc, "C2", BY, EVIDENCE, items=["FX-001"])
        self.assertEqual(self.disp.read_bytes(), before)
        self.assertEqual([e["id"] for e in entries(self.disp)], ["C1"])


if __name__ == "__main__":
    unittest.main()
