#!/usr/bin/env python3
"""Exports are what the harnesses actually run. These tests pin the contract
each format can and cannot express: exact versus approximated cases, the
regex translations that keep Python and JavaScript in agreement, drafts and
blocked questions staying out, and production configs needing a named person."""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fixtures as F  # noqa: E402
from _fixtures import dl  # noqa: E402
import export_mcpeval  # noqa: E402
import export_mcpjam  # noqa: E402


class McpjamMapping(unittest.TestCase):
    def setUp(self):
        self.suites, self.report = export_mcpjam.build(F.bank(), False, "sha256:x")
        self.cases = {c["id"]: c for s in self.suites.values() for c in s}
        self.rep = {r["bank_id"]: r for r in self.report}

    def test_every_case_carries_its_bank_id(self):
        for c in self.cases.values():
            self.assertTrue(c["title"].startswith(c["id"].upper()))
            self.assertEqual(c["import"]["sourceCaseKey"], f"questions[{c['id'].upper()}]")

    def test_single_tool_is_exact_with_rule_note(self):
        c = self.cases["q-0002"]
        self.assertEqual(c["import"]["status"], "exact")
        self.assertIn("M-1", c["import"]["note"])
        self.assertNotIn("disabled", c)

    def test_any_of_and_rubric_are_approximated_and_disabled(self):
        for cid in ("q-0003", "q-0004"):
            self.assertEqual(self.cases[cid]["import"]["status"], "approximated", cid)
            self.assertTrue(self.cases[cid]["disabled"], cid)
        self.assertIn("any-of", self.cases["q-0003"]["import"]["note"])

    def test_discovery_has_liveness_only(self):
        types = [a["type"] for a in self.cases["q-0001"]["assertions"]]
        self.assertEqual(types, ["finalAssistantMessageNonEmpty", "noToolErrors"])
        self.assertEqual(self.cases["q-0001"]["kind"], "capability")

    def test_drafts_blocked_and_rest_only_stay_out(self):
        self.assertNotIn("q-0007", self.cases)
        self.assertFalse(self.rep["Q-0007"]["emitted"])
        self.assertNotIn("q-0008", self.cases)
        self.assertIn("customer input", self.rep["Q-0008"]["reason"])
        self.assertNotIn("q-0006", self.cases, "REST-only questions belong to the probe")
        self.assertIn("q-0009", self.cases)
        suites, _ = export_mcpjam.build(F.bank(), True, "sha256:x")
        self.assertIn("q-0007", {c["id"] for s in suites.values() for c in s})

    def test_intent_fits_64(self):
        b = F.bank()
        b["personas"][0]["id"] = "p" * 70
        for x in b["questions"]:
            x["persona"] = "p" * 70
        suites, _ = export_mcpjam.build(b, False, "h")
        for s in suites.values():
            for c in s:
                self.assertLessEqual(len(c["intent"]), 64)


class RegexTranslation(unittest.TestCase):
    """The negative whole-response pattern must pass clean answers and fail
    offending ones, case-insensitively, without flags (MCPJam takes none)."""

    def check(self, pat, clean, dirty):
        neg = dl.negative_whole_response(dl.js_case_fold(pat))
        self.assertIsNotNone(re.search(neg, clean), clean)
        self.assertIsNone(re.search(neg, dirty), dirty)

    def test_verdict_pattern(self):
        self.check(r"\byou are compliant\b", "Coverage is 62%.\nThis is not a verdict.", "Good news:\nYOU ARE COMPLIANT with 800-171.")

    def test_escapes_survive_case_folding(self):
        folded = dl.js_case_fold(r"\d+\s*(hours|days)\S")
        self.assertIn(r"\d", folded)
        self.assertIn(r"\S", folded)
        self.check(r"\b\d+\s*(hours|days)\b", "Owner: sysadmin.", "About 40 Hours of work.")

    def test_character_class_gets_both_cases(self):
        self.check(r"[a-c]at", "dog", "BAT")


class McpevalMapping(unittest.TestCase):
    def test_case_insensitive_regex_uses_inline_flag(self):
        q = {x["id"]: x for x in F.bank()["questions"]}["Q-0004"]
        case, rules = export_mcpeval.map_question(q, "Planner", 0.8)
        nc = [e["NotContains"] for e in case["evaluators"] if "NotContains" in e][0]
        self.assertTrue(nc["text"].startswith("(?i)"))
        self.assertTrue(nc["case_sensitive"], "mcp-eval lowercases the pattern when case_sensitive is false, breaking \\S and \\D")
        self.assertIn("LLMJudge", json.dumps(case["evaluators"]))

    def test_every_case_records_tool_names(self):
        for x in F.bank()["questions"]:
            case, rules = export_mcpeval.map_question(x, "P", 0.8)
            names = [list(e)[0] for e in case["evaluators"]]
            self.assertTrue("FirstToolIn" in names or "ToolSequence" in names, x["id"])
            self.assertEqual(case["metadata"]["bank_id"], x["id"])


class Cli(unittest.TestCase):
    def setUp(self):
        self.w = F.Workspace()

    def tearDown(self):
        self.w.close()

    def test_both_exporters_write_their_files(self):
        rc, out, err = F.run("export_mcpjam.py", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--profile", self.w.profile, "--out", self.w.path("mj"))
        self.assertEqual(rc, 0, err)
        self.assertEqual(sorted(os.listdir(self.w.path("mj"))), ["widgets-discovery.yaml", "widgets-mapping-report.json", "widgets-strict.yaml"])
        with open(self.w.path("mj", "widgets-strict.yaml"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn('schemaVersion: "2"', text)
        self.assertIn("iterations:", text)
        self.assertNotIn("tags:", text)
        rc, out, err = F.run("export_mcpeval.py", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--profile", self.w.profile, "--out", self.w.path("me"))
        self.assertEqual(rc, 0, err)
        files = set(os.listdir(self.w.path("me")))
        for f in ("mcpeval.yaml", "mcpeval.secrets.yaml.example", ".gitignore", "widgets-strict.dataset.yaml", "widgets-discovery.dataset.yaml", "widgets-mcpeval-mapping.json"):
            self.assertIn(f, files)
        with open(self.w.path("me", ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("mcpeval.secrets.yaml", fh.read())

    def test_production_mcpeval_config_needs_named_approver(self):
        args = ["--bank", self.w.bank, "--capability-map", self.w.cmap, "--profile", self.w.profile, "--out", self.w.path("me"), "--target", "production"]
        rc, _, err = F.run("export_mcpeval.py", *args)
        self.assertEqual(rc, 2)
        rc, _, err = F.run("export_mcpeval.py", *args, "--approver", "Dorian Cougias")
        self.assertEqual(rc, 0, err)
        m = dl.load_json(self.w.path("me", "widgets-mcpeval-mapping.json"))
        self.assertEqual(m["approved_by"], "Dorian Cougias")
        self.assertTrue(m["requires_named_approval"])

    def test_invalid_bank_is_refused(self):
        b = self.w.load_bank()
        b["questions"][1]["expect"]["first_tool_any_of"] = ["widgets_nope"]
        self.w.save_bank(b)
        rc, _, err = F.run("export_mcpjam.py", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--profile", self.w.profile, "--out", self.w.path("mj"))
        self.assertNotEqual(rc, 0)
        self.assertFalse(os.path.exists(self.w.path("mj", "widgets-strict.yaml")))


if __name__ == "__main__":
    unittest.main(verbosity=1)
