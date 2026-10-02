"""GO-001 criterion 6, plus the round-1 review findings F1 to F8: goal_brief.py refuses what it says."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import goal_brief as gb  # noqa: E402

DESIGN = "## Goal\nx\n## Items and acceptance criteria\n## Eleventh objective: goal mode\ny\n## Boundary tests\n## Amendments log\n"
CO = ("/.github/ @d\n**/hooks/ @d\n/plugins/gstack-execution/scripts/peer_review.py @d\n"
      "/goals/ @d\n/goal-runs/ @d\n")
PLAN = "1. Write the thing\n   - it exists\n2. Test the thing\n   - the test fails without it\n"
GOOD = {
    "Serves": "Eleventh objective: goal mode",
    "Outcome": "A review made in a cloud session can be read after the session ends.",
    "Non-goals": "- publishing reviews",
    "Scenarios": "- Given a cloud session that ran a review, then its record is in the vault after the session ends\n- A review record that exists only in the session must never happen",
    "Goal tests": "- `tests/test_survives.py::test_record_in_vault` (outcome)\n- `tests/test_survives.py::test_no_session_only_record` (invariant)",
    "Allowed paths": "- plugins/project-init/skills/session-end/*.md\n- plugins/project-init/scripts/*.py",
    "Spend cap": "$5",
    "Provider budgets": "- openrouter: $3\n- gemini: $2",
    "Max calls": "40",
    "Max items": "3",
    "Max review rounds per item": "3",
    "Stop conditions": "- any goal test regresses",
    "Pre-mortem": "- the test checks the path exists, not that the record is readable",
}


def brief(**over):
    body = dict(GOOD, **over)
    return "".join(f"## {k}\n{v}\n\n" for k, v in body.items() if v is not None)


class Check(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, goal=None, plan=PLAN, holdout="a" * 64, tests=True):
        self.n += 1
        g = Path(self.tmp.name, f"g{self.n}")
        g.mkdir()
        if goal is not False:
            (g / "GOAL.md").write_text(goal or brief())
        if plan is not None:
            (g / "PLAN.md").write_text(plan)
        if holdout is not None:
            (g / "holdout.sha256").write_text(holdout + "\n")
        if tests:
            (g / "tests").mkdir()
            (g / "tests" / "test_survives.py").write_text("")
        return g

    def errs(self, g, design=DESIGN, co=CO):
        return gb.check(g, design, co)[0]

    def refused(self, g, fragment, **kw):
        e = self.errs(g, **kw)
        self.assertTrue(any(fragment in x for x in e), e)

    def test_valid_folder_passes_and_reports_coverage(self):
        e, n = gb.check(self.make(), DESIGN, CO)
        self.assertEqual(e, [])
        self.assertEqual(n, len(gb.FILES) + 1 + len(gb.SECTIONS))

    def test_examining_nothing_reports_zero(self):
        g = Path(self.tmp.name, "empty"); g.mkdir()
        self.assertEqual(gb.check(g, DESIGN, CO)[1], 0)

    def test_each_missing_section_is_named(self):
        for s in gb.SECTIONS:
            with self.subTest(section=s):
                self.assertIn(f"missing or empty section: {s}", self.errs(self.make(brief(**{s: None}))))

    def test_each_missing_file_is_named(self):
        cases = {"GOAL.md": dict(goal=False), "PLAN.md": dict(plan=None),
                 "holdout.sha256": dict(holdout=None), "tests/": dict(tests=False)}
        for name, kw in cases.items():
            with self.subTest(missing=name):
                self.refused(self.make(**kw), name.rstrip("/"))

    def test_serves_naming_no_objective_is_refused(self):
        self.refused(self.make(brief(Serves="Twelfth objective: nothing")), "Serves must be")

    def test_serves_naming_a_non_objective_heading_is_refused(self):
        self.refused(self.make(brief(Serves="Boundary tests")), "Serves must be")

    def test_serves_is_checked_against_the_design_text_given(self):  # F4: main's text, not the branch's
        self.refused(self.make(), "Serves must be", design=DESIGN.replace("Eleventh", "Tenth"))

    # F1: structure, not just non-empty
    def test_scenarios_need_given_then_and_must_never_happen(self):
        self.refused(self.make(brief(Scenarios="- 1")), "given ... then")
        self.refused(self.make(brief(Scenarios="- Given x, then y")), "must never happen")

    def test_goal_tests_need_ids_marked_outcome_or_invariant(self):
        self.refused(self.make(brief(**{"Goal tests": "- 1"})), "Goal tests: expected")
        self.refused(self.make(brief(**{"Goal tests": "- test_a (sometimes)"})), "Goal tests: expected")

    def test_unbulleted_lines_are_refused_not_dropped(self):
        self.refused(self.make(brief(**{"Provider budgets": "openrouter: $500"})), "not a '- ' bullet")
        self.refused(self.make(brief(**{"Allowed paths": ".github/**"})), "not a '- ' bullet")

    def test_holdout_must_be_a_sha256(self):
        self.refused(self.make(holdout="0" * 63), "holdout.sha256")
        self.refused(self.make(holdout="hello"), "holdout.sha256")

    def test_plan_items_need_acceptance_criteria(self):
        self.refused(self.make(plan="1. one\n2. two\n"), "no indented acceptance criteria")
        self.refused(self.make(plan="# Plan\n\n"), "lists no numbered items")

    def test_plan_lines_that_are_not_items_or_criteria_are_refused(self):  # round 2 F1
        indented = "1. First\n   - first passes\n 2. Second\n   - second passes\n"
        self.refused(self.make(plan=indented), "neither a '1. ' item")
        self.refused(self.make(plan="1. First\n   - ok\nsome prose\n"), "neither a '1. ' item")
        self.refused(self.make(plan="1) First\n   - ok\n"), "neither a '1. ' item")

    def test_plan_with_a_title_and_blank_lines_passes(self):
        self.assertEqual(self.errs(self.make(plan="# Plan\n\n" + PLAN + "\n")), [])

    # F2: rules, not sampled files
    def test_allowed_path_reaching_codeowners_is_refused(self):
        for g in ("plugins/gstack-execution/scripts/*", ".github/**", ".github/new-gate/**",
                  "goals/**", "goal-runs/x/*", "plugins/new-plugin/hooks/*", "plugins/foo/**", "**"):
            with self.subTest(glob=g):
                self.refused(self.make(brief(**{"Allowed paths": f"- {g}"})), "can reach CODEOWNERS path")

    def test_a_file_named_hooks_is_not_a_hooks_folder(self):
        self.assertEqual(self.errs(self.make(brief(**{"Allowed paths": "- plugins/foo/hooks.md"}))), [])

    def test_empty_codeowners_is_refused(self):  # F4: no rules is not "nothing protected"
        self.refused(self.make(), "CODEOWNERS on main has no rules", co="")

    # bounds
    def test_max_items_bounds(self):
        for v in ("0", "11"):
            with self.subTest(max_items=v):
                self.refused(self.make(brief(**{"Max items": v})), "Max items must be")

    def test_plan_longer_than_max_items_is_refused(self):
        self.refused(self.make(brief(**{"Max items": "1"})), "more than Max items")

    def test_max_review_rounds_four_is_refused(self):
        self.refused(self.make(brief(**{"Max review rounds per item": "4"})), "Max review rounds per item must be")

    # F3: the whole value, exactly
    def test_numbers_must_be_written_plainly(self):
        self.refused(self.make(brief(**{"Max review rounds per item": "1e2"})), "Max review rounds per item must be")
        self.refused(self.make(brief(**{"Spend cap": "5 dollars"})), "Spend cap must be")
        self.refused(self.make(brief(**{"Max items": "3 items"})), "Max items must be")

    def test_budget_notation_tricks_are_refused(self):
        for line in ("- openrouter: 1e3", "- openrouter: -$2", "- openrouter: $0", "- : $1", "- openrouter: $1.005"):
            with self.subTest(line=line):
                self.refused(self.make(brief(**{"Provider budgets": line})), "Provider budget must read")

    def test_budgets_past_the_cap_are_refused_exactly(self):
        self.refused(self.make(brief(**{"Provider budgets": "- openrouter: $3.01\n- gemini: $2"})), "more than the Spend cap")
        self.assertEqual(self.errs(self.make(brief(**{"Provider budgets": "- openrouter: $2.99\n- gemini: $2.01"}))), [])


class Main(unittest.TestCase):
    def test_check_reads_main_and_fails_closed_without_it(self):  # F4
        with self.assertRaises(SystemExit) as c:
            gb.from_main("DESIGN.md", ref="refs/heads/no-such-branch-xyz")
        self.assertIn("Refusing to check against the working tree", str(c.exception))

    def test_cli_check_takes_no_policy_overrides(self):  # F4
        r = subprocess.run([sys.executable, gb.__file__, "check", "x", "--design", "y"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_cli_verify_refuses_an_owner_override(self):  # F6
        r = subprocess.run([sys.executable, gb.__file__, "verify", "g1", "--pr", "7", "--owner", "someone"],
                           capture_output=True, text=True, env={"GITHUB_TOKEN": "x", "PATH": "/usr/bin:/bin"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("--owner", r.stdout)


HEAD, OLD, BASE, TREE = "a" * 40, "b" * 40, "e" * 40, "c" * 40


def fake(pages, merged=True, base_ref="main", main_tree=TREE, head_tree=TREE, base_tree=None):
    trees = {HEAD: head_tree, "main": main_tree, BASE: base_tree}
    def get(path):
        if path.endswith("/pulls/7"):
            return {"merged": merged, "head": {"sha": HEAD}, "base": {"ref": base_ref, "sha": BASE}}
        if "/reviews" in path:
            page = int(path.rsplit("page=", 1)[1])
            return pages[page - 1] if page <= len(pages) else []
        ref = path.rsplit("ref=", 1)[1]
        t = trees.get(ref)
        return [{"name": "g1", "type": "dir", "sha": t}] if t else []
    return get


def review(login="dorianatmoxywolf", state="APPROVED", commit=HEAD, rid=1):
    return {"id": rid, "user": {"login": login}, "state": state, "commit_id": commit}


class Verify(unittest.TestCase):
    def go(self, get):
        return gb.verify("g1", 7, "o/r", get)

    def refused(self, get, fragment):
        _, e = self.go(get)
        self.assertTrue(any(fragment in x for x in e), e)

    def test_approved_at_head_with_matching_tree_passes(self):
        rec, e = self.go(fake([[review()]]))
        self.assertEqual(e, [])
        self.assertEqual(rec, {"goal": "g1", "pr": 7, "review_id": 1, "head": HEAD, "tree": TREE})

    def test_review_by_someone_else_is_refused(self):
        self.refused(fake([[review(login="someone")]]), "no standing APPROVED review")

    def test_commented_review_is_refused(self):
        self.refused(fake([[review(state="COMMENTED")]]), "no standing APPROVED review")

    def test_approval_at_older_commit_is_refused(self):
        self.refused(fake([[review(commit=OLD)]]), "not the head")

    def test_later_dismissal_undoes_approval(self):
        self.refused(fake([[review(), review(state="DISMISSED", rid=2)]]), "no standing APPROVED review")

    def test_a_decision_on_a_later_page_counts(self):  # F7
        page1 = [review(login=f"bot{i}", state="COMMENTED", rid=10 + i) for i in range(99)] + [review()]
        self.refused(fake([page1, [review(state="CHANGES_REQUESTED", rid=200)]]), "no standing APPROVED review")

    def test_main_tree_differing_is_refused(self):
        self.refused(fake([[review()]], main_tree="d" * 40), "differs from the approved tree")

    def test_pr_not_targeting_main_is_refused(self):  # F5
        self.refused(fake([[review()]], base_ref="feature"), "not main")

    def test_pr_that_did_not_add_the_goal_is_refused(self):  # F8
        self.refused(fake([[review()]], base_tree=TREE), "already existed before")

    def test_pr_that_changed_an_existing_goal_is_refused(self):  # round 2 F8: adds, not changes
        self.refused(fake([[review()]], base_tree="f" * 40), "already existed before")

    def test_unmerged_pr_is_refused(self):
        self.refused(fake([[review()]], merged=False), "not merged")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    print(f"examined {r.testsRun} cases")
    sys.exit(0 if r.wasSuccessful() and r.testsRun else 1)
