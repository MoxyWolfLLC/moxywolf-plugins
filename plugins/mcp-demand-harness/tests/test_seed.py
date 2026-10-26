#!/usr/bin/env python3
"""Seeding is where evidence classes are assigned. The usage import is the
dangerous one: it handles customer words, and the harness's own test traffic
lands in the same logs. These tests pin redaction, the test-org exclusion,
demand counting, and the named-person release gate."""
import csv
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fixtures as F  # noqa: E402
from _fixtures import dl  # noqa: E402
import seed  # noqa: E402

INVENTORY_MD = """# Inventory

## A. Planning
**1. "Which widgets cover my scan?"** · **LIVE**
**2. "Am I compliant?"** · **BOUNDARY**

## B. Engineering
**3. "Export everything as OSCAL"** · **NO-TOOL**
"""


class Redact(unittest.TestCase):
    def test_catches_contact_details(self):
        for raw, tag in [("mail jo@ex.com", "[EMAIL]"), ("host 10.1.2.3", "[IP]"), ("call +1 (702) 555-0142", "[NUMBER]"),
                         ("box db01.corp.example.mil", "[HOST]"), ("key sk_live_abcdefgh1234", "[SECRET]")]:
            text, hits = seed.redact(raw)
            self.assertIn(tag, text, raw)

    def test_leaves_compliance_identifiers_alone(self):
        for raw in ["map 800-53 800-171", "since 2026-10-25", "CCI-000366 and V-257777", "SV-257777r1155676_rule", "AC.L1-3.1.1"]:
            self.assertEqual(seed.redact(raw), (raw, []), raw)


class Inventory(unittest.TestCase):
    def test_parse_sections_and_gates(self):
        items = seed.parse_inventory(INVENTORY_MD)
        self.assertEqual([(i["num"], i["section"]) for i in items], [("1", "A"), ("2", "A"), ("3", "B")])
        self.assertEqual([seed._kind_from_gate(i["gate"]) for i in items], ["live", "boundary", "gap"])


class Evidence(unittest.TestCase):
    def setUp(self):
        self.w = F.Workspace()
        rows = [
            {"id": "1", "mcp_intent": "Which widgets cover RHEL? email jo@ex.com", "created_at": "2026-10-01T00:00Z", "org_name": "Acme"},
            {"id": "2", "mcp_intent": "eval run: what widgets do you hold for RHEL", "created_at": "2026-10-02", "org_name": "Widgets Test Org"},
            {"id": "3", "mcp_intent": "What widgets do you hold for RHEL?", "created_at": "2026-10-03", "org_name": "Beta"},
            {"id": "4", "mcp_intent": "", "created_at": "2026-10-03", "org_name": "Beta"},
        ]
        self.csv = self.w.path("rows.csv")
        with open(self.csv, "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)

    def tearDown(self):
        self.w.close()

    def _import(self):
        return F.run("seed.py", "--profile", self.w.profile, "evidence", "--bank", self.w.bank, "--file", self.csv,
                     "--source-name", "api_access_logs", "--class", "observed", "--text-col", "mcp_intent",
                     "--date-col", "created_at", "--org-col", "org_name", "--id-col", "id")

    def test_import_redacts_excludes_and_counts(self):
        rc, out, err = self._import()
        self.assertEqual(rc, 0, err)
        self.assertIn("excluded_org=1", out, "test-org traffic must never count as demand")
        self.assertIn("empty=1", out)
        b = self.w.load_bank()
        obs = [x for x in b["questions"] if x["evidence"]["class"] == "observed"]
        self.assertEqual(len(obs), 1)
        self.assertIn("[EMAIL]", obs[0]["text"])
        self.assertNotIn("jo@ex.com", obs[0]["text"])
        self.assertIsNone(obs[0]["evidence"]["release_approved_by"])
        q1 = {x["id"]: x for x in b["questions"]}["Q-0001"]
        self.assertEqual(q1["demand"]["observed"], 1, "a near-duplicate increments demand instead of adding a question")

    def test_unreleased_observed_blocks_export_until_named_release(self):
        self._import()
        out = self.w.path("mj")
        rc, _, err = F.run("export_mcpjam.py", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--profile", self.w.profile, "--out", out)
        self.assertNotEqual(rc, 0)
        self.assertIn("release_approved_by", err)
        obs_id = [x["id"] for x in self.w.load_bank()["questions"] if x["evidence"]["class"] == "observed"][0]
        rc, _, err = F.run("seed.py", "--profile", self.w.profile, "approve-release", "--bank", self.w.bank, "--approver", "claude", "--ids", obs_id)
        self.assertEqual(rc, 2)
        rc, _, err = F.run("seed.py", "--profile", self.w.profile, "approve-release", "--bank", self.w.bank, "--approver", "Dorian Cougias")
        self.assertNotEqual(rc, 0, "no approve-all")
        rc, out_, err = F.run("seed.py", "--profile", self.w.profile, "approve-release", "--bank", self.w.bank, "--approver", "Dorian Cougias", "--ids", obs_id)
        self.assertEqual(rc, 0, err)
        rc, _, err = F.run("export_mcpjam.py", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--profile", self.w.profile, "--out", out)
        self.assertEqual(rc, 0, err)

    def test_reported_or_observed_only(self):
        rc, _, err = F.run("seed.py", "--profile", self.w.profile, "evidence", "--bank", self.w.bank, "--file", self.csv,
                           "--source-name", "x", "--class", "generated", "--text-col", "mcp_intent")
        self.assertEqual(rc, 2)


class Golden(unittest.TestCase):
    def test_semantics_mirror_the_upstream_harness(self):
        live = {"id": "LIVE-01", "kind": "live", "question": "Which rules implement X?", "expectTool": "widgets_search",
                "alsoAcceptable": ["widgets_get"], "call": {"tool": "widgets_search", "args": {"q": "X"}},
                "expect": {"mustContain": ["terminals"], "absenceAcceptable": True}, "why": "Marquee."}
        q = seed.golden_to_question(live, "Q-0100", "planner", "golden.ts")
        self.assertEqual(q["expect"]["first_tool_any_of"], ["widgets_search", "widgets_get"])
        self.assertNotIn("must_contain", q["expect"], "payload needles never become answer needles")
        self.assertEqual(q["payload"]["must_contain"], ["terminals"])
        bnd = {"id": "BND-01", "kind": "boundary", "question": "Am I compliant?", "expectTool": "widgets_search",
               "expect": {"mustNotContain": [{"$regex": "you are compliant", "flags": "i"}], "mustRefuse": True}, "why": "No verdicts."}
        q = seed.golden_to_question(bnd, "Q-0101", "planner", "golden.ts")
        self.assertNotIn("first_tool_any_of", q["expect"])
        self.assertTrue(q["expect"]["must_refuse"])
        self.assertTrue(q["expect"]["rubric"])
        self.assertEqual(q["surfaces"], ["mcp"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
