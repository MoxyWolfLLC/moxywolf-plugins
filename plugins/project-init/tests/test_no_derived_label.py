"""SM-002: a project's Jira label is declared, never derived from its slug.

MOXY carries both `moxywolf-plugins` and `project-moxywolf-crm`, so a rule mapping
`#project/<slug>` to `project-<slug>` is right for one project and wrong for the other. A label
that matches nothing reads as an empty backlog, not as a wrong query. The rule had five homes in
this repo; this test keeps all five clean. plugin.json changelogs are exempt: they record what was.

ponytail: a grep over a fixed list. The list is the point; a file that moves fails the test by
being missing rather than passing by being unread (EV-001).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOMES = [
    "plugins/project-init/skills/session-start/SKILL.md",
    "plugins/project-init/commands/session-start.md",
    "plugins/project-init/skills/project-init/SKILL.md",
    "plugins/project-init/commands/init-project.md",
    "plugins/team-kanban/skills/team-kanban/references/jira-board-mapping.md",
]
# The derivation as it was written: project-<slug>, project-[slug], or "maps to the label project-".
DERIVED = re.compile(r"project-<slug>|project-\[slug\]|maps to the (?:Jira )?label `?project-")


class NoDerivedLabel(unittest.TestCase):
    def test_every_home_exists_and_is_examined(self):
        missing = [h for h in HOMES if not (ROOT / h).is_file()]
        self.assertEqual(missing, [], "a home moved; update HOMES rather than skip it")
        self.assertEqual(len(HOMES), 5)

    def test_no_home_derives_a_label_from_a_slug(self):
        hits = []
        for h in HOMES:
            for n, line in enumerate((ROOT / h).read_text().splitlines(), 1):
                if DERIVED.search(line):
                    hits.append(f"{h}:{n}")
        print(f"examined {len(HOMES)} files, {len(hits)} derivations")
        self.assertEqual(hits, [])

    def test_the_pattern_catches_the_old_rule(self):
        old = "a `#project/<slug>` value maps to the Jira label `project-<slug>`"
        self.assertTrue(DERIVED.search(old))


if __name__ == "__main__":
    unittest.main()
