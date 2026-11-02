"""ME-001: session start reports the model economy and never gates on it.

ponytail: a text check over the command and the skill; the step is instructions, so text is what there is to test.
"""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
COMMAND = REPO / "plugins/project-init/commands/session-start.md"
SKILL = REPO / "plugins/project-init/skills/session-start/SKILL.md"
REMEDY = "run /model sonnet, then /advisor fable (first time: /model fable once to accept the usage-credits consent, then back to /model sonnet)"


def one_line(text):
    return " ".join(text.split())


class ModelEconomy(unittest.TestCase):
    def test_command_carries_8b_between_8_and_9(self):
        lines = COMMAND.read_text().splitlines()
        starts = [l.split(" ", 1)[0] for l in lines if l[:3] in {"8. ", "8b.", "9. "}]
        self.assertEqual(starts, ["8.", "8b.", "9."])
        text = one_line(COMMAND.read_text())
        for s in ["ME-001", "advisorModel", "Model economy: NOT SET (main=<x>, advisor=<y>)", REMEDY, "never gates and never edits the settings file"]:
            self.assertIn(s, text)

    def test_command_matches_the_patch_exactly(self):
        # The hunk of Dorian's patch, context and added lines in order, appears contiguously and byte for byte.
        patch = (REPO / "docs/evidence/ME-001-session-start.patch").read_text(encoding="utf-8").splitlines()
        hunk = [l[1:] for l in patch[patch.index("@@") + 1:]]
        lines = COMMAND.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any(lines[i:i + len(hunk)] == hunk for i in range(len(lines))), "patch hunk not found verbatim")

    def test_skill_carries_step_h(self):
        text = one_line(SKILL.read_text())
        self.assertIn("h. **Model economy (ME-001)**", text)
        self.assertLess(text.index("g. **Behavioural hook liveness**"), text.index("h. **Model economy (ME-001)**"))
        for s in ["~/.claude/settings.json", ".claude/settings.json", "the project's value wins", "Model economy: sonnet main + <advisor> advisor", "Model economy: NOT SET (main=<x>, advisor=<y>)", REMEDY, "DISABLE_TELEMETRY", "CLAUDE_CODE_DISABLE_ADVISOR_TOOL", "never gates the session and never edits a settings file", "`explore` and `docs` agents on Haiku"]:
            with self.subTest(s=s):
                self.assertIn(s, text)

    def test_briefing_has_the_shared_services_line(self):
        block = SKILL.read_text().split("**Shared services**", 1)[1].split("```", 1)[0]
        self.assertIn("- Model economy: [✓ sonnet main + [advisor] advisor | ⚠ NOT SET (main=[x], advisor=[y])", block)


if __name__ == "__main__":
    unittest.main()
