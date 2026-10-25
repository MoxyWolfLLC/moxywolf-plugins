"""SM-009: the session-end roster names Dorian C, as a person separate from Dorian, and no longer Phil.

ponytail: a text check over the skill and its command. A file that moves fails by being missing.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/session-end/SKILL.md"
HOMES = [SKILL, ROOT / "commands/session-end.md", ROOT / "commands/session-review.md"]
NAMES = ["Dorian", "Michael", "Dorian C", "Steven"]


def option_lists(text):
    """Each run of consecutive '- `Name`' lines in the skill, as a list of names."""
    runs, cur = [], []
    for line in text.splitlines():
        m = re.fullmatch(r"- `([^`]+)`(?: \*\(.*\)\*)?", line.strip())
        if m:
            cur.append(m.group(1))
        elif cur:
            runs.append(cur); cur = []
    return [r for r in runs if "Michael" in r]


class Roster(unittest.TestCase):
    def test_both_lists_name_the_four_and_not_phil(self):
        lists = option_lists(SKILL.read_text())
        print(f"examined {len(lists)} roster lists in {SKILL.name}")
        self.assertEqual(len(lists), 2, "the author and handoff-target lists moved")
        self.assertEqual(lists[0], NAMES)
        self.assertEqual(lists[1], ["Just stopping for the day", *NAMES])

    def test_dorian_c_normalizes_apart_from_dorian(self):
        text = SKILL.read_text()
        self.assertIn("(`dorian`, `michael`, `dorian-c`, `steven`)", text)

    def test_no_home_names_phil(self):
        hits = [f"{h.name}:{n}" for h in HOMES for n, line in enumerate(h.read_text().splitlines(), 1)
                if re.search(r"\bphil\b", line, re.I)]
        print(f"examined {len(HOMES)} files, {len(hits)} references to Phil")
        self.assertEqual(hits, [])

    def test_cloud_review_is_kept_without_asking(self):
        for h in [SKILL, ROOT / "commands/session-review.md"]:
            self.assertIn("--standing-consent SM-009", h.read_text(), h.name)

    def test_the_check_catches_the_old_roster(self):
        old = "- `Dorian`\n- `Michael`\n- `Phil`\n- `Steven`\n\nx\n- `Just stopping for the day`\n- `Dorian`\n- `Michael`\n- `Phil`\n- `Steven`\n"
        self.assertNotEqual(option_lists(old)[0], NAMES)


if __name__ == "__main__":
    unittest.main()
