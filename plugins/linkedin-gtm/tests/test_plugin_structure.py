#!/usr/bin/env python3
"""linkedin-gtm structure: tiers declared, commands present, no em dashes, every tool name real,
marketplace entry in step, and the config defaults answer the plan's open decisions safely."""
import json
import re
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parent.parent
sys.path.insert(0, str(PLUGIN / "scripts"))

SKILLS = {
    "linkedin-gtm": "generate",
    "li-health": "read-only",
    "li-signals": "read-only",
    "li-research-draft": "generate",
    "li-approval-batch": "side-effectful-gated",
    "li-execute": "high-stakes",
    "li-publish": "high-stakes",
    "li-blog-bridge": "generate",
    "li-inbox-triage": "generate",
    "li-digest": "read-only",
    "li-weekly": "read-only",
}
COMMANDS = ["li-day", "li-health", "li-signals", "li-draft", "li-batch", "li-execute", "li-publish", "li-blog",
            "li-triage", "li-digest", "li-weekly", "li-setup"]
REFERENCES = ["gtm-api-tool-map.md", "sequences.md", "budgets-and-guardrails.md", "voice-and-craft.md",
              "lanes.md", "approval-batch-format.md", "crm-sync-contract.md", "connection.md"]
TIERS = {"read-only", "generate", "bounded-write", "side-effectful-bounded", "side-effectful-gated", "high-stakes"}
NOT_TOOLS = {"reply_to_linkedin_message_sid", "send_outcome", "send_status"}


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip()
    return fm, text


def plugin_text_files():
    for p in PLUGIN.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".json", ".py") and "__pycache__" not in p.parts:
            yield p


class Skills(unittest.TestCase):
    def test_every_skill_declares_its_tier(self):
        found = {p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md")}
        self.assertEqual(found, set(SKILLS))
        for name, tier in SKILLS.items():
            fm, _ = frontmatter(PLUGIN / "skills" / name / "SKILL.md")
            self.assertIsNotNone(fm, name)
            self.assertEqual(fm.get("name"), name)
            self.assertIn(fm.get("risk_tier"), TIERS, name)
            self.assertEqual(fm.get("risk_tier"), tier, name)
            self.assertTrue(fm.get("description"), name)

    def test_high_stakes_skills_name_the_release_owner_and_the_execute_path(self):
        for name in ("li-execute", "li-publish"):
            text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("Dorian Cougias", text)
            self.assertIn("gtm_mcp.py\" execute", text)

    def test_governance_lists_every_skill(self):
        gov = (PLUGIN / "GOVERNANCE.md").read_text(encoding="utf-8")
        self.assertIn("named Release Owner is Dorian Cougias", gov)
        self.assertIn("record_decision.py", gov)
        for name in SKILLS:
            self.assertIn(f"skill `{name}`", gov)


class Commands(unittest.TestCase):
    def test_commands_exist_with_frontmatter(self):
        for c in COMMANDS:
            fm, _ = frontmatter(PLUGIN / "commands" / f"{c}.md")
            self.assertIsNotNone(fm, c)
            self.assertTrue(fm.get("description"), c)
            self.assertIn("allowed-tools", fm, c)

    def test_li_day_stops_at_the_gate(self):
        text = (PLUGIN / "commands" / "li-day.md").read_text(encoding="utf-8")
        self.assertIn("Do not execute anything", text)


class Content(unittest.TestCase):
    def test_references_exist(self):
        for r in REFERENCES:
            self.assertTrue((PLUGIN / "references" / r).is_file(), r)

    def test_no_em_dashes_anywhere(self):
        for p in plugin_text_files():
            self.assertNotIn("\u2014", p.read_text(encoding="utf-8"), str(p.relative_to(PLUGIN)))

    def test_no_selftest_entry_points(self):
        # CI runs any .py that contains the flag; this plugin's scripts have none.
        flag = "--" + "selftest"
        for p in (PLUGIN / "scripts").glob("*.py"):
            self.assertNotIn(flag, p.read_text(encoding="utf-8"), p.name)

    def test_every_tool_name_mentioned_is_in_the_policy(self):
        policy = json.loads((PLUGIN / "scripts" / "tool_policy.json").read_text(encoding="utf-8"))
        known = set(policy["read_tools"]) | set(policy["never"]) | \
            {k["tool"] for k in policy["gated_kinds"].values()} | {"list_toolsets", "call_tool"} | \
            set(policy["gated_kinds"])  # batch kinds such as mark_unread
        pat = re.compile(r"`((?:get|search|scrape|enrich|check|create|send|update|delete|preview|react|repost|"
                         r"accept|ignore|withdraw|mark|visit|endorse)_[a-z_]+)`")
        for p in list((PLUGIN / "references").glob("*.md")) + list((PLUGIN / "skills").rglob("*.md")) + \
                list((PLUGIN / "commands").glob("*.md")) + [PLUGIN / "README.md", PLUGIN / "GOVERNANCE.md"]:
            for name in pat.findall(p.read_text(encoding="utf-8")):
                if name in NOT_TOOLS:
                    continue
                self.assertIn(name, known, f"{name} in {p.relative_to(PLUGIN)}")

    def test_policy_lists_are_disjoint(self):
        policy = json.loads((PLUGIN / "scripts" / "tool_policy.json").read_text(encoding="utf-8"))
        gated = {k["tool"] for k in policy["gated_kinds"].values()}
        self.assertFalse(set(policy["read_tools"]) & gated)
        self.assertFalse(set(policy["read_tools"]) & set(policy["never"]))
        self.assertFalse(gated & set(policy["never"]))
        self.assertIn("create_mass_action", policy["never"])


class Config(unittest.TestCase):
    def test_example_config_defaults(self):
        cfg = json.loads((PLUGIN / "config" / "linkedin-gtm.example.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["release_owner"], "Dorian Cougias")
        self.assertEqual(cfg["lanes"]["A"]["mode"], "engagement-only")
        self.assertEqual(cfg["approval_time"], "10:15")
        self.assertEqual(cfg["timezone"], "America/Los_Angeles")
        self.assertEqual(cfg["meetings"], "hand-to-dorian")
        self.assertEqual(cfg["crm_target"], "moxywolf-crm")
        self.assertEqual(cfg["crm_extra_targets"], [])
        self.assertTrue(cfg["account_sid"].startswith("ln_ac_"))


class Manifest(unittest.TestCase):
    def test_plugin_json_and_marketplace_agree(self):
        pj = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(pj["name"], "linkedin-gtm")
        mp_path = REPO / ".claude-plugin" / "marketplace.json"
        if not mp_path.exists():
            self.skipTest("not inside the marketplace repo")
        mp = json.loads(mp_path.read_text(encoding="utf-8"))
        entry = [p for p in mp["plugins"] if p["name"] == "linkedin-gtm"]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["version"], pj["version"])
        self.assertEqual(entry[0]["source"], "./plugins/linkedin-gtm")

    def test_readme_has_no_version_line(self):
        self.assertNotRegex((PLUGIN / "README.md").read_text(encoding="utf-8"), r"\*\*Version:\*\*")


if __name__ == "__main__":
    unittest.main()
