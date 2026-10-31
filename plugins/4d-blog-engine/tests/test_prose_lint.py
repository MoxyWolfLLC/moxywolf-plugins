"""BP-002: prose_lint counts the tells an outside detector flagged and the Wikipedia ones.

ponytail: synthetic texts, one per criterion; the real email that prompted this stays out of the repo.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prose_lint as pl  # noqa: E402

RUN = (
    "Teams propose and vote. Signed rule cards decide. A reviewer rules on what the cards can’t settle. "
    "Every output keeps the exact question it answered and the evidence it saw along the way."
)
SPLIT = (
    "Teams propose and vote.\n\nSigned rule cards decide.\n\n"
    "A reviewer rules on what the cards can’t settle."
)
ZING = (
    "The method treats a missing match as a voted and gated result instead of silence. "
    "It also measures the links that were missed across every batch it runs. "
    "Most tools skip it."
)
NO_ZING = (
    "The method treats a missing match as a voted and gated result instead of silence. "
    "It also measures the links that were missed across every batch it runs. "
    "That measurement goes into the report next to the decisions it qualifies."
)


def rules(text, **kw):
    return [f["rule"] for f in pl.scan(text, **kw)["findings"]]


class ParallelRun(unittest.TestCase):
    def test_run_in_one_paragraph_hits(self):
        self.assertEqual(rules(RUN).count("parallel_run"), 1)

    def test_split_across_paragraphs_does_not(self):
        self.assertNotIn("parallel_run", rules(SPLIT))

    def test_numbered_prose_item_counts(self):
        self.assertIn("parallel_run", rules("1. " + RUN))

    def test_longform_budgets_instead_of_scoring(self):
        short = pl.scan(RUN, longform=False)
        # The run (sentence 0) and a contrast framing three sentences later are one stacked pair.
        stacked = (
            "Teams propose and vote. Signed rule cards decide. A reviewer rules on what the cards can’t settle. "
            "It is not a guess about the outcome, but a record of the vote and the evidence behind it."
        )
        long_ = pl.scan(stacked, longform=True)
        self.assertIn("parallel_run", [f["rule"] for f in short["findings"]])
        self.assertNotIn("parallel_run", [f["rule"] for f in long_["findings"]])
        self.assertGreater(long_["metrics"]["density_violations"], 0)


    def test_closing_contrast_counts_once_in_longform(self):
        # Review F1: "Facts, not guesses." is a contrast framing and a closing zinger at one sentence.
        par = ("The panel reads every candidate mapping against the published source text. "
               "Each vote is stored with the model that cast it and the evidence it saw. "
               "A reviewer can replay the decision later without calling any model at all. "
               "The record shows which rule card settled it and which version was in force. "
               "Facts, not guesses.")
        r = pl.scan("\n\n".join([par] * 3), longform=True)
        self.assertEqual(r["metrics"]["density_violations"], 0)


class ClosingZinger(unittest.TestCase):
    def test_short_closer_hits(self):
        self.assertEqual(rules(ZING).count("closing_zinger"), 1)

    def test_long_closer_does_not(self):
        self.assertNotIn("closing_zinger", rules(NO_ZING))

    def test_numbered_prose_item_counts(self):
        self.assertIn("closing_zinger", rules("2. " + ZING))


class HereOpener(unittest.TestCase):
    def test_curly_and_straight(self):
        self.assertIn("here_opener", rules("Here’s where I think it lands in your plan for next year."))
        self.assertIn("here_opener", rules("Here's how the vote works when the panel disagrees on a case."))

    def test_other_here_does_not(self):
        self.assertNotIn("here_opener", rules("Here the panel disagrees, so a reviewer rules on the case."))


class WikipediaTells(unittest.TestCase):
    # Review F2: every new phrase, participle and word, each asserting its own rule.
    PHRASES = [
        ("It is part of a broader movement among auditors across the country.", "broader"),
        ("That was a defining moment for the team and for the product.", "defining moment"),
        ("The release marks a significant shift for the whole field this year.", "marks?"),
        ("Mapping plays a key role in how assessors read the evidence they get.", "plays?"),
        ("The outage serves as a reminder that backups need real restore tests.", "serves?"),
    ]
    PARTICIPLES = ["highlighting", "underscoring", "emphasizing", "emphasising", "reflecting",
                   "showcasing", "signaling", "signalling", "illustrating"]
    WORDS = ["breathtaking", "nestled", "vibrant", "stunning", "bustling", "renowned"]

    def test_each_phrase_hits_its_rule(self):
        for sentence, key in self.PHRASES:
            with self.subTest(sentence=sentence):
                self.assertTrue(any(r.startswith("banned_phrase:") and key in r for r in rules(sentence)))

    def test_each_participle_hits_the_trailing_clause_rule(self):
        for verb in self.PARTICIPLES:
            with self.subTest(verb=verb):
                got = rules(f"The team shipped the parser, {verb} the need for better tests.")
                self.assertTrue(any(r.startswith("banned_phrase:,") and verb in r for r in got), got)

    def test_each_word_hits_its_rule(self):
        for w in self.WORDS:
            with self.subTest(word=w):
                self.assertIn(f"banned_word:{w}", rules(f"The office has a {w} view of the parking lot."))

    def test_plain_verb_does_not(self):
        self.assertFalse(any(r.startswith(("banned_phrase:", "banned_word:"))
                             for r in rules("The results highlight the gap between the two methods.")))


class HiddenUnicode(unittest.TestCase):
    def test_flagged_and_fixed(self):
        dirty = "Plain text​ with a hidden﻿ mark."
        self.assertIn("hidden_unicode", rules(dirty))
        fixed, counts = pl.auto_fix(dirty)
        self.assertEqual(counts["hidden_unicode"], 2)
        self.assertNotIn("​", fixed)
        self.assertNotIn("﻿", fixed)

    def test_nbsp_not_flagged(self):
        self.assertNotIn("hidden_unicode", rules("Ten percent of the checks failed on the first run."))


class CatalogMirrorsScript(unittest.TestCase):
    def test_new_rules_and_words_in_catalog(self):
        cat = (ROOT / "references" / "ai-anti-patterns.md").read_text(encoding="utf-8")
        for term in ["parallel_run", "closing_zinger", "here_opener", "hidden_unicode",
                     "parallel-run", "closing-zinger", "breathtaking", "nestled", "vibrant",
                     "stunning", "bustling", "renowned", "defining moment", "serves? as a (reminder|testament)"]:
            with self.subTest(term=term):
                self.assertIn(term, cat)


if __name__ == "__main__":
    unittest.main()
