"""SM-010: startup reads the standing operating rule from its one home and says when it could not.

ponytail: a text check over the two command files and the canonical file, plus one real run of the hook.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHECKS = REPO / "plugins/gstack-execution/skills/gstack-execution/references/verification-checks.md"
HOOK = REPO / "plugins/gstack-execution/hooks/verify-discipline.js"
COMMANDS = [REPO / "plugins/project-init/commands/init-project.md", REPO / "plugins/project-init/commands/session-start.md"]
HEADING = "Standing operating rule: verify before recommending commitment"
PATH = "gstack-execution/skills/gstack-execution/references/verification-checks.md"
# Sentences only the rule itself should carry; finding one elsewhere means the rule has a second home.
RULE_SENTENCES = ["partial verification is not readiness", "An apology is not the correction."]


def one_line(text):
    return " ".join(text.split())


class StandingRule(unittest.TestCase):
    def test_canonical_file_has_the_section_above_the_checks(self):
        text = CHECKS.read_text()
        self.assertIn("## " + HEADING, text)
        self.assertLess(text.index("## " + HEADING), text.index("## Checks"))
        self.assertLess(text.index("## Checks"), text.index("**1. Verify through the user's path"))

    def test_both_commands_name_the_path_heading_and_not_loaded(self):
        for cmd in COMMANDS:
            text = one_line(cmd.read_text())
            with self.subTest(cmd=cmd.name):
                self.assertIn(PATH, text)
                self.assertIn(HEADING, text)
                self.assertIn("Standing operating rule: not loaded", text)

    def test_no_other_file_restates_the_rule(self):
        homes = {s: [] for s in RULE_SENTENCES}
        examined = 0
        for p in REPO.rglob("*"):
            if ".git" in p.parts or "node_modules" in p.parts or not p.is_file() or p.suffix not in {".md", ".json", ".py", ".js", ".txt"}:
                continue
            if p == Path(__file__).resolve():
                continue
            examined += 1
            text = one_line(p.read_text(errors="ignore"))
            for s in RULE_SENTENCES:
                if s in text:
                    homes[s].append(p.relative_to(REPO).as_posix())
        print(f"examined {examined} files for the rule's text")
        self.assertGreater(examined, 0)
        for s, found in homes.items():
            self.assertEqual(found, [CHECKS.relative_to(REPO).as_posix()], s)

    def test_hook_session_start_output_carries_the_rule(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed; the hook could not be run")
        with tempfile.TemporaryDirectory() as data:
            env = {**os.environ, "CLAUDE_PLUGIN_DATA": data}
            env.pop("CODEX_HOME", None)
            env.pop("CLAUDE_CODE_HOST", None)
            out = subprocess.run([node, str(HOOK)], input=json.dumps({"session_id": "sm010-test"}), capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("VERIFICATION DISCIPLINE ACTIVE", out.stdout)
        self.assertIn("## " + HEADING, out.stdout)


if __name__ == "__main__":
    unittest.main()
