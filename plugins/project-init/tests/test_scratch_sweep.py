"""SS-001: session end measures the loop's scratch before sweeping it, and never touches evidence.

ponytail: a text check over the command and the skill; the step is instructions, so text is what there is to test.
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
COMMAND = REPO / "plugins/project-init/commands/session-end.md"
SKILL = REPO / "plugins/project-init/skills/session-end/SKILL.md"
PROTECTED = ["GSTACK_PEER_REVIEW_DIR", "tests/container/results/", "any repository clone", "the Cowork VM bundle"]


def one_line(text):
    return " ".join(text.split())


class ScratchSweep(unittest.TestCase):
    def test_command_carries_8b_between_8a_and_9(self):
        starts = [l.split(" ", 1)[0] for l in COMMAND.read_text().splitlines() if l[:3] in {"8a.", "8b.", "9. "}]
        self.assertEqual(starts, ["8a.", "8b.", "9."])
        text = one_line(COMMAND.read_text())
        for s in ["SS-001", "Count before characterizing", "Scratch: not measured (<reason>)", *PROTECTED]:
            self.assertIn(s, text)

    def test_skill_step_7c_measures_before_it_removes(self):
        text = one_line(SKILL.read_text())
        start = text.index("### Step 7c: Sweep the loop's scratch (SS-001)")
        self.assertLess(text.index("### Step 7b:"), start)
        self.assertLess(start, text.index("### Step 8: Report what was written"))
        step = text[start:text.index("### Step 8: Report what was written")]
        self.assertLess(step.index("**Measure**"), step.index("**Ask, then remove.**"))
        for s in ["Desktop Commander, not `device_bash`", "docker system df", "vm_bundles", "In a cloud session, remove nothing", "never swept by default", "git worktree prune", "run-record.json", *PROTECTED]:
            with self.subTest(s=s):
                self.assertIn(s, step)

    def test_report_has_the_scratch_line(self):
        report = SKILL.read_text().split("### Step 8: Report what was written", 1)[1]
        self.assertIn("Scratch: [freed <n> GB (<what>); left <m> GB (<what>, why) | not measured (<reason>)]", report)


if __name__ == "__main__":
    unittest.main()
