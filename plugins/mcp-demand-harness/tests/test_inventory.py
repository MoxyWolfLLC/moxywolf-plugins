#!/usr/bin/env python3
"""The capability map is what every expectation is checked against. If it
misses a tool, valid questions get rejected; if it misreads an endpoint, the
REST-only list (what an API buyer can do that an MCP user cannot) is wrong."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fixtures as F  # noqa: E402
from _fixtures import dl  # noqa: E402


class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = F.Workspace()
        cls.m = dl.load_json(cls.w.cmap)

    @classmethod
    def tearDownClass(cls):
        cls.w.close()

    def test_tools_found_by_every_register_pattern(self):
        self.assertEqual(self.m["mcp"]["tool_names"], ["widgets_search", "widgets_get", "widgets_plan"])

    def test_endpoint_methods_and_const_templates(self):
        t = {x["name"]: x for x in self.m["mcp"]["tools"]}
        self.assertEqual(t["widgets_search"]["endpoints"], [{"method": "GET", "path": "/api/v1/search"}])
        self.assertEqual(t["widgets_get"]["endpoints"], [{"method": "GET", "path": "/api/v1/items/${args.id}"}])
        self.assertEqual(t["widgets_plan"]["endpoints"], [{"method": "POST", "path": "/api/v1/plan"}])
        self.assertTrue(t["widgets_search"]["read_only"])
        self.assertEqual(t["widgets_plan"]["input_keys"], ["findings", "output"])

    def test_routes_methods_and_rest_only(self):
        r = {x["path"]: x for x in self.m["rest"]["routes"]}
        self.assertEqual(r["/api/v1/batch"]["methods"], ["POST"], "export const POST = ... is a handler too")
        self.assertEqual(r["/api/v1/items/{id}"]["reached_by_tools"], ["widgets_get"])
        self.assertEqual(sorted(self.m["rest"]["rest_only_routes"]), ["/api/v1/batch", "/api/v1/items/{id}/download"])
        self.assertEqual(self.m["rest"]["tool_endpoints_without_route"], [])

    def test_prompts_and_provenance(self):
        self.assertEqual([p["name"] for p in self.m["mcp"]["prompts"]], ["triage"])
        self.assertEqual(self.m["source"]["commit"], "abc1234")
        self.assertTrue(self.m["generated_by"].startswith(dl.PLUGIN_NAME))

    def test_inventory_does_not_touch_the_repo(self):
        before = sorted(os.path.relpath(os.path.join(d, f), self.w.repo) for d, _, fs in os.walk(self.w.repo) for f in fs)
        rc, _, err = F.run("inventory.py", "--repo", self.w.repo, "--profile", self.w.profile, "--out", self.w.path("m2.json"), "--commit", "x")
        self.assertEqual(rc, 0, err)
        after = sorted(os.path.relpath(os.path.join(d, f), self.w.repo) for d, _, fs in os.walk(self.w.repo) for f in fs)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=1)
