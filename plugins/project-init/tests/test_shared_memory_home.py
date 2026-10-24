"""SM-007: team rules live in GitHub/Projects/_shared-memory, and only a Taskade project mounts Taskade.

The rules moved out of `Taskade/_Shared Files/_shared-memory/` on 2026-10-24, so an org-shared or
vault-only session never needs the Taskade root. This test keeps every plugin home off the old path.
plugin.json and marketplace.json changelogs are exempt: they record what was.

ponytail: a grep over a fixed list plus project-init's commands folder. A file that moves fails the
test by being missing rather than passing by being unread (EV-001).
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXED = [
    "plugins/project-init/skills/session-start/SKILL.md",
    "plugins/project-init/skills/session-end/SKILL.md",
    "plugins/project-init/skills/project-init/SKILL.md",
    "plugins/gstack-execution/commands/gstack-build.md",
    "plugins/gstack-execution/skills/gstack-execution/SKILL.md",
    "plugins/obsidian-update/skills/personal-os/SKILL.md",
    "README.md",
]
OLD = "Taskade/_Shared Files/_shared-memory"
NEW = "GitHub/Projects/_shared-memory"


def homes():
    return FIXED + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "plugins/project-init/commands").glob("*.md"))


class SharedMemoryHome(unittest.TestCase):
    def test_every_home_exists_and_is_examined(self):
        missing = [h for h in FIXED if not (ROOT / h).is_file()]
        self.assertEqual(missing, [], "a home moved; update FIXED rather than skip it")
        self.assertGreater(len(homes()), len(FIXED), "project-init/commands examined nothing")

    def test_no_home_names_the_old_path(self):
        hits = []
        for h in homes():
            for n, line in enumerate((ROOT / h).read_text().splitlines(), 1):
                if OLD in line:
                    hits.append(f"{h}:{n}")
        print(f"examined {len(homes())} files, {len(hits)} old-path references")
        self.assertEqual(hits, [])

    def test_session_start_reads_the_new_home_and_skips_taskade(self):
        text = (ROOT / FIXED[0]).read_text()
        self.assertIn(f"{NEW}/INDEX.md", text)
        self.assertIn("not needed (org-shared or vault-only project)", text)

    def test_the_check_catches_the_old_path(self):
        self.assertIn(OLD, "Read `Taskade/_Shared Files/_shared-memory/INDEX.md` first.")


if __name__ == "__main__":
    unittest.main()
