import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # run_all_tests runs this file as a script
from pilotmod.slug import slug  # noqa: E402


class Slug(unittest.TestCase):
    def test_runs_of_other_characters_become_one_hyphen(self):
        for text, want in [("Hello, World!", "hello-world"), ("  --Été 2026: A/B__test!! ", "été-2026-a-b-test"),
                           ("A¼B", "a-b"), ("xⅧy", "x-y"), ("---", ""), ("", "")]:
            with self.subTest(text=text):
                self.assertEqual(slug(text), want)


if __name__ == "__main__":
    unittest.main()
