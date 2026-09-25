"""SM-003 criterion 9: every refusal the ledger check makes, and the pass it must not refuse."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mistake_ledger as ml  # noqa: E402

HEAD = "| id | date | what | caught_by | evidence | disposition | target | repeats |\n|---|---|---|---|---|---|---|---|\n"
M1 = "| M-001 | 2026-09-24 | packet named /tmp | reviewer | review r1 | became_check | XE-020 | |\n"
M2 = "| M-002 | 2026-09-24 | stale by date | self | grep | became_rule | analyzer/SKILL.md | |\n"
CAUGHT = ml.vocab_ids("caught_by")
DISP = ml.vocab_ids("mistake_disposition")


def check(text):
    return ml.validate(ml.parse(text), CAUGHT, DISP)


class MistakeLedger(unittest.TestCase):
    def test_vocabulary_carries_both_groups(self):
        self.assertEqual(CAUGHT, {"user", "reviewer", "test", "ci", "self"})
        self.assertEqual(DISP, {"became_check", "became_rule", "one_off"})

    def test_valid_ledger_passes(self):
        self.assertEqual(check(HEAD + M1 + M2), [])
        self.assertEqual(len(ml.parse(HEAD + M1 + M2)), 2)

    def test_empty_ledger_fails(self):
        self.assertTrue(any("no rows" in f for f in check(HEAD)))
        self.assertTrue(any("no rows" in f for f in check("no table here")))

    def test_missing_field_fails_by_name(self):
        f = check(HEAD + "| M-003 | 2026-09-24 | | user | quote | one_off | | |\n")
        self.assertIn("M-003: missing what", f)

    def test_unknown_caught_by_fails(self):
        f = check(HEAD + "| M-003 | 2026-09-24 | x | luck | q | one_off | | |\n")
        self.assertTrue(any("caught_by 'luck'" in x for x in f))

    def test_unknown_disposition_fails(self):
        f = check(HEAD + "| M-003 | 2026-09-24 | x | user | q | noted | | |\n")
        self.assertTrue(any("disposition 'noted'" in x for x in f))

    def test_duplicate_id_fails(self):
        self.assertIn("M-001: duplicate id", check(HEAD + M1 + M1))

    def test_check_or_rule_needs_a_target(self):
        f = check(HEAD + "| M-003 | 2026-09-24 | x | user | q | became_check | | |\n")
        self.assertIn("M-003: became_check names no target", f)

    def test_repeat_of_unknown_entry_fails(self):
        f = check(HEAD + M1 + "| M-003 | 2026-09-25 | x | user | q | became_check | XE-020 | M-009 |\n")
        self.assertTrue(any("not in the ledger" in x for x in f))

    def test_repeat_cannot_be_one_off(self):
        f = check(HEAD + M2 + "| M-003 | 2026-09-25 | again | user | q | one_off | | M-002 |\n")
        self.assertTrue(any("cannot be one_off" in x for x in f))

    def test_repeat_cannot_be_the_same_rule_again(self):
        f = check(HEAD + M2 + "| M-003 | 2026-09-25 | again | user | q | became_rule | analyzer/SKILL.md | M-002 |\n")
        self.assertTrue(any("same rule target" in x for x in f))

    def test_repeat_escalated_elsewhere_passes(self):
        self.assertEqual(check(HEAD + M2 + "| M-003 | 2026-09-25 | again | user | q | became_check | XE-021 | M-002 |\n"), [])
        self.assertEqual(check(HEAD + M2 + "| M-003 | 2026-09-25 | again | user | q | became_rule | other/SKILL.md | M-002 |\n"), [])

    def test_cli_reports_what_it_examined(self):
        import io, contextlib, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as t:
            t.write(HEAD + M1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = ml.main([t.name])
        self.assertEqual(rc, 0)
        self.assertIn("examined 1 row(s), 0 failure(s)", out.getvalue())
        Path(t.name).unlink()


if __name__ == "__main__":
    unittest.main()
