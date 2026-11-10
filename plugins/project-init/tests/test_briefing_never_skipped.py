"""SM-011: session start never drops a briefing section, and reads don't wait on a mount.

On 2026-11-10 two sessions skipped Jira, decision records and open issues: one because a folder
prompt was refused, one because it timed out and a task was passed as the argument. The skill said
to skip sections that read from a missing root. This test keeps that permission out and the
reader order, the no-skip rule and the task-is-not-a-replacement rule in.

ponytail: text checks on two files. It proves the instructions say it, not that a session obeys.
"""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "session-start" / "SKILL.md"
COMMAND = PLUGIN / "commands" / "session-start.md"
# The SM-011 criterion 5 phrase, in the shapes the skill used before 0.46.0.
OLD = re.compile(r"skip(ped)?( any)? briefing sections? that reads? from|sections that read from it are skipped", re.I)
READERS = ["Desktop Commander", "The mounted root", "`MoxyWolfLLC/Projects`", "`project_read`", "Google Drive connector"]


def old_permission(text):
    return [m.group(0) for m in OLD.finditer(text)]


class BriefingNeverSkipped(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")
        self.command = COMMAND.read_text(encoding="utf-8")

    def test_the_skip_permission_is_gone(self):
        self.assertEqual(old_permission(self.skill), [])
        self.assertEqual(old_permission(self.command), [])

    def test_reader_order_is_stated_in_order(self):
        start = self.skill.index("**Step C — Reader order (SM-011).**")
        positions = [self.skill.index(r, start) for r in READERS]
        self.assertEqual(positions, sorted(positions), "readers out of order")

    def test_no_section_is_skipped_and_unavailable_names_sources(self):
        self.assertIn("No section is skipped to save time or to stay on a task (SM-011).", self.skill)
        self.assertIn("`unavailable: <reason>`, naming the sources tried", self.skill)
        self.assertIn("never depend on a mount", self.skill)

    def test_a_task_argument_does_not_replace_the_briefing(self):
        self.assertIn("doesn't replace the briefing (SM-011)", self.skill)
        self.assertIn("a task never replaces the briefing (SM-011)", self.command)

    def test_git_runs_on_the_mac_not_the_vm(self):
        # 0.46.1: device_bash is a Linux VM with no GitHub login; every skill that runs git says so.
        self.assertIn("**Don't run git in `device_bash`.**", self.skill)
        for name in ("session-end", "project-init"):
            text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("`device_bash` is a Linux VM with no GitHub login", text, name)

    def test_the_check_catches_the_old_wording(self):
        for old in ("skip briefing sections that read from the missing root",
                    "Skip any briefing section that reads from the missing root",
                    "the sections that read from it are skipped with a one-line note"):
            self.assertTrue(old_permission(old), old)


if __name__ == "__main__":
    unittest.main()
