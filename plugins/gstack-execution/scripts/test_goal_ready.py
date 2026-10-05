"""GO-008.4: goal_ready.py against a stub GitHub API built from this checkout. No network."""
import base64
import contextlib
import io
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import goal_guard  # noqa: E402
import goal_ready as gr  # noqa: E402

R = "o/r"


def content(path):
    return {"content": base64.b64encode((gr.ROOT / path).read_bytes()).decode()}


class Stub:
    """A repository set up exactly as moxywolf-plugins is; each test breaks one thing."""

    def __init__(self):
        self.files = {"DESIGN.md": content("DESIGN.md"), ".github/CODEOWNERS": content(".github/CODEOWNERS")}
        for w in goal_guard.CHECKS:
            self.files[f".github/workflows/{w}"] = content(f".github/workflows/{w}")
        self.tree = [{"path": p, "sha": s, "type": "blob"} for p, s in gr.local_tree(gr.SCRIPTS).items()]
        self.rules = [{"type": "deletion"}, {"type": "non_fast_forward"},
                      {"type": "pull_request", "parameters": {"require_code_owner_review": True}},
                      {"type": "required_status_checks", "parameters": {"required_status_checks":
                                                                       [{"context": c} for c in gr.CHECKS]}}]
        self.env = {"deployment_branch_policy": {"custom_branch_policies": True}}
        self.branches = [("branch", "main")]
        self.repo = {"default_branch": "main"}
        self.refuse = set()

    def __call__(self, path):
        for frag in self.refuse:
            if frag in path:
                raise gr.Unknown(f"HTTP 403 on {path}")
        if path == f"repos/{R}":
            return self.repo
        if path.startswith(f"repos/{R}/contents/"):
            return self.files.get(path.split("/contents/", 1)[1].split("?", 1)[0])
        if path.startswith(f"repos/{R}/git/trees/"):
            return {"tree": self.tree, "truncated": False}
        if path.startswith(f"repos/{R}/rules/branches/main"):
            return self.rules if "page=1" in path else []
        if path == f"repos/{R}/environments/goal-holdout":
            return self.env
        if "/deployment-branch-policies" in path:
            return {"branch_policies": [{"type": t, "name": n} for t, n in self.branches]}
        raise AssertionError(path)


class Ready(unittest.TestCase):
    def status(self, stub):
        return {n: s for n, s, _ in gr.requirements(R, stub)}

    def test_a_repository_set_up_like_this_one_is_ready_on_all_seven(self):
        rows = gr.requirements(R, Stub())
        self.assertEqual(len(rows), 7)
        self.assertEqual([s for _, s, _ in rows], ["ready"] * 7, rows)

    def broken(self, fix, name):
        s = Stub()
        fix(s)
        st = self.status(s)
        self.assertEqual(st.pop(name), "missing", name)
        self.assertEqual(set(st.values()), {"ready"}, st)

    def test_each_requirement_fails_alone(self):
        self.broken(lambda s: s.repo.update(default_branch="master"), "app can read it, default branch main")
        self.broken(lambda s: s.files.pop("DESIGN.md"), "DESIGN.md with objectives (a goal serves one)")
        self.broken(lambda s: s.files.update({".github/CODEOWNERS": {"content": base64.b64encode(b"/.github/ @x\n").decode()}}),
                    "CODEOWNERS names Dorian on goal mode's gate paths")
        self.broken(lambda s: s.files.pop(".github/workflows/goal-holdout.yml"), "tests and goal workflows, as goal_guard pins them")
        self.broken(lambda s: s.tree.pop(), "goal-mode scripts, same as this checkout")
        self.broken(lambda s: s.rules[3]["parameters"]["required_status_checks"].pop(), "main's ruleset")
        self.broken(lambda s: s.rules[2]["parameters"].update(require_code_owner_review=False), "main's ruleset")
        self.broken(lambda s: s.branches.append(("branch", "goal/*")), "goal-holdout environment, main only")
        self.broken(lambda s: s.branches.__setitem__(0, ("tag", "main")), "goal-holdout environment, main only")
        self.broken(lambda s: s.branches.append(("tag", "main")), "goal-holdout environment, main only")

    def test_rules_split_across_rulesets_still_count(self):
        s = Stub()
        checks = s.rules[3]["parameters"]["required_status_checks"]
        s.rules[3:] = [{"type": "required_status_checks", "parameters": {"required_status_checks": checks[:2]}},
                       {"type": "required_status_checks", "parameters": {"required_status_checks": checks[2:]}},
                       {"type": "pull_request", "parameters": {"require_code_owner_review": False}}]
        self.assertEqual(self.status(s)["main's ruleset"], "ready")

    def test_a_later_rule_that_drops_dorian_wins(self):
        for override in ("/goals/ @someone-else\n", "/.github/workflows/goal-holdout.yml @someone-else\n",
                         "/plugins/gstack-execution/scripts/goal_run.py\n", "* @someoneelse\n", "*.yml @x\n",
                         "/**/goal_run.py @x\n"):
            def drop(s, override=override):
                text = (gr.ROOT / ".github/CODEOWNERS").read_text() + override
                s.files[".github/CODEOWNERS"] = {"content": base64.b64encode(text.encode()).decode()}
            self.broken(drop, "CODEOWNERS names Dorian on goal mode's gate paths")

    def test_the_gate_covers_the_goal_workflows_and_scripts(self):
        need = gr.gate_paths()
        for p in (".github/workflows/goal-holdout.yml", ".github/workflows/tests.yml", "goals/README.md",
                  "plugins/gstack-execution/scripts/goal_run.py"):
            self.assertIn(p, need)

    def test_a_refused_call_is_unknown_and_never_ready(self):
        s = Stub()
        s.refuse.add("/environments/")
        self.assertEqual(self.status(s)["goal-holdout environment, main only"], "unknown")

    def test_main_prints_one_line_for_an_invisible_repository(self):
        s = Stub()
        s.repo = None
        orig, gr.api = gr.api, lambda token: s
        self.addCleanup(setattr, gr, "api", orig)
        out = io.StringIO()
        with unittest.mock.patch.dict("os.environ", {"GITHUB_TOKEN": "t"}), contextlib.redirect_stdout(out):
            rc = gr.main([R])
        self.assertEqual(rc, 1)
        self.assertEqual(len(out.getvalue().splitlines()), 1, out.getvalue())

    def test_an_invisible_repository_stops_after_one_line(self):
        s = Stub()
        s.repo = None
        rows = gr.requirements(R, s)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "missing")


if __name__ == "__main__":
    unittest.main()
