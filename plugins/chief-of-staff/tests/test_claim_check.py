"""CS-006: a line that reaches Dorian is a quotation found in its source or a labeled line.

These run the real script as a subprocess, the way the Chief of Staff does, and read its exit code
and its receipt. The slipped sentences below are copied from recorded scenario runs 12 to 17, where
an evaluator failed them: each must fail as written. Labeled as an inference it passes, unless it says
what nobody did, and then it fails under that label too.

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
8. Proposed next action. _Dorian decides on the discount_ and __sales drafts the quote__ from pipeline_review notes.
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
OPEN = "- Open: Do we offer it?\n"


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
        # emphasis marks in the source don't hide the words; an underscore inside an identifier is kept
        self.ok('- Sales: "Dorian decides on the discount" and "sales drafts the quote"\n- Sales: "from pipeline_review notes"\n'
                '- Sales: "_Dorian decides on the discount_" then "__sales drafts the quote__"\n')
        self.bad('- Sales: "from pipeline review notes"\n', "not found in Sales")
        print("examined curly quotes, asterisk and underscore emphasis in source and document, and quotations joined by and/then")

    def test_a_quotation_must_be_in_the_named_source(self):
        self.bad('- Sales: "Whether Halden would accept prepay"\n', "not found in Sales")
        self.bad('- Finance: "30% off is $14,000 of margin"\n', "not found in Finance")
        self.bad('- Marketing: "Offer the 30% discount"\n', "not a known label")
        # "he supplied note" is inside "the supplied note": a quotation starts and ends on a word
        self.bad('- Sales: "he supplied note. No CRM"\n', "not found in Sales")
        self.bad('- Sales: "Read the supplied no"\n', "not found in Sales")
        print("examined the wrong source, a changed word, an unknown source and two fragments that start or end inside a word")

    def test_an_ellipsis_is_never_a_quotation(self):
        """Review F2: a trailing ellipsis was stripped with the trailing period and then matched."""
        for q in ("Offer the 30% discount ... budget closes this month", "No CRM read...", "No CRM read…", "… No CRM read."):
            self.bad(f'- Sales: "{q}"\n', "ellipsis")

    def test_only_quotations_joined_by_and_or_then(self):
        """Review F2: the joiners were deleted wherever they stood, not checked for where they stood."""
        self.bad('- Sales: "No CRM read." So nobody has looked.\n', "outside its quotations")
        self.bad('- Sales: and "No CRM read." then\n', "outside its quotations")
        self.bad('- Sales: "No CRM read." "Read the supplied note."\n', "outside its quotations")
        self.bad('- Sales: "No CRM read." and then "Read the supplied note."\n', "outside its quotations")
        self.bad('- Sales: "No CRM"\n', "three words")
        self.bad("- Sales: says it read nothing.\n", "no quotation")
        self.bad('- Sales: "No CRM read\n', "no quotation")
        self.ok('- Sales: "No CRM read." then "Read the supplied note.", and "Offer the 30% discount".\n')

    def test_the_other_labels(self):
        self.ok("- Me: I didn't read the CRM.\n- Open: Would Halden accept prepay?\n- My inference: 10% is $4,800.\n"
                "- Inference: the deal slips.\n- Proposal: draft the quote.\n- Skill: sales:pipeline-review\n- Source: the dispatch, 2026-10-07\n")
        self.bad("- Me: Nobody read the CRM.\n", "first person")
        self.bad("- Me: I didn't read the CRM. Nobody did.\n", "one sentence")
        self.bad("- Open: Halden would accept prepay.\n", "question")
        for label in ("My inference", "Inference", "Proposal", "Skill", "Source"):
            self.bad(f"{OPEN}- {label}:\n", "empty")
            self.bad(f"{OPEN}- **{label}:**   \n", "empty")

    def test_structure_is_not_a_claim_and_a_claim_is_not_structure(self):
        self.ok("# Memo\n\n## 1. The call\n\n**A. Offer 30% off.**\n\n---\n\n- Open: Do we offer it?\n\n```\n- Outcome: escalated (nobody checked)\n```\n")
        self.bad("**A. Offer 30% off.** Sales wants it.\n- Open: Do we?\n", "unlabeled")
        self.bad("**" + "A long bold line is a sentence wearing a title's clothes, and it says nobody read the CRM at all" + "**\n- Open: Do we?\n", "unlabeled")
        self.bad("| Option | Cost |\n|---|---|\n| A | $14,400 |\n- Open: Do we?\n", "unlabeled")

    def test_a_fence_closes_only_on_its_own_kind(self):
        """Review F4: any line starting with three backticks toggled the fence, and a tilde fence wasn't one."""
        out = self.ok("~~~\nnobody read it\n~~~\n" + OPEN)
        self.assertEqual((out["fenced"], out["labeled"]), (1, 1))
        out = self.ok("````\n```\nnobody read it\n```\nstill inside the four-backtick block\n````\n" + OPEN)
        self.assertEqual((out["fenced"], out["labeled"]), (4, 1), "a shorter fence inside a longer one closed it")
        out = self.ok("```text\n~~~\nnobody read it\n```\n" + OPEN)
        self.assertEqual(out["fenced"], 2, "a tilde line inside a backtick block is content")
        # an unclosed fence swallows the rest, so the labeled line is never examined and the document doesn't pass
        rc, out = check("```\nnobody read it\n" + OPEN)
        self.assertEqual((rc, out["labeled"]), (1, 0), out)
        self.bad("```\nx\n```\nnobody read it\n" + OPEN, "unlabeled")

    def test_a_document_with_nothing_labeled_does_not_pass(self):
        rc, out = check("# Memo\n\n**Title**\n")
        self.assertEqual(rc, 1, out)
        self.assertEqual(out["labeled"], 0)
        rc, out = check("")
        self.assertEqual(rc, 1, out)
        print("examined a document of structure only and an empty one: both fail, because nothing was examined")

    def test_sentences_the_evaluator_failed(self):
        for sentence, where in SLIPPED:
            self.bad(f"{OPEN}{sentence}\n", "unlabeled")
            self.bad(f"{OPEN}- {sentence}\n", "unlabeled")
            labeled = f"{OPEN}- My inference: {sentence}\n"
            if "nobody" in sentence.lower() or "nothing" in sentence.lower():
                self.bad(labeled, "nobody")
            else:
                self.ok(labeled)
        print(f"examined {len(SLIPPED)} recorded sentences: each fails bare and as a bullet; labeled as an inference, "
              "the two that say what nobody did still fail and the other four pass")

    def test_a_source_is_quoted_never_retold(self):
        """Run 16, S12: an inference credited sales with more than it said. The label was right and the line was still wrong."""
        recorded = ("My inference: My second reason is that 10% with prepay is still a concession this month, "
                    "and a concession is what sales-department says keeps the deal from slipping.")
        for line in (recorded, "My inference: finance says 30% is too much.", "Inference: according to Sales, the deal slips.",
                     "Me: I checked, and finance's result confirms the floor.", "Proposal: do what Sales recommended.",
                     'Inference: "Finance says the deal is approved."'):   # review F3: quote marks don't hide a retelling
            self.bad(f"{OPEN}- {line}\n", "retells")
        self.ok("- My inference: sales and finance give opposite answers.\n- Me: I sent the finance result to security.\n"
                "- Open: Is finance right about the floor?\n- My inference: the claim in the sales result rests on one call note.\n")
        print("examined 6 lines that retell a source, one recorded in run 16 and one hidden in quote marks, and 4 that only refer to one")

    def test_an_inference_cannot_say_what_nobody_did(self):
        """Run 17, S2 and S8: two inferences said what nobody had done. One run can't know that."""
        for label in ("Inference", "My inference", "Proposal"):
            for claim in ("up to $2,000 goes to an audience nobody has evidenced.",
                          "the risk is that nobody has reviewed the email against the FTC guide.",
                          "no quote goes out, because nothing's written and sending one waits for you.",
                          "hold the send, since no one has checked the address.",
                          'hold because "nobody has reviewed the email".'):   # review F3: quote marks don't hide it
                self.bad(f"{OPEN}- {label}: {claim}\n", "nobody")
        self.ok("- Me: I sent nothing to Halden.\n- Me: I haven't reviewed the email against the FTC guide.\n"
                "- Open: Has nobody checked the address?\n- Inference: the email wasn't reviewed against the FTC guide in this run.\n")
        # honest lines the first version of this rule failed when it was replayed over run 17
        self.ok("- My inference: doing nothing is option B by default.\n- Proposal: the audience is the buyer. Nobody else.\n"
                "- Proposal: I do nothing further until a dispatch carries his recorded approval.\n"
                "- Inference: with no target number, nobody can grade the campaign afterwards.\n"
                "- Proposal: Nothing is written to the CRM until a recorded approval matches.\n")
        print("examined 5 claims about what nobody did under each of 3 labels, three recorded in runs 16 and 17, and 9 lines that make no such claim")

    def test_nothing_passes_unchecked(self):
        """Review F1: `--also LABEL` let any line through, including a built-in label or a source's own."""
        self.ok('> - Finance: "takes this deal below the floor"\n> - Open: Is that right?\n')
        self.bad("DISPATCH: security the finance result\n" + OPEN, "not a known label")
        for label in ("DISPATCH", "Me", "Sales"):
            rc, out = check("- Me: Nobody reviewed it.\n" + OPEN, "--also", label)
            self.assertEqual(rc, 2, f"--also {label} was accepted: {out}")

    def test_the_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            doc = Path(d) / "doc.md"; doc.write_text("# Memo\n- Open: Do we offer it?\n```\nnobody read it\nat all\n```\n")
            r = subprocess.run([sys.executable, str(SCRIPT), "--doc", str(doc)], capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1]
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(last, r"^claim-check: examined 1 line, 1 labeled, 0 quotations verified, 0 failed, 1 titles and 2 fenced lines not examined, sha256 [0-9a-f]{64}$")
        r = subprocess.run([sys.executable, str(SCRIPT), "--doc", str(Path(d) / "gone.md")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, "a missing document is a usage error, not a pass and not a failed line")
        # a source can't take the name of a built-in label, or `Me:` lines would stop meaning what they mean
        for name in ("Me", "Open", "Inference", "Proposal"):
            rc, out = check(OPEN, "--source", f"{name}={SCRIPT}")
            self.assertEqual(rc, 2, f"--source {name}=... was accepted: {out}")


if __name__ == "__main__":
    unittest.main()
