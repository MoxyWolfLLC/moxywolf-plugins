"""BP-003 (goal shared-prose-lint item 1): social_score.py runs the BP-002 lint on every post.

ponytail: three synthetic posts, run as the skill runs the script; no fixtures folder.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "social_score.py"

CLEAN = (
    "The evidence was missing.\n\n"
    "We checked again.\n\n"
    "A reviewer traced the disputed mapping to a missing source paragraph. "
    "During the next review, she attached the passage and recorded why the "
    "proposed match did not satisfy the published requirement. "
    "The record includes the question, the document version, and the evidence "
    "available when the decision was made.\n\n"
    "Another reviewer can inspect those materials without repeating the "
    "original search or asking the author to reconstruct the discussion. "
    "If a later edition changes the requirement, the team can identify which "
    "decisions need another look and retain the earlier explanation alongside "
    "the revision. "
    "We used this process on the last batch of mappings and found two cases "
    "that needed additional source material before review could continue."
)
RUN = "Teams propose and vote. Signed rule cards decide. A reviewer rules on what the cards can't settle.\n\n" + CLEAN
ZINGER = CLEAN + " Nobody else does."


def score(text):
    with tempfile.TemporaryDirectory() as d:
        post = Path(d) / "post.md"
        post.write_text(text, encoding="utf-8")
        out = Path(d) / "post.score.md"
        p = subprocess.run([sys.executable, str(SCRIPT), "--file", str(post), "--type", "post", "--out", str(out)],
                           capture_output=True, text=True, timeout=60)
        return p, json.loads(out.with_suffix(".json").read_text())


class SocialScoreLint(unittest.TestCase):
    def test_parallel_run_fails_the_check(self):
        p, result = score(RUN)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("STATUS=fail", p.stdout)
        self.assertIn("Prose lint", p.stdout)
        self.assertRegex(p.stdout, r"(?m)^- parallel_run \(Medium\): ")
        self.assertIn(("parallel_run", "Medium"), [(f["rule"], f["severity"]) for f in result["lint_findings"]])
        self.assertNotIn("parallel_run", [f["rule"] for f in result["findings"]])  # format verdict stays format-only

    def test_minor_finding_is_printed_and_passes(self):
        p, result = score(ZINGER)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertRegex(p.stdout, r"(?m)^- closing_zinger \(Minor\): ")
        self.assertEqual({f["severity"] for f in result["lint_findings"]}, {"Minor"})

    def test_clean_post_passes_as_before(self):
        p, result = score(CLEAN)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("STATUS=pass TYPE=post", p.stdout)
        self.assertEqual(result["lint_findings"], [])
        self.assertEqual([(f["rule"], f["severity"]) for f in result["findings"]], [("outside_sweet_spot", "Minor")])

    def test_missing_file_still_exits_2(self):
        p = subprocess.run([sys.executable, str(SCRIPT), "--file", "/nonexistent/post.md", "--type", "post"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 2)
        self.assertIn("file not found", p.stderr)
        self.assertEqual(p.stdout, "")


if __name__ == "__main__":
    unittest.main()
