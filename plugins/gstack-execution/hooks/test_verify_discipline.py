"""XE-046: the verification block arrives once at session start, and again after compaction.

ponytail: runs the real hook as a subprocess with the hook JSON on stdin, the way the host calls it.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "verify-discipline.js"
MARK = "VERIFICATION DISCIPLINE ACTIVE"


class VerifyDisciplineDelivery(unittest.TestCase):
    def setUp(self):
        self.node = shutil.which("node")
        if not self.node:
            self.skipTest("node is not installed; the hook could not be run")
        self.data = tempfile.TemporaryDirectory()
        self.env = {**os.environ, "CLAUDE_PLUGIN_DATA": self.data.name}
        self.env.pop("CODEX_HOME", None)
        self.env.pop("CLAUDE_CODE_HOST", None)

    def tearDown(self):
        self.data.cleanup()

    def run_hook(self, mode, payload):
        args = [self.node, str(HOOK)] + ([mode] if mode else [])
        out = subprocess.run(args, input=json.dumps(payload), capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return MARK in out.stdout

    def test_prompt_then_startup_is_silent_the_second_time(self):
        self.assertTrue(self.run_hook("prompt", {"session_id": "s1"}))
        self.assertFalse(self.run_hook(None, {"session_id": "s1", "source": "startup"}))

    def test_startup_with_no_marker_emits_and_marks(self):
        self.assertTrue(self.run_hook(None, {"session_id": "s2", "source": "startup"}))
        self.assertFalse(self.run_hook("prompt", {"session_id": "s2"}))

    def test_every_other_source_emits_after_a_prompt(self):
        for source in ("compact", "clear", "resume", "fork"):
            with self.subTest(source=source):
                sid = "s3-" + source
                self.assertTrue(self.run_hook("prompt", {"session_id": sid}))
                self.assertTrue(self.run_hook(None, {"session_id": sid, "source": source}))

    def test_no_source_emits_after_a_prompt(self):
        self.assertTrue(self.run_hook("prompt", {"session_id": "s4"}))
        self.assertTrue(self.run_hook(None, {"session_id": "s4"}))

    def test_no_session_id_emits(self):
        self.assertTrue(self.run_hook(None, {"source": "startup"}))

    def test_subagent_emits_marker_or_not(self):
        self.assertTrue(self.run_hook("subagent", {"session_id": "s5"}))
        self.assertTrue(self.run_hook("prompt", {"session_id": "s5"}))
        self.assertTrue(self.run_hook("subagent", {"session_id": "s5"}))


if __name__ == "__main__":
    unittest.main()
