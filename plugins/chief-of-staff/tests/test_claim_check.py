"""CS-006: a line that reaches Dorian is a quotation found in its source or a labeled line.

These run the real script as a subprocess, the way the Chief of Staff does, and read its exit code
and its receipt. The slipped sentences below are copied from recorded scenario runs 12 to 15, where
an evaluator failed them: each must fail as written and pass once it's labeled as an inference.

ponytail: stdlib, tempfiles, one subprocess per case. The script can't judge whether an inference is
sound or a `Me:` line is true, so nothing here pretends to test that.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/claim_check.py"
SALES = """1. Answer. Offer the 30% discount. Halden's buyer said on 2026-10-06 that budget closes this month.
7. Verification performed or missing. Read the supplied note. No CRM read.
9. Pending approvals. Audience: Halden's buyer; the address is not in the dispatch.
"""
FINANCE = """- Answer. Don't offer 30%. At $48,000 list, 30% off is **$14,400 of margin** and takes this deal below the floor.
- Open questions. Whether Halden would accept prepay.
"""
# (the sentence as the subject wrote it, the run it came from)
SLIPPED = [("Security hasn't reviewed either result.", "run 12, S12"),
           ("Nothing's been checked with Halden.", "run 15, S7"),
           ("Halden's address isn't confirmed.", "run 15, S11"),
           ("Sales used no cost numbers.", "run 15, S12"),
           ("Halden hasn't moved.", "run 15, S13"),
           ("The account may have CRM history which nobody read.", "run 15, S1")]


def check(doc, *extra, sources=True):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "doc.md").write_text(doc)
        (d / "sales.md").write_text(SALES)
        (d / "finance.md").write_text(FINANCE)
        argv = [sys.executable, str(SCRIPT), "--doc", str(d / "doc.md"), "--json", *extra]
        if sources:
            argv += ["--source", f"Sales={d / 'sales.md'}", "--source", f"Finance={d / 'finance.md'}"]
        r = subprocess.run(argv, capture_output=True, text=True)
    try:
        return r.returncode, json.loads(r.stdout)
    except ValueError:
        return r.returncode, {"raw": r.stdout + r.stderr}


class Forms(unittest.TestCase):
    def ok(self, doc, *extra):
        rc, out = check(doc, *extra)
        self.assertEqual((rc, out.get("failed")), (0, 0), out)
        return out

    def bad(self, doc, reason, *extra):
        rc, out = check(doc, *extra)
        self.assertEqual(rc, 1, out)
        self.assertTrue(any(reason in f["reason"] for f in out["failures"]), out["failures"])
        return out

    def test_a_quotation_found_in_its_source_passes(self):
        out = self.ok('- Finance: "At $48,000 list, 30% off is $14,400 of margin"\n'
                      '- Sales: “Read the supplied note.” and "No CRM read."\n')
        self.assertEqual((out["labeled"], out["quotations_verified"]), (2, 3))
        print("examined curly quotes, emphasis marks in the source, and two quotations joined by 'and'")

    def test_a_quotation_must_be_in_the_named_source(self):
        self.bad('- Sales: "Whether Halden would accept prepay"\n', "not found in Sales")
        self.bad('- Finance: "30% off is $14,000 of margin"\n', "not found in Finance")
        self.bad('- Sales: "Offer the 30% discount ... budget closes this month"\n', "not found in Sales")
        self.bad('- Marketing: "Offer the 30% discount"\n', "not a known label")
        print("examined the wrong source, a changed word, an ellipsis and an unknown source")

    def test_words_outside_the_quotation_fail(self):
        self.bad('- Sales: "No CRM read." So nobody has looked.\n', "outside its quotations")
        self.bad('- Sales: "No CRM"\n', "three words")
        self.bad("- Sales: says it read nothing.\n", "no quotation")

    def test_the_other_labels(self):
        self.ok("- Me: I didn't read the CRM.\n- Open: Would Halden accept prepay?\n- My inference: 10% is $4,800.\n"
                "- Inference: the deal slips.\n- Proposal: draft the quote.\n- Skill: sales:pipeline-review\n- Source: the dispatch, 2026-10-07\n")
        self.bad("- Me: Nobody read the CRM.\n", "first person")
        self.bad("- Me: I didn't read the CRM. Nobody did.\n", "one sentence")
        self.bad("- Open: Halden would accept prepay.\n", "question")
        self.bad("- My inference:\n", "empty")

    def test_structure_is_not_a_claim_and_a_claim_is_not_structure(self):
        self.ok("# Memo\n\n## 1. The call\n\n**A. Offer 30% off.**\n\n---\n\n- Open: Do we offer it?\n\n```\n- Outcome: escalated (nobody checked)\n```\n")
        self.bad("**A. Offer 30% off.** Sales wants it.\n- Open: Do we?\n", "unlabeled")
        self.bad("**" + "A long bold line is a sentence wearing a title's clothes, and it says nobody read the CRM at all" + "**\n- Open: Do we?\n", "unlabeled")
        self.bad("| Option | Cost |\n|---|---|\n| A | $14,400 |\n- Open: Do we?\n", "unlabeled")

    def test_a_document_with_nothing_labeled_does_not_pass(self):
        rc, out = check("# Memo\n\n**Title**\n")
        self.assertEqual(rc, 1, out)
        self.assertEqual(out["labeled"], 0)
        rc, out = check("")
        self.assertEqual(rc, 1, out)
        print("examined a document of structure only and an empty one: both fail, because nothing was examined")

    def test_sentences_the_evaluator_failed(self):
        for sentence, where in SLIPPED:
            self.bad(f"- Open: Do we offer it?\n{sentence}\n", "unlabeled")
            self.bad(f"- Open: Do we offer it?\n- {sentence}\n", "unlabeled")
            self.ok(f"- Open: Do we offer it?\n- My inference: {sentence}\n")
        print(f"examined {len(SLIPPED)} recorded sentences: each fails bare, fails as a bullet, and passes labeled as an inference")

    def test_a_source_is_quoted_never_retold(self):
        """Run 16, S12: an inference credited sales with more than it said. The label was right and the line was still wrong."""
        recorded = ("My inference: My second reason is that 10% with prepay is still a concession this month, "
                    "and a concession is what sales-department says keeps the deal from slipping.")
        for line in (recorded, "My inference: finance says 30% is too much.", "Inference: according to Sales, the deal slips.",
                     "Me: I checked, and finance's result confirms the floor.", "Proposal: do what Sales recommended."):
            self.bad(f"- Open: Do we offer it?\n- {line}\n", "retells")
        self.ok("- My inference: sales and finance give opposite answers.\n- Me: I sent the finance result to security.\n"
                "- Open: Is finance right about the floor?\n- My inference: the claim in the sales result rests on one call note.\n")
        print("examined 5 lines that retell a source, one of them recorded in run 16, and 4 that only refer to one")

    def test_blockquotes_and_extra_labels(self):
        self.ok('> - Finance: "takes this deal below the floor"\n> - Open: Is that right?\n')
        self.bad("DISPATCH: security the finance result\n- Open: Do we?\n", "not a known label")
        self.ok("DISPATCH: security the finance result\n- Open: Do we?\n", "--also", "DISPATCH")

    def test_the_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            doc = Path(d) / "doc.md"; doc.write_text("# Memo\n- Open: Do we offer it?\n```\nnobody read it\nat all\n```\n")
            r = subprocess.run([sys.executable, str(SCRIPT), "--doc", str(doc)], capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1]
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(last, r"^claim-check: examined 1 line, 1 labeled, 0 quotations verified, 0 failed, 1 titles and 2 fenced lines not examined, sha256 [0-9a-f]{64}$")
        r = subprocess.run([sys.executable, str(SCRIPT), "--doc", str(Path(d) / "gone.md")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, "a missing document is a usage error, not a pass and not a failed line")


if __name__ == "__main__":
    unittest.main()
