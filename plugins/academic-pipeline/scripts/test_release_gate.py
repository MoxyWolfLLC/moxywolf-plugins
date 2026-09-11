#!/usr/bin/env python3
"""AP-003 acceptance: the gate fails on exactly the planted defects, and passes clean input."""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate import run_gate

REQUIREMENTS = {
    "academic_requirements": {
        "citation_style": "Vancouver",
        "section_order": ["Abstract", "Keywords", "1. Introduction", "2. Discussion", "Funding", "References"],
        "gate_exempt_sections": [],
    },
    "moxywolf_constraints": {"forbidden_phrases": ["It's worth noting that", "Furthermore", "In conclusion"]},
}

CLEAN = """# A Paper

## Abstract
A short abstract that states the problem and the finding.

## Keywords
task graphs; verification

## 1. Introduction
The first source says one thing [1]. The second says another [2].

## 2. Discussion
The two disagree, which is the point.

## Funding
There are no sources of funding to declare.

## References

1. Lastname A. First work. Journal. 2024. https://example.org/first

2. Otherlastname B. Second work. Journal. 2025. https://example.org/second
"""

# three planted defects: an em dash, two references sharing a URL, and a missing section
DEFECTIVE = CLEAN.replace("The two disagree, which is the point.",
                          "The two disagree — which is the point.") \
                 .replace("https://example.org/second", "https://example.org/first") \
                 .replace("## Funding\nThere are no sources of funding to declare.\n\n", "")


def gate(paper_text):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "paper.md"); r = os.path.join(d, "req.json")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(paper_text)
    with open(r, "w", encoding="utf-8") as fh:
        json.dump(REQUIREMENTS, fh)
    return {name: (ok, detail) for name, ok, detail in run_gate(p, r)}


class GateTests(unittest.TestCase):
    def test_clean_paper_passes_every_check(self):
        res = gate(CLEAN)
        failed = [n for n, (ok, _) in res.items() if not ok]
        self.assertEqual(failed, [], f"clean paper should pass, failed: {[(n, res[n][1]) for n in failed]}")

    def test_fails_on_exactly_the_three_planted_defects(self):
        res = gate(DEFECTIVE)
        failed = sorted(n for n, (ok, _) in res.items() if not ok)
        self.assertEqual(failed, ["duplicate_sources", "em_dashes", "sections_present"])

    def test_each_planted_defect_is_named_in_its_detail(self):
        res = gate(DEFECTIVE)
        self.assertIn("em dash", res["em_dashes"][1])
        self.assertIn("example.org/first", res["duplicate_sources"][1])
        self.assertIn("Funding", res["sections_present"][1])

    def test_forbidden_phrase_is_caught_and_named(self):
        ok, detail = gate(CLEAN.replace("The two disagree", "Furthermore, the two disagree"))["forbidden_phrases"]
        self.assertFalse(ok)
        self.assertIn("Furthermore", detail)

    def test_duplicate_detection_is_by_url_not_by_entry_text(self):
        """Two different works cited identically apart from the link are not duplicates;
        two differently worded entries pointing at one URL are."""
        same_url = CLEAN.replace("Otherlastname B. Second work. Journal. 2025. https://example.org/second",
                                 "Completely Different Text Here. 2019. http://www.example.org/first/")
        self.assertFalse(gate(same_url)["duplicate_sources"][0], "normalized URL match should fire")


if __name__ == "__main__":
    unittest.main(verbosity=2)
