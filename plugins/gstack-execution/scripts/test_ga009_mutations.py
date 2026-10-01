"""GA-009 criterion 5, in CI: each new record-release case fails alone when its fix is removed.

Copies the plugin to a temp dir, applies one mutation to peer_review.py, and runs the one
test_governed_review.py case that guards it. A control run on the unmutated copy must pass,
so a failure means the mutation was caught, not that the harness is broken.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CASES = [  # (criterion, original text, mutated text, guarding test, text the failure must show)
    (2, 'elif merger.get("login") != AGENT_LOGIN:', "elif False:",
     "GovernedReview.test_wrong_actor_or_revision_cannot_authorize_release", "AssertionError"),
    (1, '"outcome": "agent_merge_autonomous"})',
     '"outcome": "agent_merge_autonomous"}); raise ReviewError("release_blocked", "unrequested agent merge")',
     "GovernedReview.test_agent_merge_without_a_matching_instruction_is_recorded_as_autonomous",
     "unrequested agent merge"),
    (3, 'raise ReviewError("release_blocked", "merge predates the release handoff")', "pass",
     "GovernedReview.test_an_autonomous_merge_before_the_handoff_is_still_refused", "AssertionError"),
]


def run_case(test, mutate=None):
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "gstack-execution"
        shutil.copytree(PLUGIN, copy, ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
        if mutate:
            target = copy / "scripts" / "peer_review.py"
            text = target.read_text()
            assert text.count(mutate[0]) == 1, f"mutation anchor not found exactly once: {mutate[0]}"
            target.write_text(text.replace(mutate[0], mutate[1]))
        return subprocess.run([sys.executable, str(copy / "scripts" / "test_governed_review.py"), test],
                              capture_output=True, text=True, timeout=300)


class GA009Mutations(unittest.TestCase):
    def test_each_case_passes_unmutated_and_fails_alone_when_its_fix_is_removed(self):
        for criterion, old, new, test, shows in CASES:
            with self.subTest(criterion=criterion):
                control = run_case(test)
                self.assertEqual(control.returncode, 0, control.stderr[-2000:])
                mutated = run_case(test, (old, new))
                self.assertNotEqual(mutated.returncode, 0, f"criterion {criterion}: mutation not caught")
                self.assertIn(shows, mutated.stderr)
                print(f"criterion {criterion}: {test.split('.')[-1]} passes unmutated, fails mutated")
        print(f"examined {len(CASES)} mutations")


if __name__ == "__main__":
    unittest.main()
