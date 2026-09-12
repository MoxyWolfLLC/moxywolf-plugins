#!/usr/bin/env python3
"""AP-003 acceptance plus EV-001 coverage: the gate fails on exactly the planted
defects, passes clean input, and cannot report a pass over input it never examined.

Every check carries a seeded-defect case here, because a repair verified only
against the case that was reported reproduces the defect it is repairing. That
happened to this file's subject: the fix for one false pass introduced another in
the same check and passed its author's own testing.
"""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from release_gate import run_gate, PASS, FAIL, SKIP

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


def gate(paper_text, requirements=None):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "paper.md"); r = os.path.join(d, "req.json")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(paper_text)
    with open(r, "w", encoding="utf-8") as fh:
        json.dump(requirements or REQUIREMENTS, fh)
    return {rec["name"]: rec for rec in run_gate(p, r)}


def failed(res):
    return sorted(n for n, rec in res.items() if rec["status"] == FAIL)


class GateTests(unittest.TestCase):
    def test_clean_paper_passes_every_check(self):
        res = gate(CLEAN)
        self.assertEqual(failed(res), [], f"clean paper should pass: {[(n, res[n]['detail']) for n in failed(res)]}")

    def test_fails_on_exactly_the_three_planted_defects(self):
        self.assertEqual(failed(gate(DEFECTIVE)), ["duplicate_sources", "em_dashes", "sections_present"])

    def test_each_planted_defect_is_named_in_its_detail(self):
        res = gate(DEFECTIVE)
        self.assertIn("em dash", res["em_dashes"]["detail"])
        self.assertIn("example.org/first", res["duplicate_sources"]["detail"])
        self.assertIn("Funding", res["sections_present"]["detail"])

    def test_forbidden_phrase_is_caught_and_named(self):
        rec = gate(CLEAN.replace("The two disagree", "Furthermore, the two disagree"))["forbidden_phrases"]
        self.assertEqual(rec["status"], FAIL)
        self.assertIn("Furthermore", rec["detail"])

    def test_duplicate_detection_is_by_url_not_by_entry_text(self):
        """Two different works cited identically apart from the link are not duplicates;
        two differently worded entries pointing at one URL are."""
        same_url = CLEAN.replace("Otherlastname B. Second work. Journal. 2025. https://example.org/second",
                                 "Completely Different Text Here. 2019. http://www.example.org/first/")
        self.assertEqual(gate(same_url)["duplicate_sources"]["status"], FAIL)


class CoverageTests(unittest.TestCase):
    """EV-001. A check that examined nothing cannot report a pass, and a check that
    does not apply says SKIP rather than joining the green lines."""

    def test_every_check_reports_what_it_examined(self):
        for rec in gate(CLEAN).values():
            self.assertIn("examined", rec, rec["name"])
            self.assertIsInstance(rec["examined"], int)
            self.assertTrue(rec["unit"], f"{rec['name']} must name its unit of coverage")

    def test_no_passing_check_examined_zero_input(self):
        for text in (CLEAN, DEFECTIVE, ""):
            for rec in gate(text).values():
                if rec["status"] == PASS:
                    self.assertGreater(rec["examined"], 0, f"{rec['name']} passed over zero input: {rec['detail']}")

    def test_missing_reference_list_fails_the_duplicate_check(self):
        """The original false pass: no reference section parsed, so zero entries were
        examined and the check reported '0 unique sources' with a pass."""
        rec = gate(CLEAN.split("## References")[0])["duplicate_sources"]
        self.assertEqual(rec["status"], FAIL)
        self.assertEqual(rec["examined"], 0)
        self.assertIn("examined 0", rec["detail"])

    def test_empty_forbidden_phrase_list_fails_rather_than_reporting_a_clean_paper(self):
        req = json.loads(json.dumps(REQUIREMENTS))
        req["moxywolf_constraints"]["forbidden_phrases"] = []
        rec = gate(CLEAN, req)["forbidden_phrases"]
        self.assertEqual(rec["status"], FAIL)
        self.assertIn("examined 0", rec["detail"])

    def test_empty_section_order_fails_rather_than_reporting_all_present(self):
        req = json.loads(json.dumps(REQUIREMENTS))
        req["academic_requirements"]["section_order"] = []
        rec = gate(CLEAN, req)["sections_present"]
        self.assertEqual(rec["status"], FAIL)
        self.assertIn("examined 0", rec["detail"])

    def test_empty_paper_fails_the_line_scan(self):
        rec = gate("")["em_dashes"]
        self.assertEqual(rec["status"], FAIL)
        self.assertEqual(rec["examined"], 0)

    def test_non_vancouver_is_skip_not_pass(self):
        req = json.loads(json.dumps(REQUIREMENTS))
        req["academic_requirements"]["citation_style"] = "APA"
        rec = gate(CLEAN, req)["citation_order"]
        self.assertEqual(rec["status"], SKIP, "an inapplicable check is skipped, never passed")

    def test_vancouver_paper_without_citation_markers_cannot_pass_citation_order(self):
        """Renumber exits 0 over a paper with nothing to renumber. Coverage is what
        separates 'checked and correct' from 'nothing was there to check'."""
        no_markers = CLEAN.replace("one thing [1]", "one thing").replace("another [2]", "another")
        rec = gate(no_markers)["citation_order"]
        self.assertEqual(rec["examined"], 0)
        self.assertNotEqual(rec["status"], PASS)


class SeededDefectTests(unittest.TestCase):
    """One mutation per check that the check must catch. A check with no seeded defect
    is a check nobody has watched fail."""

    def test_each_check_catches_its_own_seeded_defect(self):
        seeds = {
            "em_dashes": CLEAN.replace("the point.", "the point — really."),
            "forbidden_phrases": CLEAN.replace("## 2. Discussion\n", "## 2. Discussion\nIn conclusion, "),
            "sections_present": CLEAN.replace("## Keywords\ntask graphs; verification\n\n", ""),
            "duplicate_sources": CLEAN.replace("https://example.org/second", "https://example.org/first"),
        }
        for name, mutated in seeds.items():
            with self.subTest(check=name):
                rec = gate(mutated)[name]
                self.assertEqual(rec["status"], FAIL, f"{name} did not catch its seeded defect")
                self.assertGreater(rec["examined"], 0, f"{name} must fail having examined something")


class RegressionTests(unittest.TestCase):
    """One regression per blocker found in peer review 20260911-165938-d11564a-g289mqlt."""

    def test_unrelated_heading_beginning_with_a_required_name_does_not_satisfy_it(self):
        """F2: prefix matching let 'Funding mechanisms in prior research' pass as 'Funding'."""
        decoy = CLEAN.replace("## Funding\nThere are no sources of funding to declare.",
                              "### Funding mechanisms in prior research\nEarlier studies were grant supported.")
        rec = gate(decoy)["sections_present"]
        self.assertEqual(rec["status"], FAIL, "an unrelated heading must not satisfy a required declaration")
        self.assertIn("Funding", rec["detail"])

    def test_declared_alias_does_satisfy_a_required_section(self):
        req = json.loads(json.dumps(REQUIREMENTS))
        req["academic_requirements"]["section_aliases"] = {"Funding": ["Funding Statement"]}
        rec = gate(CLEAN.replace("## Funding", "## Funding Statement"), req)["sections_present"]
        self.assertEqual(rec["status"], PASS, rec["detail"])

    def test_duplicate_detection_covers_unnumbered_styles(self):
        """F1: only numbered entries were parsed, so APA, Chicago and MLA were never examined."""
        apa = CLEAN.split("## References")[0] + """## References

Lastname, A. (2024). First work. Journal. https://doi.org/10.1234/ABC

Otherlastname, B. (2025). Second work, worded entirely differently. https://dx.doi.org/10.1234/abc
"""
        rec = gate(apa)["duplicate_sources"]
        self.assertEqual(rec["status"], FAIL, "unnumbered entries sharing a normalized DOI must be caught")
        self.assertIn("10.1234/abc", rec["detail"])

    def test_adjacent_numbered_entries_without_blank_lines_are_still_separate(self):
        """F3: the F1 fix split only on blank lines, merging adjacent numbered entries
        so only the first identifier was read."""
        packed = CLEAN.split("## References")[0] + """## References

1. Lastname A. First work. Journal. 2024. https://example.org/same
2. Otherlastname B. Second work. Journal. 2025. https://example.org/same
3. Thirdlastname C. Third work. Journal. 2026. https://example.org/other
"""
        rec = gate(packed)["duplicate_sources"]
        self.assertEqual(rec["status"], FAIL, "adjacent numbered entries sharing a URL must be caught")
        self.assertIn("example.org/same", rec["detail"])

    def test_mixed_spacing_counts_every_entry(self):
        mixed = CLEAN.split("## References")[0] + """## References

1. Lastname A. First work. 2024. https://example.org/a
2. Otherlastname B. Second work. 2025. https://example.org/b

3. Thirdlastname C. Third work. 2026. https://example.org/c
"""
        rec = gate(mixed)["duplicate_sources"]
        self.assertEqual(rec["status"], PASS, rec["detail"])
        self.assertIn("3 unique sources", rec["detail"])
        self.assertEqual(rec["examined"], 3, "coverage must equal the entries actually parsed")

    def test_entries_without_identifiers_are_counted_and_named(self):
        """An entry with no DOI or URL cannot be compared. Saying so is the difference
        between 'no duplicates' and 'no duplicates among the ones I could read'."""
        mixed = CLEAN.split("## References")[0] + """## References

1. Lastname A. A book with no link. Publisher; 2024.

2. Otherlastname B. Second work. 2025. https://example.org/b
"""
        rec = gate(mixed)["duplicate_sources"]
        self.assertEqual(rec["examined"], 2)
        self.assertIn("no resolvable identifier", rec["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
