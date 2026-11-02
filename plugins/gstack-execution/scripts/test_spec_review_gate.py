#!/usr/bin/env python3
"""SR-001.6/7: `peer_review.py open` refuses an item packet without a current, clean spec review,
through the real dispatcher in a subprocess. The reviewer and the API are never reached."""
import json
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spec_review as sr  # noqa: E402
import test_governed_review as _tgr  # noqa: E402

DESIGN = """# Fixture

## Goal

Change the value.

## Constraints and settled decisions

- The value is a word.

### FX-001 — The value changes

**Status:** planned.

1. value is after
"""


class Gate(unittest.TestCase):
    setUp, git, call = _tgr.GovernedReview.setUp, _tgr.GovernedReview.git, _tgr.GovernedReview.call

    def opened(self, items):
        self.packet["items"] = items
        self.packet["model_selection"] = {"status": "checked", "mode": "shadow"}
        self.packet_file.write_text(json.dumps(self.packet))
        return self.call("open", "--builder", "claude", "--packet", str(self.packet_file))

    def refused(self, items, code):
        r = self.opened(items)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn(code, r.stderr + r.stdout)
        self.assertNotIn(f"{code}: {code}", r.stderr + r.stdout)
        return r

    def test_design_item_missing_then_open_then_stale_then_contradiction(self):
        (self.repo / ".git" / "info" / "exclude").write_text("DESIGN.md\nreviews/\ngoals/\n")
        self.refused(["FX-001"], "spec_review_missing")                  # no DESIGN.md anywhere
        doc = self.repo / "DESIGN.md"; doc.write_text(DESIGN)
        self.refused(["FX-001"], "spec_review_missing")                  # the doc, no record
        self.refused(["FX-404"], "spec_review_missing")                  # an item the doc lacks
        sr.seed_clean(doc, ["FX-001"])
        r = self.opened(["FX-001"]); self.assertEqual(r.returncode, 0, r.stderr)
        doc.write_text(DESIGN.replace("**Status:** planned.", "**Status:** building."))
        r = self.opened(["FX-001"]); self.assertEqual(r.returncode, 0, "a status move made the record stale: " + r.stderr)
        doc.write_text(DESIGN.replace("value is after", "value is after, in capitals"))
        self.refused(["FX-001"], "spec_review_stale")
        conflict = {"contradictions": [{"id": "C1", "requirements": ["FX-001.1", "Constraints"],
                                        "scenario": "capitals", "smallest_change": "drop it"}], "ambiguities": []}
        sr.cmd_run(doc, ["FX-001"], post=sr.stub_post(conflict))
        self.refused(["FX-001"], "spec_review_open")

    def test_a_mirror_repo_without_the_doc_is_not_a_refusal_and_a_goal_item_reads_its_plan(self):
        (self.repo / ".git" / "info" / "exclude").write_text("DESIGN.md\nreviews/\ngoals/\n")
        doc = self.repo / "DESIGN.md"; doc.write_text(DESIGN); sr.seed_clean(doc, ["FX-001"])
        mirror = Path(self.tmp.name, "mirror"); shutil.copytree(self.repo, mirror)
        (mirror / "DESIGN.md").unlink(); shutil.rmtree(mirror / "reviews")
        self.packet["repos"].append({**self.packet["repos"][0], "path": str(mirror)})
        r = self.opened(["FX-001"]); self.assertEqual(r.returncode, 0, r.stderr)
        self.packet["repos"].pop()
        self.refused(["g1/1"], "spec_review_missing")                    # no goals/g1/PLAN.md
        plan = self.repo / "goals" / "g1" / "PLAN.md"; plan.parent.mkdir(parents=True); plan.write_text("1. one\n")
        sr.seed_clean(plan)
        r = self.opened(["g1/1"]); self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_table_row_item_opens_and_a_batch_needs_every_item(self):
        (self.repo / ".git" / "info" / "exclude").write_text("DESIGN.md\nreviews/\n")
        doc = self.repo / "DESIGN.md"
        doc.write_text(DESIGN.split("### FX-001")[0] + "## Items\n\n| ID | Item | Acceptance criteria | Status |\n|---|---|---|---|\n"
                       "| FX-001 | The value changes | 1. value is after | planned |\n| FX-002 | Other | 1. nothing | planned |\n")
        sr.seed_clean(doc, ["FX-001"])
        r = self.opened(["FX-001"]); self.assertEqual(r.returncode, 0, r.stderr)
        self.refused(["FX-001", "FX-002"], "spec_review_missing")      # FX-002 has no record of its own
        sr.seed_clean(doc, ["FX-002"])
        r = self.opened(["FX-002", "FX-001"]); self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
