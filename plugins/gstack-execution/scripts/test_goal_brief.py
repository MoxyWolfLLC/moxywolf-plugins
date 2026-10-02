"""GO-001 criterion 6: goal_brief.py check and verify refuse what the item says they refuse."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import goal_brief as gb  # noqa: E402

DESIGN = "## Goal\nx\n## Items and acceptance criteria\n## Eleventh objective: goal mode\ny\n## Boundary tests\n## Amendments log\n"
CO = "/.github/ @d\n/plugins/gstack-execution/scripts/peer_review.py @d\n/goals/ @d\n/goal-runs/ @d\n"
TRACKED = ["plugins/gstack-execution/scripts/peer_review.py", "plugins/foo/a.py", ".github/CODEOWNERS"]


def brief(**over):
    body = {s: "1" for s in gb.SECTIONS}
    body.update({"Serves": "Eleventh objective: goal mode", "Allowed paths": "- plugins/foo/**",
                 "Provider budgets": "- openrouter: 3\n- gemini: 2", "Spend cap": "$5",
                 "Max items": "3", "Max review rounds per item": "3", "Max calls": "40"})
    body.update(over)
    return "".join(f"## {k}\n{v}\n\n" for k, v in body.items() if v is not None)


class Check(unittest.TestCase):
    def make(self, goal=None, plan="1. one\n2. two\n", files=("holdout.sha256",), tests=True):
        g = Path(self.tmp.name, "g")
        g.mkdir()
        if goal is not False:
            (g / "GOAL.md").write_text(goal or brief())
        if plan is not None:
            (g / "PLAN.md").write_text(plan)
        for f in files:
            (g / f).write_text("0" * 64)
        if tests:
            (g / "tests").mkdir()
            (g / "tests" / "test_goal.py").write_text("")
        return g

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, g):
        return gb.check(g, DESIGN, CO, TRACKED)

    def test_valid_folder_passes_and_reports_coverage(self):
        errs, n = self.run_check(self.make())
        self.assertEqual(errs, [])
        self.assertEqual(n, len(gb.FILES) + 1 + len(gb.SECTIONS))

    def test_each_missing_section_is_named(self):
        for s in gb.SECTIONS:
            with self.subTest(section=s):
                self.tmp.cleanup(); self.tmp = tempfile.TemporaryDirectory()
                errs, _ = self.run_check(self.make(brief(**{s: None})))
                self.assertIn(f"missing or empty section: {s}", errs)

    def test_each_missing_file_is_named(self):
        for missing in ("GOAL.md", "PLAN.md", "holdout.sha256", "tests/"):
            with self.subTest(missing=missing):
                self.tmp.cleanup(); self.tmp = tempfile.TemporaryDirectory()
                g = self.make(goal=False if missing == "GOAL.md" else None,
                              plan=None if missing == "PLAN.md" else "1. one\n",
                              files=() if missing == "holdout.sha256" else ("holdout.sha256",),
                              tests=missing != "tests/")
                errs, _ = self.run_check(g)
                self.assertTrue(any(missing.rstrip("/") in e for e in errs), errs)

    def test_examining_nothing_reports_zero(self):
        g = Path(self.tmp.name, "empty"); g.mkdir()
        _, n = self.run_check(g)
        self.assertEqual(n, 0)

    def test_serves_naming_no_objective_is_refused(self):
        errs, _ = self.run_check(self.make(brief(Serves="Twelfth objective: nothing")))
        self.assertTrue(any("Serves names no objective" in e for e in errs), errs)

    def test_serves_naming_a_non_objective_heading_is_refused(self):
        errs, _ = self.run_check(self.make(brief(Serves="Boundary tests")))
        self.assertTrue(any("Serves names no objective" in e for e in errs), errs)

    def test_allowed_path_reaching_codeowners_is_refused(self):
        for g in ("plugins/gstack-execution/scripts/*", ".github/**", "goals/**", "**"):
            with self.subTest(glob=g):
                self.tmp.cleanup(); self.tmp = tempfile.TemporaryDirectory()
                errs, _ = self.run_check(self.make(brief(**{"Allowed paths": f"- {g}"})))
                self.assertTrue(any("reaches a CODEOWNERS path" in e for e in errs), errs)

    def test_max_items_bounds(self):
        for v in ("0", "11"):
            with self.subTest(max_items=v):
                self.tmp.cleanup(); self.tmp = tempfile.TemporaryDirectory()
                errs, _ = self.run_check(self.make(brief(**{"Max items": v})))
                self.assertTrue(any(e.startswith("Max items must be") for e in errs), errs)

    def test_plan_longer_than_max_items_is_refused(self):
        errs, _ = self.run_check(self.make(brief(**{"Max items": "1"})))
        self.assertTrue(any("more than Max items" in e for e in errs), errs)

    def test_max_review_rounds_four_is_refused(self):
        errs, _ = self.run_check(self.make(brief(**{"Max review rounds per item": "4"})))
        self.assertTrue(any(e.startswith("Max review rounds per item must be") for e in errs), errs)

    def test_budgets_past_the_cap_are_refused(self):
        errs, _ = self.run_check(self.make(brief(**{"Provider budgets": "- openrouter: 4\n- gemini: 2"})))
        self.assertTrue(any("more than the Spend cap" in e for e in errs), errs)

    def test_negative_budget_cannot_offset(self):
        errs, _ = self.run_check(self.make(brief(**{"Provider budgets": "- openrouter: 9\n- gemini: -6"})))
        self.assertTrue(any("finite positive" in e for e in errs), errs)


HEAD, OLD, TREE = "a" * 40, "b" * 40, "c" * 40


def fake(reviews, merged=True, main_tree=TREE, head_tree=TREE):
    def get(path):
        if path.endswith("/pulls/7"):
            return {"merged": merged, "head": {"sha": HEAD}, "base": {"ref": "main"}}
        if "/reviews" in path:
            return reviews
        if f"ref={HEAD}" in path:
            return [{"name": "g1", "type": "dir", "sha": head_tree}]
        return [{"name": "g1", "type": "dir", "sha": main_tree}] if main_tree else []
    return get


def review(login="dorianatmoxywolf", state="APPROVED", commit=HEAD, rid=1):
    return {"id": rid, "user": {"login": login}, "state": state, "commit_id": commit}


class Verify(unittest.TestCase):
    def go(self, get):
        return gb.verify("g1", 7, "o/r", "dorianatmoxywolf", get)

    def test_approved_at_head_with_matching_tree_passes(self):
        rec, errs = self.go(fake([review()]))
        self.assertEqual(errs, [])
        self.assertEqual(rec, {"goal": "g1", "pr": 7, "review_id": 1, "head": HEAD, "tree": TREE})

    def test_review_by_someone_else_is_refused(self):
        _, errs = self.go(fake([review(login="someone")]))
        self.assertTrue(any("no standing APPROVED review" in e for e in errs), errs)

    def test_commented_review_is_refused(self):
        _, errs = self.go(fake([review(state="COMMENTED")]))
        self.assertTrue(any("no standing APPROVED review" in e for e in errs), errs)

    def test_approval_at_older_commit_is_refused(self):
        _, errs = self.go(fake([review(commit=OLD)]))
        self.assertTrue(any("not the head" in e for e in errs), errs)

    def test_later_dismissal_undoes_approval(self):
        _, errs = self.go(fake([review(), review(state="DISMISSED", rid=2)]))
        self.assertTrue(any("no standing APPROVED review" in e for e in errs), errs)

    def test_main_tree_differing_is_refused(self):
        _, errs = self.go(fake([review()], main_tree="d" * 40))
        self.assertTrue(any("differs from the approved tree" in e for e in errs), errs)

    def test_unmerged_pr_is_refused(self):
        _, errs = self.go(fake([review()], merged=False))
        self.assertTrue(any("not merged" in e for e in errs), errs)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    print(f"examined {r.testsRun} cases")
    sys.exit(0 if r.wasSuccessful() and r.testsRun else 1)
