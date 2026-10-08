"""CS-001.10: the Chief of Staff's roster names exactly the department agents that exist.

The roster in skills/chief-of-staff/SKILL.md and the agents under plugins/ are one fact with two
homes. A roster naming an agent that isn't there routes work into nothing; a department missing
from the roster is never called. Either drift fails here.

ponytail: a regex over one fenced block and a glob. A department agent is an agents/<name>.md in
plugins/<name>/ whose description says "department agent". The non-department routes (legal:,
product-orchestrator:, /gstack-build) are not examined here, and the test says so.

CS-004: Sales and Marketing are departments now (`sales-department`, `marketing-department`), so
they are examined like the other eight. The `sales:` and `marketing:` skills they borrow live in
other marketplaces and still aren't.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANUAL = ROOT / "plugins/chief-of-staff/skills/chief-of-staff/SKILL.md"
BLOCK = re.compile(r"```roster\n(.*?)```", re.S)


def roster(text):
    m = BLOCK.search(text)
    if not m:
        return []
    return [line.split("|")[0].strip() for line in m.group(1).splitlines() if line.strip()]


def departments(root):
    out = []
    for p in sorted(root.glob("plugins/*/agents/*.md")):
        if p.stem == p.parent.parent.name and "department agent" in p.read_text().lower():
            out.append(p.stem)
    return out


class Roster(unittest.TestCase):
    def test_roster_matches_department_agents(self):
        names = roster(MANUAL.read_text())
        found = departments(ROOT)
        print(f"examined roster of {len(names)} in {MANUAL.relative_to(ROOT)} against "
              f"{len(found)} department agents under plugins/; non-department routes not examined")
        self.assertTrue(names, "empty or missing roster block reads as no departments, not as fine")
        self.assertTrue(found, "no department agents found; the glob examined nothing")
        self.assertEqual(sorted(set(names) - set(found)), [], "roster names an agent that doesn't exist")
        self.assertEqual(sorted(set(found) - set(names)), [], "a department agent is missing from the roster")
        self.assertEqual(len(names), len(set(names)), "roster names an agent twice")

    def test_sales_and_marketing_are_departments(self):
        """CS-004.9: on the baseline both are missing from the roster and from plugins/, so the
        general check above passes over eight and says nothing. This one names them."""
        names, found = roster(MANUAL.read_text()), departments(ROOT)
        for dept in ("sales-department", "marketing-department"):
            self.assertIn(dept, found, f"no plugins/{dept}/agents/{dept}.md that says it is a department agent")
            self.assertIn(dept, names, f"{dept} is not in the roster")
        self.assertEqual(len(names), 10, f"the roster routes {len(names)} agents, not ten")

    def test_parser_catches_drift(self):
        self.assertEqual(roster("no block here"), [])
        self.assertEqual(roster("```roster\nghost | nothing\n```"), ["ghost"])
        self.assertNotIn("ghost", departments(ROOT))


if __name__ == "__main__":
    unittest.main()
