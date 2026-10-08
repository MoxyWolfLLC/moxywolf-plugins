"""CS-004.9: Sales and Marketing are department packages the Chief of Staff can route to.

Structure only. These checks prove the two packages exist, agree with the marketplace, don't
shadow the installed `sales:` and `marketing:` skills, are routed, and point at files that are
there. They can't prove an agent holds the Release Owner Gate when someone asks it to send
something. That evidence is the recorded scenario evaluation under docs/evidence/ (CS-004.9),
and a text check here must never be read as it.

ponytail: stdlib, regex and json. The marketplace is read, never rewritten. Skills that live in
other marketplaces (`sales:`, `marketing:`) are not examined here, and each test says so.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MARKET = ROOT / ".claude-plugin/marketplace.json"
COS = ROOT / "plugins/chief-of-staff"
MANUAL = COS / "skills/chief-of-staff/SKILL.md"
DISPATCHER = COS / "skills/cos/SKILL.md"
# package -> (local head skill, the external namespace it must not shadow, CS-004.4's candidates)
DEPARTMENTS = {
    "sales-department": ("head-of-sales", "sales", [
        "sales:account-research", "sales:call-prep", "sales:draft-outreach", "sales:pipeline-review", "sales:forecast"]),
    "marketing-department": ("head-of-marketing", "marketing", [
        "marketing:campaign-plan", "marketing:content-creation", "marketing:brand-review", "marketing:seo-audit",
        "marketing:performance-report"]),
}
# CS-004.6: the four fields every department returns, then the five these two add
RETURN_FIELDS = ["answer", "skills loaded", "sources cited", "open questions", "criterion-by-criterion",
                 "assumptions and uncertainty", "verification performed or missing", "proposed next action",
                 "pending approvals"]
LOCAL_REF = re.compile(r"\b(sales-department|marketing-department):([a-z][a-z0-9-]*)")
FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def read(p):
    return p.read_text() if p.is_file() else ""


def front(p, key):
    m = FRONT.match(read(p))
    hit = re.search(rf"(?m)^{key}:\s*(.+)$", m.group(1)) if m else None
    return hit.group(1).strip().strip('"') if hit else None


def entries():
    return {p["name"]: p for p in json.loads(MARKET.read_text())["plugins"]}


def section(text, heading):
    """The body under a markdown heading, up to the next heading of the same or a higher level."""
    m = re.search(rf"(?m)^(#+) {re.escape(heading)}\s*$", text)
    if not m:
        return ""
    rest = text[m.end():]
    end = re.search(rf"(?m)^#{{1,{len(m.group(1))}}} ", rest)
    return rest[:end.start()] if end else rest


class Packages(unittest.TestCase):
    def test_each_package_carries_every_required_file(self):
        examined = 0
        for pkg, (head, _, _) in DEPARTMENTS.items():
            base = ROOT / "plugins" / pkg
            for rel in (".claude-plugin/plugin.json", "README.md", "GOVERNANCE.md", f"agents/{pkg}.md",
                        f"skills/{head}/SKILL.md", f"skills/{head}/references/sources.md"):
                examined += 1
                self.assertTrue(read(base / rel).strip(), f"{pkg}/{rel} is missing or empty")
            self.assertIn("## Version History", read(base / "README.md"), f"{pkg} README has no Version History")
            self.assertIn("department agent", (front(base / f"agents/{pkg}.md", "description") or "").lower(),
                          f"{pkg}'s agent description doesn't say it is a department agent, so the roster check can't see it")
        print(f"examined {examined} required files across {len(DEPARTMENTS)} packages")
        self.assertEqual(examined, 12)

    def test_manifest_marketplace_and_readme_agree(self):
        market = entries()
        names = [*DEPARTMENTS, "chief-of-staff"]
        for name in names:
            base = ROOT / "plugins" / name
            manifest = json.loads(read(base / ".claude-plugin/plugin.json") or "{}")
            self.assertEqual(manifest.get("name"), name, f"{name}: plugin.json names something else")
            self.assertIn(name, market, f"{name} isn't registered in the marketplace")
            self.assertEqual(market[name].get("source"), f"./plugins/{name}")
            self.assertEqual(market[name].get("version"), manifest.get("version"), f"{name}: marketplace and manifest versions differ")
            history = section(read(base / "README.md"), "Version History")
            first = next((line for line in history.splitlines() if line.startswith("- ")), "")
            self.assertTrue(manifest.get("version") and first.startswith(f"- {manifest['version']} "),
                            f"{name}: README's newest Version History entry isn't {manifest.get('version')}: {first!r}")
        self.assertIn("CS-004", section(read(COS / "README.md"), "Version History"),
                      "the Chief of Staff changed for CS-004 and its Version History doesn't say so")
        print(f"examined {len(names)} packages against {len(market)} marketplace entries: manifest, entry and README versions")

    def test_no_package_shadows_the_installed_namespaces(self):
        market = entries()
        examined = 0
        for pkg, (head, external, candidates) in DEPARTMENTS.items():
            base = ROOT / "plugins" / pkg
            self.assertNotIn(external, market, f"a marketplace plugin named {external!r} would shadow the installed {external}: skills")
            self.assertFalse((ROOT / "plugins" / external).exists(), f"plugins/{external} would shadow the installed {external}: skills")
            self.assertEqual(front(base / f"agents/{pkg}.md", "name"), pkg)
            self.assertEqual(front(base / f"skills/{head}/SKILL.md", "name"), head)
            local = {p.parent.name for p in base.glob("skills/*/SKILL.md")}
            self.assertTrue(local, f"{pkg} has no skills; the glob examined nothing")
            borrowed = {c.split(":", 1)[1] for c in candidates}
            self.assertEqual(sorted(local & borrowed), [], f"{pkg} carries a local copy of an installed specialist skill")
            examined += len(local)
        print(f"examined {examined} local skills in {len(DEPARTMENTS)} packages; the installed sales: and marketing: "
              "catalogs are another marketplace's and are not examined")


class Routing(unittest.TestCase):
    def test_the_chief_of_staff_routes_ten(self):
        manual, dispatcher, readme = read(MANUAL), read(DISPATCHER), read(COS / "README.md")
        roster = dict(line.split("|", 1) for line in section(manual, "Roster").split("```roster\n")[-1].split("```")[0].splitlines()
                      if "|" in line)
        roster = {k.strip(): v.strip() for k, v in roster.items()}
        self.assertEqual(len(roster), 10, f"the roster routes {len(roster)} agents, not ten: {sorted(roster)}")
        for pkg in DEPARTMENTS:
            self.assertTrue(roster.get(pkg), f"{pkg} has no roster line or no remit")
            self.assertIn(pkg, readme, f"the Chief of Staff README doesn't name {pkg}")
        for name, text in (("manual", manual), ("dispatcher", dispatcher), ("README", readme)):
            self.assertIsNone(re.search(r"\beight\b", text.lower()), f"the {name} still says eight")
        left_out = section(manual, "What the ten don't cover")
        self.assertTrue(left_out.strip(), "the manual has no section for what the ten don't cover")
        for gone in ("- Sales", "- Marketing"):
            self.assertNotIn(gone, left_out, "Sales and Marketing are departments now, not routes outside the roster")
        lines = section(manual, "Where the lines fall")
        for owner in (*DEPARTMENTS, "customer-experience", "finance", "corporate-strategy", "legal", "/gstack-build"):
            self.assertIn(owner, lines, f"the manual doesn't say where the line with {owner} falls")
        description = (front(DISPATCHER, "description") or "").lower()
        self.assertTrue("sales" in description and "marketing" in description, "/cos's description doesn't offer sales or marketing")
        print(f"examined a roster of {len(roster)}, the manual's two boundary sections, the dispatcher and the README")

    def test_local_skill_and_source_references_resolve(self):
        files = [*COS.rglob("*.md")] + [p for pkg in DEPARTMENTS for p in (ROOT / "plugins" / pkg).rglob("*.md")]
        refs = {(m.group(1), m.group(2)) for p in files for m in LOCAL_REF.finditer(read(p))}
        self.assertTrue(refs, "no local sales-department: or marketing-department: reference found; examined nothing")
        for pkg, skill in sorted(refs):
            self.assertTrue((ROOT / "plugins" / pkg / "skills" / skill / "SKILL.md").is_file(), f"{pkg}:{skill} resolves to no SKILL.md")
        for pkg, (head, _, candidates) in DEPARTMENTS.items():
            base = ROOT / "plugins" / pkg
            agent, skill = read(base / f"agents/{pkg}.md"), read(base / f"skills/{head}/SKILL.md")
            first = re.search(r"`([a-z-]+:[a-z0-9-]+)`", agent.split("---", 2)[-1])
            self.assertEqual(first and first.group(1), f"{pkg}:{head}", f"{pkg}'s agent doesn't load its head skill first")
            self.assertIn("references/sources.md", skill, f"{head} doesn't point at its sources")
            sources = read(base / f"skills/{head}/references/sources.md")
            self.assertTrue(re.search(r"(?m)^## ", sources), f"{head}'s sources.md lists no source")
            self.assertTrue(re.search(r"[Rr]etrieved \d{4}-\d{2}-\d{2}", sources), f"{head}'s sources.md records no retrieval date")
            for c in candidates:
                self.assertIn(f"`{c}`", skill, f"{head} doesn't name the specialist {c}")
        print(f"examined {len(refs)} distinct local references in {len(files)} files, and 2 head skills' sources and specialists; "
              "whether a sales: or marketing: skill is installed is resolved at run time and not examined here")

    def test_the_expanded_return_contract_and_the_gate_are_written_down(self):
        """Presence, not behavior: whether an agent follows these is the scenario evaluation's question."""
        manual = read(MANUAL).lower()
        for pkg, (head, _, _) in DEPARTMENTS.items():
            base = ROOT / "plugins" / pkg
            skill, governance = read(base / f"skills/{head}/SKILL.md"), read(base / "GOVERNANCE.md")
            for field in RETURN_FIELDS:
                self.assertIn(field, skill.lower(), f"{head} doesn't promise: {field}")
            for must in ("Dorian Cougias", "Release Owner Gate", "not technical enforcement"):
                self.assertIn(must, skill, f"{head} doesn't state: {must}")
            self.assertIn("Dorian Cougias", governance, f"{pkg}'s GOVERNANCE.md names no Release Owner")
            for row in (f"`{pkg}`", f"`{head}`"):
                self.assertTrue(re.search(rf"(?m)^\|[^|]*{re.escape(row)}[^|]*\|\s*(read-only|generate|side-effectful-gated|high-stakes)\s*\|", governance),
                                f"{pkg}'s GOVERNANCE.md gives {row} no risk tier")
        for field in RETURN_FIELDS[4:]:
            self.assertIn(field, manual, f"the manual doesn't check the two departments' results for: {field}")
        print(f"examined {len(RETURN_FIELDS)} return fields and the gate's wording in 2 head skills, 2 GOVERNANCE.md files and the manual")

    def test_the_disagreement_rules_are_written_down(self):
        """CS-004.8 as amended 2026-10-07. Presence, not behavior: scenarios S7, S11 and S12 are the behavior."""
        manual, dispatcher = read(MANUAL), read(DISPATCHER)
        review = section(manual, "Nobody reviews their own work")
        self.assertRegex(review, r"involves sales-department or finance doesn't wait for security",
                         "the manual doesn't say which disagreements go ahead without security")
        self.assertIn("by what it contains", review, "the manual doesn't say a result is judged by what it contains")
        self.assertIn("stays blocked", review, "the manual doesn't keep the sensitive action blocked while a review is out")
        memo = section(manual, "The decision memo")
        for must in ("**For the bookkeeper.**", "context card", "never contact", "open question stays", "identifies the customer"):
            self.assertIn(must, memo, f"the decision memo's rules don't say: {must}")
        self.assertIn("bookkeeper", dispatcher, "/cos doesn't carry a finance disagreement to the bookkeeper's section")
        self.assertRegex(dispatcher, r"involves sales-department or finance", "/cos doesn't name the disagreements that skip the wait")
        # ponytail: the bookkeeper's name lives only on the context card, so no check here can spell it.
        # That it's absent from this repository is checked by hand at review, not by this test.
        print("examined the manual's review and memo sections and the dispatcher")


if __name__ == "__main__":
    unittest.main()
