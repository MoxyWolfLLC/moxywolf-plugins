#!/usr/bin/env python3
"""The bank validator is the only thing standing between a model-written
question and an export that looks like customer demand. These tests pin the
rules that keep that line: evidence lineage, the generated cap, discovery
naming no tools, strict needing a why, read-only REST, release and review gates."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fixtures as F  # noqa: E402
from _fixtures import dl, q  # noqa: E402

TOOLS = ["widgets_search", "widgets_get", "widgets_plan"]
ROUTES = ["/api/v1/search", "/api/v1/items/{id}", "/api/v1/items/{id}/download", "/api/v1/plan", "/api/v1/batch"]


def errors(b, **kw):
    rep = dl.validate_bank(b, TOOLS, routes=ROUTES, **kw)
    return [str(e) for e in rep.errors]


class Validate(unittest.TestCase):
    def test_payload_json_contract_is_validated_and_exportable(self):
        b=F.bank();q=next(q for q in b['questions'] if q.get('payload'))
        q['payload']['json_any_of']=[[{'path':'/roles','type':'array','nonempty':True}]]
        self.assertEqual(errors(b),[])
        import probe
        plan=probe.build_plan(b,{'mcp':{'tools':[]}})
        self.assertIn('json_any_of',next(i for i in plan['items'] if i['bank_id']==q['id'])['checks'])
        q['payload']['json_any_of']=[[]]
        self.assertTrue(any('json_any_of' in e for e in errors(b)))

    def test_fixture_bank_is_valid(self):
        self.assertEqual(errors(F.bank()), [])

    def test_generated_needs_existing_non_generated_parent(self):
        b = F.bank()
        b["questions"].append(q("Q-0010", evidence={"class": "generated", "note": "x"}))
        self.assertTrue(any("must name a parent" in e for e in errors(b)))
        b["questions"][-1]["evidence"]["parent"] = "Q-0099"
        self.assertTrue(any("does not exist" in e for e in errors(b)))
        b["questions"][-1]["evidence"]["parent"] = "Q-0009"
        self.assertTrue(any("is itself generated" in e for e in errors(b)))

    def test_generated_cap_per_persona(self):
        b = F.bank()
        b["questions"] = [x for x in b["questions"] if x["persona"] != "engineer"]
        b["questions"].append(q("Q-0020", persona="engineer"))
        for i in range(4):
            b["questions"].append(q(f"Q-003{i}", persona="engineer", text=f"gen {i}", evidence={"class": "generated", "parent": "Q-0020"}))
        self.assertTrue(any("exceeds the 3x cap" in e for e in errors(b)))
        b["questions"].pop()
        self.assertFalse(any("cap" in e for e in errors(b)))

    def test_discovery_names_no_tools(self):
        b = F.bank()
        b["questions"][0]["expect"] = {"first_tool_any_of": ["widgets_search"]}
        self.assertTrue(any("discovery questions do not name expected tools" in e for e in errors(b)))

    def test_strict_needs_why_and_an_expectation(self):
        b = F.bank()
        del b["questions"][1]["why"]
        self.assertTrue(any("(why)" in e for e in errors(b)))
        b = F.bank()
        b["questions"][1]["expect"] = {}
        self.assertTrue(any("at least one expectation" in e for e in errors(b)))

    def test_unknown_tool_rejected(self):
        b = F.bank()
        b["questions"][1]["expect"]["first_tool_any_of"] = ["widgets_delete"]
        self.assertTrue(any("does not register" in e for e in errors(b)))

    def test_must_refuse_needs_rubric(self):
        b = F.bank()
        del b["questions"][3]["expect"]["rubric"]
        self.assertTrue(any("must_refuse needs a rubric" in e for e in errors(b)))

    def test_rest_calls_are_read_only_routed_and_surfaced(self):
        b = F.bank()
        b["questions"][5]["rest"]["calls"] = [{"method": "DELETE", "path": "/api/v1/items/42"}]
        self.assertTrue(any("read-only" in e for e in errors(b)))
        b["questions"][5]["rest"]["calls"] = [{"method": "GET", "path": "/api/v1/nope"}]
        self.assertTrue(any("matches no route" in e for e in errors(b)))
        b["questions"][5]["rest"]["calls"] = [{"method": "GET", "path": "/api/v1/items/42/download", "headers": {}}]
        self.assertTrue(any("rest call keys" in e for e in errors(b)))
        b = F.bank()
        b["questions"][5]["surfaces"] = ["mcp"]
        self.assertTrue(any("must list rest in surfaces" in e for e in errors(b)))

    def test_route_templates_match_concrete_paths(self):
        m = dl._route_matcher(ROUTES)
        self.assertTrue(m("/api/v1/items/42"))
        self.assertTrue(m("/api/v1/items/42/download?x=1"))
        self.assertFalse(m("/api/v1/items"))
        self.assertFalse(m("/api/v1/items/42/other"))

    def test_draft_needs_author(self):
        b = F.bank()
        del b["questions"][6]["evidence"]["authored_by"]
        self.assertTrue(any("authored_by" in e for e in errors(b)))

    def test_observed_must_be_redacted_and_released_for_export(self):
        b = F.bank()
        b["questions"].append(q("Q-0011", evidence={"class": "observed", "source": "logs:1"}))
        self.assertTrue(any("redacted" in e for e in errors(b)))
        b["questions"][-1]["evidence"]["redacted"] = True
        self.assertEqual(errors(b), [], "unreleased observed is a warning outside export")
        self.assertTrue(any("release_approved_by" in e for e in errors(b, for_export=True)))

    def test_regex_that_differs_between_python_and_js_is_rejected(self):
        b = F.bank()
        b["questions"][3]["expect"]["must_not_match"] = [r"(?P<x>a)"]
        self.assertTrue(errors(b))

    def test_runnable_excludes_drafts_and_blocked(self):
        b = {x["id"]: x for x in F.bank()["questions"]}
        self.assertFalse(dl.runnable(b["Q-0007"])[0])
        self.assertTrue(dl.runnable(b["Q-0007"], include_drafts=True)[0])
        self.assertFalse(dl.runnable(b["Q-0008"])[0])
        self.assertTrue(dl.runnable(b["Q-0009"])[0])

    def test_named_person(self):
        for ok in ("Dorian Cougias", "Ana Maria Lopez"):
            self.assertTrue(dl.named_person(ok), ok)
        for bad in ("", None, "Dorian", "claude", "The Team", "Claude Agent", "owner user"):
            self.assertFalse(dl.named_person(bad), bad)


class Cli(unittest.TestCase):
    def setUp(self):
        self.w = F.Workspace()

    def tearDown(self):
        self.w.close()

    def test_add_is_all_or_nothing(self):
        before = self.w.load_bank()
        good = q("Q-0000", text="A new good one about widgets")
        bad = q("Q-0000", text="A bad strict one", mode="strict", expect={"first_tool_any_of": ["widgets_get"]})
        for x in (good, bad):
            del x["id"]
        path = F.write_json([good, bad], self.w.path("add.json"))
        rc, out, err = F.run("bank.py", "add", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--file", path)
        self.assertEqual(rc, 1)
        self.assertIn("REJECTED", out + err)
        self.assertEqual(self.w.load_bank(), before)
        path = F.write_json([good], self.w.path("add.json"))
        rc, out, err = F.run("bank.py", "add", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--file", path)
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.w.load_bank()["questions"]), len(before["questions"]) + 1)

    def test_accept_needs_named_person_and_ids(self):
        rc, _, err = F.run("bank.py", "accept", "--bank", self.w.bank, "--ids", "Q-0007", "--approver", "claude")
        self.assertEqual(rc, 2)
        rc, _, err = F.run("bank.py", "accept", "--bank", self.w.bank, "--approver", "Dorian Cougias")
        self.assertNotEqual(rc, 0, "accept without --ids must not accept everything")
        rc, out, err = F.run("bank.py", "accept", "--bank", self.w.bank, "--ids", "Q-0007", "--approver", "Dorian Cougias")
        self.assertEqual(rc, 0, err)
        qd = {x["id"]: x for x in self.w.load_bank()["questions"]}["Q-0007"]
        self.assertEqual(qd["review_status"], "accepted")
        self.assertEqual(qd["history"][-1]["approved_by"], "Dorian Cougias")

    def test_report_and_stats_run(self):
        rc, out, err = F.run("bank.py", "stats", "--bank", self.w.bank)
        self.assertEqual(rc, 0, err)
        self.assertIn('"drafts": 1', out)
        rc, out, err = F.run("bank.py", "report", "--bank", self.w.bank, "--capability-map", self.w.cmap, "--out", self.w.path("r.md"))
        self.assertEqual(rc, 0, err)
        with open(self.w.path("r.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("/api/v1/batch", text, "REST-only routes belong in the report")


if __name__ == "__main__":
    unittest.main(verbosity=1)
