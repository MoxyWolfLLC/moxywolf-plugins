#!/usr/bin/env python3
"""Results close the loop. Report shapes were taken from @mcpjam/sdk 10.0.0
(eval-local-run) and mcpevals 0.1.10 (EvaluationReport.to_dict). These tests
pin the parsing traps (MCPJam's duplicate case lists, mcp-eval's count-only
tool metric), the failure patterns, and the apply gates."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fixtures as F  # noqa: E402
from _fixtures import dl  # noqa: E402
import results  # noqa: E402


def it(n, verdict, tools, failed=()):
    return {"iterationNumber": n, "status": "completed", "taskVerdict": verdict,
            "toolCalls": [{"toolName": t, "arguments": {}} for t in tools], "policyBlocks": [],
            "scores": [{"scorerId": s, "status": "done", "passed": False} for s in failed]}


def mcpjam_report(cases):
    return {"schemaVersion": 1, "kind": "eval-local-run", "passed": False, "verdict": "failed",
            "cases": [{"id": c["caseId"], "title": c["title"], "passed": c["verdict"] == "passed"} for c in cases],
            "metadata": {"schemaVersion": 1, "cases": cases}}


def mj_case(qid, verdict, iterations, judge=None):
    return {"caseId": qid.lower(), "title": f"{qid} text", "judge": judge or {"configured": False, "run": False}, "verdict": verdict, "iterations": iterations}


def me_result(qid, passed, seq, failed=()):
    evs = [{"name": "ToolSequence", "passed": True, "result": {"passed": True, "details": {"sequence": seq}}}]
    evs += [{"name": n, "passed": False, "result": {"passed": False}} for n in failed]
    return {"case_name": qid, "passed": passed, "metrics": {"tool_calls": len(seq)}, "evaluation_results": evs}


class Parse(unittest.TestCase):
    def test_probe_retains_assertion_strength_and_flags_legacy(self):
        r={'results':[{'bank_id':'Q-0005','passed':True,'layers':[{'checks':[],'assertion_strength':'liveness'},{'checks':[]}]}]}
        self.assertEqual(results.collect_probe(r)[0]['probe_strengths'],['liveness','unknown_legacy'])

    def test_mcpjam_reads_iterations_once(self):
        rep = mcpjam_report([mj_case("Q-0001", "passed", [it(1, "passed", ["widgets_search"]), it(2, "passed", ["widgets_search"])])])
        recs, notes = results.collect_any(rep, "mcpjam")
        self.assertEqual(len(recs), 2, "two iterations, not two plus the duplicate top-level case")
        self.assertEqual(recs[0]["tools"], ["widgets_search"])

    def test_mcpjam_notes_unrun_judge_and_missing_verdicts(self):
        bad = dict(it(2, None, []), status="failed", refusal="rateLimited")
        rep = mcpjam_report([mj_case("Q-0004", "failed", [it(1, "failed", [], ["judge"]), bad],
                                     judge={"configured": True, "run": False, "skipReason": "localJudgeUnsupported"})])
        recs, notes = results.collect_any(rep, "mcpjam")
        self.assertEqual(len(recs), 1)
        self.assertTrue(any("judge" in n for n in notes))
        self.assertTrue(any("rateLimited" in n for n in notes))

    def test_mcpeval_reads_sequence_from_recorder(self):
        recs, notes = results.collect_any({"results": [me_result("Q-0001", True, ["widgets_get", "widgets_search"])]}, "mcp-eval")
        self.assertEqual(recs[0]["tools"], ["widgets_get", "widgets_search"])
        self.assertEqual(recs[0]["tool_count"], 2)
        self.assertEqual(notes, [])

    def test_mcpeval_count_without_sequence_is_flagged_not_guessed(self):
        r = {"case_name": "Q-0001", "passed": False, "metrics": {"tool_calls": 3}, "evaluation_results": [{"name": "X", "passed": False, "result": {}}]}
        recs, notes = results.collect_any({"results": [r]}, "mcp-eval")
        self.assertEqual(recs[0]["tools"], [])
        self.assertEqual(recs[0]["tool_count"], 3)
        self.assertTrue(any("ToolSequence" in n for n in notes))


class Ingest(unittest.TestCase):
    def setUp(self):
        self.w = F.Workspace()
        mj = mcpjam_report([
            mj_case("Q-0001", "passed", [it(i, "passed", ["widgets_search"]) for i in (1, 2, 3)]),
            mj_case("Q-0002", "failed", [it(1, "failed", ["widgets_get"], ["firstToolWas"])]),
        ])
        me = {"results": [
            me_result("Q-0004", False, ["widgets_search"], ["NotContains"]),
            me_result("Q-0009", False, [], ["FirstToolIn"]),
        ]}
        pr = {"results": [{"bank_id": "Q-0005", "passed": False, "layers": [{"layer": "mcp_payload", "checks": [{"check": "contains 'roles'", "passed": False}], "passed": False}]}]}
        self.paths = [F.write_json(mj, self.w.path("mj.json")), F.write_json(me, self.w.path("me.json")), F.write_json(pr, self.w.path("pr.json"))]
        rc, out, err = F.run("results.py", "ingest", "--bank", self.w.bank, "--mcpjam", self.paths[0], "--mcpeval", self.paths[1],
                             "--probe", self.paths[2], "--out", self.w.path("runs", "gap-report.md"), "--min-runs", "3")
        self.assertEqual(rc, 0, err)
        with open(self.w.path("runs", "gap-report.md"), encoding="utf-8") as fh:
            self.report = fh.read()
        self.props = dl.load_json(self.w.path("runs", "proposals.json"))

    def tearDown(self):
        self.w.close()

    def test_patterns(self):
        for qid, pat in [("Q-0002", "wrong-tool"), ("Q-0004", "boundary-broken"), ("Q-0005", "payload-wrong"), ("Q-0009", "no-tool-used")]:
            line = next((ln for ln in self.report.splitlines() if qid in ln and pat in ln), None)
            self.assertIsNotNone(line, f"{qid} should be {pat}")

    def test_stable_discovery_pass_is_proposed_for_promotion(self):
        p = [x for x in self.props["proposals"] if x["bank_id"] == "Q-0001"]
        self.assertEqual(p[0]["action"], "promote-to-strict")
        self.assertEqual(p[0]["set"]["expect.first_tool_any_of"], ["widgets_search"])
        self.assertEqual(self.props["bank_hash"], dl.sha256_file(self.w.bank))

    def test_ingest_changes_nothing(self):
        self.assertEqual(self.w.load_bank(), F.bank())

    def test_apply_gates(self):
        args = ["results.py", "apply", "--bank", self.w.bank, "--proposals", self.w.path("runs", "proposals.json")]
        rc, _, _ = F.run(*args, "--approver", "claude", "--ids", "Q-0001")
        self.assertEqual(rc, 2)
        rc, _, _ = F.run(*args, "--approver", "Dorian Cougias")
        self.assertNotEqual(rc, 0, "no apply-all")
        rc, out, err = F.run(*args, "--approver", "Dorian Cougias", "--ids", "Q-0001")
        self.assertEqual(rc, 0, err)
        q1 = {x["id"]: x for x in self.w.load_bank()["questions"]}["Q-0001"]
        self.assertEqual(q1["mode"], "strict")
        self.assertTrue(q1["why"])
        self.assertEqual(q1["history"][-1]["approved_by"], "Dorian Cougias")
        self.assertEqual(dl.validate_bank(self.w.load_bank(), ["widgets_search", "widgets_get", "widgets_plan"]).errors, [])
        rc, _, err = F.run(*args, "--approver", "Dorian Cougias", "--ids", "Q-0001")
        self.assertEqual(rc, 2, "proposals written against an older bank are refused")
        self.assertIn("re-run ingest", err)


if __name__ == "__main__":
    unittest.main(verbosity=1)
