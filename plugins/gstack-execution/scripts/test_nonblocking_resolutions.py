#!/usr/bin/env python3
"""XE-021 acceptance: a reviewer that also resolves a non-blocking prior finding does not void a
clean round. STIGViewer PL-004 round 2 is the case: F1 blocking and fixed, F2 separate and disproved,
reply resolved both, and validate threw the clean verdict away."""
import json, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr

PACKET = {"acceptance_criteria": ["f(1) == 2"]}
PRIOR = {"findings": [
    {"id": "F1", "severity": "blocking", "file": "a.py", "line": 2, "what": "x", "evidence": "y", "criterion": "z", "fix": "w"},
    {"id": "F2", "severity": "separate", "file": "b.py", "line": 0, "what": "x", "evidence": "y", "criterion": "z", "fix": "w"}]}
DISP = {"F1": "fixed", "F2": {"disposition": "disproved", "evidence": "b.py:3"}}


def reply(*ids):
    return json.dumps({"verdict": "no_blocking_findings",
                       "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
                       "findings": [],
                       "blocker_resolutions": [{"id": i, "resolved": True, "evidence": "a.py:2"} for i in ids]})


class NonBlockingResolutionTests(unittest.TestCase):
    def test_resolving_a_separate_finding_too_still_passes_and_is_dropped(self):
        out = pr.validate(reply("F1", "F2"), PACKET, PRIOR, DISP)
        self.assertEqual([r["id"] for r in out["blocker_resolutions"]], ["F1"])

    def test_an_id_that_was_never_a_finding_is_still_malformed(self):
        with self.assertRaises(pr.ReviewError) as caught:
            pr.validate(reply("F1", "F9"), PACKET, PRIOR, DISP)
        self.assertEqual(caught.exception.outcome, "malformed_output")

    def test_a_prior_blocker_still_needs_its_entry(self):
        with self.assertRaises(pr.ReviewError) as caught:
            pr.validate(reply("F2"), PACKET, PRIOR, DISP)
        self.assertEqual(caught.exception.outcome, "malformed_output")

    def test_a_duplicate_blocker_entry_is_still_malformed(self):
        with self.assertRaises(pr.ReviewError):
            pr.validate(reply("F1", "F1"), PACKET, PRIOR, DISP)

    def test_a_duplicate_non_blocking_entry_is_still_malformed(self):
        """Review 20260924-205619 F1: the skip must not hide a duplicate."""
        with self.assertRaises(pr.ReviewError) as caught:
            pr.validate(reply("F1", "F2", "F2"), PACKET, PRIOR, DISP)
        self.assertEqual(caught.exception.outcome, "malformed_output")


if __name__ == "__main__":
    unittest.main()
