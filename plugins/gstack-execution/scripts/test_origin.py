#!/usr/bin/env python3
"""TB-001: a record says where its content came from, or it is not written.

These are checks on the write path, not on the model. They prove that an unlabelled record
cannot be saved, that external text cannot be saved without naming what read it, and that
`verify` reports the origins it examined rather than assuming them.
"""
import json
import tempfile
import unittest
from pathlib import Path

import peer_review as pr


class Origin(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_vocabulary_defines_the_origins_and_carries_the_bump(self):
        self.assertEqual(pr.VOCAB_VERSION, "1.3.0")
        self.assertEqual(pr.ORIGINS,
                         {"repository_artifact", "gate_output", "human_instruction", "external_text", "unexamined"})

    def test_a_writer_that_omits_origin_cannot_write(self):
        # positional and no default: forgetting it is a TypeError at the call, not a quiet default
        with self.assertRaises(TypeError):
            pr.save(self.d, "x.json", {"a": 1})
        self.assertFalse((self.d / "x.json").exists())

    def test_an_origin_outside_the_vocabulary_is_refused(self):
        with self.assertRaises(pr.ReviewError) as e:
            pr.save(self.d, "x.json", {"a": 1}, "trusted")
        self.assertEqual(e.exception.outcome, "malformed_record")
        self.assertFalse((self.d / "x.json").exists())

    def test_external_text_needs_examined_by(self):
        with self.assertRaises(pr.ReviewError) as e:
            pr.save(self.d, "round-1.json", {"round": 1}, "external_text")
        self.assertEqual(e.exception.outcome, "malformed_record")
        self.assertFalse((self.d / "round-1.json").exists())
        pr.save(self.d, "round-1.json", {"round": 1}, "external_text", examined_by="unexamined")
        got = json.loads((self.d / "round-1.json").read_text())
        self.assertEqual((got["origin"], got["examined_by"]), ("external_text", "unexamined"))

    def test_a_written_record_carries_its_origin(self):
        pr.save(self.d, "state.json", {"review_id": "r"}, "gate_output")
        self.assertEqual(json.loads((self.d / "state.json").read_text())["origin"], "gate_output")

    def test_verify_reports_the_origins_it_examined(self):
        # a review directory with no repos to re-resolve still has records to account for
        pr.save(self.d, "packet.json", {"repos": [], "vocabulary_version": pr.VOCAB_VERSION}, "gate_output")
        pr.save(self.d, "state.json", {"review_id": self.d.name, "rounds_used": 0}, "gate_output")
        (self.d / "round-9.json").write_text(json.dumps({"round": 9}))   # written around save(): no origin
        out = pr.verify_links(self.d)
        self.assertEqual(out["records_by_origin"].get("gate_output"), 2)
        self.assertEqual(out["records_by_origin"].get("missing"), 1)
        self.assertEqual(out["outcome"], "examined_nothing", "no links were re-resolved, whatever the records say")
        self.assertEqual(out["records_examined"], 3)
        self.assertEqual(out["examined"], 0, "provenance checks must not satisfy the verifier's own EV-001 guard")
        named = [c for c in out["checks"] if not c["ok"] and "round-9.json" in c["link"]]
        self.assertTrue(named, "the unlabelled record is named in the checks, not just counted")


if __name__ == "__main__":
    unittest.main()
