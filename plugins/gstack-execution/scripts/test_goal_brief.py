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
    "Goal tests": "- `tests/test_survives.py::Survives.test_record_in_vault` (outcome)\n- `tests/test_survives.py::Survives.test_no_session_only_record` (invariant)",
    "Allowed paths": "- plugins/project-init/skills/session-end/*.md\n- plugins/project-init/scripts/*.py",
    "Spend cap": "$5",
    "Provider budgets": "- openrouter: $3\n- gemini: $2",
    "Max calls": "40",
    "Max items": "3",
    "Max review rounds per item": "3",
    "Stop conditions": "- any goal test regresses",
    "Pre-mortem": "- the test checks the path exists, not that the record is readable",
}


TESTFILE = """# drafted-by: gpt/gpt-6-astra
import unittest


def candidate(expr):
    \"\"\"Run the candidate as its own program and return what it prints for expr. Goal tests never
    import the candidate: its code runs in a separate process, so it can't reach this one.\"\"\"
    import os, subprocess, sys
    r = subprocess.run([sys.executable, "-c", "import goalmod; print(repr(%s))" % expr],
                       cwd=os.environ["GOAL_CANDIDATE"], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


class Survives(unittest.TestCase):
    def test_record_in_vault(self):
        \"\"\"Scenario: Given a cloud session that ran a review, then its record is in the vault after the session ends\"\"\"
        self.assertEqual(candidate("goalmod.done"), "True")

    def test_no_session_only_record(self):
        \"\"\"Scenario: A review record that exists only in the session must never happen\"\"\"
        self.assertEqual(candidate("goalmod.session_only"), "False")
"""


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
            (g / "tests" / "test_survives.py").write_text(tests if isinstance(tests, str) else TESTFILE)
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

    # GO-002.1 and .4: tests exist, name their scenario, and one family drafted them
    def test_goal_test_id_must_name_an_existing_test(self):
        self.refused(self.make(brief(**{"Goal tests": "- `tests/test_survives.py::Survives.test_missing` (outcome)"})), "is not a unittest TestCase method")
        self.refused(self.make(brief(**{"Goal tests": "- `tests/nope.py::Survives.test_record_in_vault` (outcome)"})), "is not a unittest TestCase method")

    def test_goal_test_must_carry_a_brief_scenario(self):
        self.refused(self.make(tests=TESTFILE.replace("Scenario: Given a cloud", "Scenario: Given a laptop")), "needs a 'Scenario:' docstring line")
        self.refused(self.make(tests=TESTFILE.replace("Scenario: A review", "No scenario. A review")), "needs a 'Scenario:' docstring line")

    def test_malformed_goal_test_lines_are_refused(self):  # round 1 F3
        self.refused(self.make(brief(**{"Goal tests": "tests/test_survives.py::Survives.test_record_in_vault (outcome)"})), "not a '- ' bullet")
        self.refused(self.make(brief(**{"Goal tests": GOOD["Goal tests"] + "\n- just words"})), "Goal tests: expected")

    def test_nested_test_files_are_refused(self):  # round 1 F4
        g = self.make()
        (g / "tests" / "sub").mkdir()
        (g / "tests" / "sub" / "test_x.py").write_text("import unittest\n")
        self.refused(g, "not in a subfolder")

    def test_a_plain_class_method_is_not_a_test(self):  # round 1 F5
        self.refused(self.make(tests=TESTFILE.replace("class Survives(unittest.TestCase):", "class Survives:")), "is not a unittest TestCase method")

    def test_inherited_testcase_is_accepted(self):
        t = TESTFILE.replace("class Survives(unittest.TestCase):", "class Base(unittest.TestCase):\n    pass\n\n\nclass Survives(Base):")
        self.assertEqual(self.errs(self.make(tests=t)), [])

    def test_unlisted_test_method_is_refused(self):  # round 1 F7
        t = TESTFILE + "\n    def test_extra(self):\n        pass\n"
        self.refused(self.make(tests=t), "is not listed in Goal tests")

    def test_a_local_class_named_testcase_is_not_unittest(self):  # round 2 F5
        t = TESTFILE.replace("class Survives(unittest.TestCase):", "class TestCase:\n    pass\n\n\nclass Survives(TestCase):")
        self.refused(self.make(tests=t), "is not a unittest TestCase method")

    def test_an_inherited_mixin_test_must_be_listed(self):  # round 2 F7
        t = TESTFILE.replace("class Survives(unittest.TestCase):",
                             "class Extra:\n    def test_extra(self):\n        pass\n\n\nclass Survives(Extra, unittest.TestCase):")
        self.refused(self.make(tests=t), "Survives.test_extra is not listed in Goal tests")

    def test_a_test_file_that_imports_the_candidate_is_refused(self):  # sealed goal tests (GO-002.1)
        self.refused(self.make(tests=TESTFILE.replace("import unittest\n", "import unittest\nimport goalmod\n", 1)),
                     "never imports it")

    def test_goal_tests_name_their_drafter(self):
        self.refused(self.make(tests=TESTFILE.replace("# drafted-by: gpt/gpt-6-astra\n", "")), "drafted-by")

    def test_goal_tests_have_one_drafting_family(self):
        g = self.make()
        (g / "tests" / "test_more.py").write_text("# drafted-by: gemini/gemini-3.8-flash\nimport unittest\n")
        self.refused(g, "drafted by one model family")

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


class Baseline(unittest.TestCase):  # GO-002.2
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name, "repo"); self.repo.mkdir()
        self.goal = Path(self.tmp.name, "goal"); (self.goal / "tests").mkdir(parents=True)
        (self.goal / "tests" / "test_survives.py").write_text(TESTFILE)
        (self.goal / "GOAL.md").write_text(brief())

    def tearDown(self):
        self.tmp.cleanup()

    def main_is(self, done, session_only):
        (self.repo / "goalmod.py").write_text(f"done = {done}\nsession_only = {session_only}\n")
        return gb.baseline(self.goal, self.repo)

    def test_outcome_fails_and_invariant_holds_on_main_passes(self):
        self.assertEqual(self.main_is(False, False), ([], 2))

    def test_outcome_already_passing_on_main_is_refused(self):
        e, _ = self.main_is(True, False)
        self.assertTrue(any("already passes on main" in x for x in e), e)

    def test_invariant_failing_on_main_is_refused(self):
        e, _ = self.main_is(False, True)
        self.assertTrue(any("fails on main" in x for x in e), e)

    def test_relative_goal_path_runs_from_the_goal_folder(self):  # round 1 F1
        import os
        (self.repo / "goalmod.py").write_text("done = False\nsession_only = False\n")
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            self.assertEqual(gb.baseline(Path("goal"), self.repo), ([], 2))
        finally:
            os.chdir(cwd)

    def test_a_test_that_cannot_run_is_not_a_failure(self):  # round 1 F2
        (self.goal / "GOAL.md").write_text(brief(**{"Goal tests": "- `tests/missing.py::Survives.test_record_in_vault` (outcome)"}))
        e, n = self.main_is(False, False)
        self.assertEqual(n, 0)
        self.assertTrue(any("could not be run against main" in x for x in e), e)
        (self.goal / "GOAL.md").write_text(brief(**{"Goal tests": "- `tests/test_survives.py::Survives.test_gone` (outcome)"}))
        e, n = self.main_is(False, False)
        self.assertTrue(any("could not be run against main" in x for x in e), e)

    def test_a_test_whose_class_setup_fails_did_not_run(self):  # round 2 F2
        t = TESTFILE.replace("class Survives(unittest.TestCase):",
                             "class Survives(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        raise RuntimeError('no')\n")
        (self.goal / "tests" / "test_survives.py").write_text(t)
        e, n = self.main_is(False, False)
        self.assertEqual(n, 0)
        self.assertEqual(sum("could not be run against main" in x for x in e), 2, e)

    def test_module_fixtures_run_as_unittest_runs_them(self):  # review 2 F1
        t = TESTFILE.replace("import unittest\n", "import unittest\nready = False\n\n\ndef setUpModule():\n    global ready\n    ready = True\n", 1)
        t = t.replace('        self.assertEqual(candidate("goalmod.done"), "True")', "        self.assertTrue(ready)")
        (self.goal / "tests" / "test_survives.py").write_text(t)
        e, _ = self.main_is(False, False)
        self.assertTrue(any("test_record_in_vault already passes on main" in x for x in e), e)

    def test_a_failing_module_fixture_ran_nothing(self):  # review 2 F1
        t = TESTFILE.replace("import unittest\n", "import unittest\n\n\ndef setUpModule():\n    raise RuntimeError('no')\n", 1)
        (self.goal / "tests" / "test_survives.py").write_text(t)
        e, n = self.main_is(False, False)
        self.assertEqual(n, 0)
        self.assertEqual(sum("could not be run against main" in x for x in e), 2, e)

    def test_a_candidate_process_cant_write_a_verdict_that_counts(self):  # GO-003 review F3, sealed
        tid = "tests/test_survives.py::Survives.test_record_in_vault"
        for forged in ("passed", "failed"):
            (self.repo / "goalmod.py").write_text(
                "import os, sys\nos.write(1, b'\\ngoal-test-result guess %s\\n')\nos._exit(0)\n" % forged)
            self.assertNotEqual(gb.run_test(self.repo, self.goal, tid), "passed")
        t = TESTFILE.replace('        self.assertEqual(candidate("goalmod.done"), "True")',
                             '        import subprocess, sys, os\n        subprocess.run([sys.executable, "-c", "import goalmod"], cwd=os.environ["GOAL_CANDIDATE"])\n        self.fail("never")')
        (self.goal / "tests" / "test_survives.py").write_text(t)                  # the forged line reaches the harness's stdout
        (self.repo / "goalmod.py").write_text("import os\nos.write(1, b'\\ngoal-test-result 0000 passed\\n')\n")
        self.assertEqual(gb.run_test(self.repo, self.goal, tid), "failed")

    def test_a_test_that_loads_the_candidate_in_process_did_not_run(self):  # sealed goal tests (GO-002.1)
        t = TESTFILE.replace('        self.assertEqual(candidate("goalmod.done"), "True")',
                             '        import os, sys\n        sys.path.insert(0, os.environ["GOAL_CANDIDATE"])\n        import goalmod\n        self.assertTrue(goalmod.done)')
        (self.goal / "tests" / "test_survives.py").write_text(t)
        (self.repo / "goalmod.py").write_text("done = True\nsession_only = False\n")
        self.assertEqual(gb.run_test(self.repo, self.goal, "tests/test_survives.py::Survives.test_record_in_vault"), "not_run")

    def test_a_skipped_test_did_not_run(self):  # round 2 F2
        t = TESTFILE.replace('        self.assertEqual(candidate("goalmod.session_only")', "        self.skipTest('later')\n        self.assertEqual(candidate(\"goalmod.session_only\")")
        (self.goal / "tests" / "test_survives.py").write_text(t)
        e, n = self.main_is(False, False)
        self.assertEqual(n, 1)
        self.assertTrue(any("test_no_session_only_record could not be run" in x for x in e), e)

    def test_baseline_leaves_the_goal_folder_as_check_saw_it(self):  # round 2 F8
        before = gb.check(self.goal, DESIGN, CO)[0]
        self.assertEqual(self.main_is(False, False), ([], 2))
        self.assertEqual(gb.check(self.goal, DESIGN, CO)[0], before)
        self.assertFalse(any(self.goal.rglob("__pycache__")))

    def test_baseline_over_no_tests_fails(self):
        (self.goal / "GOAL.md").write_text(brief(**{"Goal tests": "- nothing here"}))
        e, n = self.main_is(False, False)
        self.assertEqual(n, 0)
        self.assertIn("baseline examined no goal tests", e)


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


READING = ("## Plain-English reading\n"
           "- tests/test_survives.py::Survives.test_record_in_vault checks the record is in the vault.\n"
           "- tests/test_survives.py::Survives.test_no_session_only_record checks no record lives only in the session.\n"
           "Read by: claude/claude-sonnet-5.5\n")


def b64(text):
    import base64
    return {"content": base64.b64encode(text.encode()).decode()}


def fake(pages, merged=True, base_ref="main", main_tree=TREE, head_tree=TREE, base_tree=None, body=READING):
    trees = {HEAD: head_tree, "main": main_tree, BASE: base_tree}
    def get(path):
        if path.endswith("/pulls/7"):
            return {"merged": merged, "head": {"sha": HEAD}, "base": {"ref": base_ref, "sha": BASE}, "body": body}
        if "/goals/g1/GOAL.md" in path:
            return b64(brief())
        if "/goals/g1/tests?" in path:
            return [{"name": "test_survives.py", "path": "goals/g1/tests/test_survives.py"}]
        if "/goals/g1/tests/test_survives.py" in path:
            return b64(TESTFILE)
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
        self.assertEqual(rec, {"goal": "g1", "pr": 7, "review_id": 1, "head": HEAD, "tree": TREE,
                               "drafted_by": ["gpt"], "read_by": "claude"})   # GO-003.3 reads these

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

    def test_pr_without_a_plain_english_reading_is_refused(self):  # GO-002.4
        self.refused(fake([[review()]], body="no reading"), "no '## Plain-English reading' section")

    def test_reading_must_cover_every_goal_test(self):
        body = READING.replace("- tests/test_survives.py::Survives.test_no_session_only_record checks no record lives only in the session.\n", "")
        self.refused(fake([[review()]], body=body), "doesn't cover")

    def test_a_prefix_id_does_not_cover_a_shorter_one(self):  # round 1 F6
        body = READING.replace("Survives.test_record_in_vault checks", "Survives.test_record_in_vault_later checks")
        self.refused(fake([[review()]], body=body), "doesn't cover")

    def test_reading_needs_a_reader(self):
        self.refused(fake([[review()]], body=READING.replace("Read by: claude/claude-sonnet-5.5\n", "")), "Read by")

    def test_reader_must_not_be_the_drafting_family(self):
        self.refused(fake([[review()]], body=READING.replace("claude/claude-sonnet-5.5", "gpt/gpt-6.1-sol")), "family that drafted")

    def test_unmerged_pr_is_refused(self):
        self.refused(fake([[review()]], merged=False), "not merged")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    print(f"examined {r.testsRun} cases")
    sys.exit(0 if r.wasSuccessful() and r.testsRun else 1)
