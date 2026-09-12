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



class RegressionTests(unittest.TestCase):
    """One regression per blocker found in peer review 20260911-165938-d11564a-g289mqlt."""

    def test_unrelated_heading_beginning_with_a_required_name_does_not_satisfy_it(self):
        """F2: prefix matching let 'Funding mechanisms in prior research' pass as 'Funding'."""
        decoy = CLEAN.replace("## Funding\nThere are no sources of funding to declare.",
                              "### Funding mechanisms in prior research\nEarlier studies were grant supported.")
        ok, detail = gate(decoy)["sections_present"]
        self.assertFalse(ok, "an unrelated heading must not satisfy a required declaration")
        self.assertIn("Funding", detail)

    def test_declared_alias_does_satisfy_a_required_section(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "paper.md"); r = os.path.join(d, "req.json")
        req = json.loads(json.dumps(REQUIREMENTS))
        req["academic_requirements"]["section_aliases"] = {"Funding": ["Funding Statement"]}
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(CLEAN.replace("## Funding", "## Funding Statement"))
        with open(r, "w", encoding="utf-8") as fh:
            json.dump(req, fh)
        res = {n: (ok, d_) for n, ok, d_ in run_gate(p, r)}
        self.assertTrue(res["sections_present"][0], res["sections_present"][1])

    def test_duplicate_detection_covers_unnumbered_styles(self):
        """F1: only numbered entries were parsed, so APA, Chicago and MLA were never examined."""
        apa = CLEAN.split("## References")[0] + """## References

Lastname, A. (2024). First work. Journal. https://doi.org/10.1234/ABC

Otherlastname, B. (2025). Second work, worded entirely differently. https://dx.doi.org/10.1234/abc
"""
        ok, detail = gate(apa)["duplicate_sources"]
        self.assertFalse(ok, "unnumbered entries sharing a normalized DOI must be caught")
        self.assertIn("10.1234/abc", detail)


    def test_adjacent_numbered_entries_without_blank_lines_are_still_separate(self):
        """F3: the F1 fix split only on blank lines, merging adjacent numbered entries
        so only the first identifier was read."""
        packed = CLEAN.split("## References")[0] + """## References

1. Lastname A. First work. Journal. 2024. https://example.org/same
2. Otherlastname B. Second work. Journal. 2025. https://example.org/same
3. Thirdlastname C. Third work. Journal. 2026. https://example.org/other
"""
        ok, detail = gate(packed)["duplicate_sources"]
        self.assertFalse(ok, "adjacent numbered entries sharing a URL must be caught")
        self.assertIn("example.org/same", detail)

    def test_mixed_spacing_counts_every_entry(self):
        mixed = CLEAN.split("## References")[0] + """## References

1. Lastname A. First work. 2024. https://example.org/a
2. Otherlastname B. Second work. 2025. https://example.org/b

3. Thirdlastname C. Third work. 2026. https://example.org/c
"""
        ok, detail = gate(mixed)["duplicate_sources"]
        self.assertTrue(ok, detail)
        self.assertIn("3 unique sources", detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
