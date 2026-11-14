"""BP-003 (goal shared-prose-lint item 2): academic-pipeline's prose lint is the 4d-blog-engine original, byte for byte.

ponytail: a byte comparison, not a sync script; the copy is refreshed by copying the two files again.
"""
import unittest
from pathlib import Path

PLUGINS = Path(__file__).resolve().parents[2]
PAIRS = [
    ("academic-pipeline/scripts/prose_lint.py", "4d-blog-engine/scripts/prose_lint.py"),
    ("academic-pipeline/references/ai-anti-patterns.md", "4d-blog-engine/references/ai-anti-patterns.md"),
]


class ProseLintCopy(unittest.TestCase):
    def test_copies_are_byte_identical_to_the_original(self):
        for copy, original in PAIRS:
            with self.subTest(copy=copy):
                a, b = PLUGINS / copy, PLUGINS / original
                self.assertTrue(a.is_file(), f"{copy} is missing")
                self.assertEqual(a.read_bytes(), b.read_bytes(),
                                 f"{copy} differs from plugins/{original}; copy the original over it again")


if __name__ == "__main__":
    unittest.main()
