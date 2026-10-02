"""GO-005 criteria 1 to 3: code types each change, and the type decides who decides."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_calls as gcalls  # noqa: E402
import goal_run as gr  # noqa: E402
import test_goal_run as tgr  # noqa: E402  its runner fixture

CO = "/.github/ @d\n/goals/ @d\n/goal-runs/ @d\n"
BRIEF = "## Allowed paths\n- `src/**`\n"


class Typing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@t"); self.git("config", "user.name", "t")
        self.commit({".github/CODEOWNERS": CO, "goals/g1/GOAL.md": BRIEF,
                     "src/a.py": "import os\nURL = 'https://api.known.com/v1'\nKEY = os.environ['KNOWN_KEY']\n"})

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, files):
        for k, v in files.items():
            (self.repo / k).parent.mkdir(parents=True, exist_ok=True); (self.repo / k).write_text(v)
        self.git("add", "-A"); self.git("commit", "-q", "-m", "c")
        return self.git("rev-parse", "HEAD")

    def typed(self, files):
        self.git("switch", "-q", "-C", "item", "main")
        head = self.commit(files)
        self.git("switch", "-q", "main")
        return gcalls.action_type(self.repo, "g1", head, base="main")

    def test_code_types_each_change(self):
        cases = [
            ({"src/b.py": "x = 1\n"}, "in_envelope_code"),
            ({"src/b.py": "u = 'https://api.known.com/v2'\nimport os\nk = os.environ.get('KNOWN_KEY')\n"}, "in_envelope_code"),
            ({"src/package.json": "{}\n"}, "dependency"),
            ({"src/requirements-dev.txt": "requests\n"}, "dependency"),
            ({"src/package-lock.json": "{}\n"}, "dependency"),
            ({"src/b.py": "u = 'https://known.com/x'\n"}, "external"),               # a suffix of api.known.com
            ({"src/b.py": "import os\nk = os.getenv('KEY')\n"}, "external"),         # a suffix of KNOWN_KEY
            ({"src/b.py": "import os\nk = os.getenv('known_key')\n"}, "external"),   # names are case-sensitive
            ({"src/run.sh": "echo ${NEW_TOKEN}\n"}, "external"),
            ({"src/run.sh": "export NEW_TOKEN=abc\n"}, "external"),
            ({"src/.env.example": "SERVICE_SECRET=x\n"}, "external"),
            ({"src/run.sh": "curl $DEPLOY_HOOK\n"}, "external"),
            ({"src/cfg.yml": "host: service.internal\n"}, "external"),
            ({"src/cfg.yml": "host: 10.0.0.5\n"}, "external"),
            ({"src/cfg.yml": "host: service.fr\n"}, "external"),                # a suffix not in any list
            ({"src/cfg.yml": "api_endpoint: 'edge.service.fr'\n"}, "external"),
            ({"src/b.py": "H = 'api.service.fr'\n"}, "external"),
            ({"src/b.py": "H = \"api.known.com:443\"\n"}, "in_envelope_code"),  # the base already uses it
            ({"src/b.py": "u = 'https://API.KNOWN.COM/v3'\n"}, "in_envelope_code"),  # hostnames aren't
            ({"src/b.py": "u = 'https://api.newhost.io/x'\n"}, "external"),
            ({"src/b.py": "import os\nk = os.getenv('BRAND_NEW_TOKEN')\n"}, "external"),
            ({"src/b.js": "const k = process.env.ANOTHER_NEW_NAME\n"}, "external"),
            ({"goals/g1/PLAN.md": "1. x\n   - y\n"}, "goal_brief"),
            ({"lib/x.py": "x = 1\n"}, "unclassified"),
            ({".github/workflows/x.yml": "on: push\n"}, "unclassified"),
        ]
        for files, want in cases:
            with self.subTest(files=list(files)):
                kind, reasons = self.typed(files)
                self.assertEqual(kind, want, reasons)
                self.assertTrue(reasons)

    def test_only_env_and_shell_files_vouch_for_a_bare_name(self):
        self.commit({"src/c.py": "NEW_TOKEN=1\n", "src/.env.example": "OLD_TOKEN=1\n", "src/run.sh": "echo $SH_TOKEN\n"})
        for name, want in (("NEW_TOKEN", "external"), ("OLD_TOKEN", "in_envelope_code"), ("SH_TOKEN", "in_envelope_code")):
            with self.subTest(name=name):
                kind, reasons = self.typed({"src/b.py": f"import os\nk = os.getenv('{name}')\n"})
                self.assertEqual(kind, want, reasons)

    def test_reasons_name_what_was_new(self):
        kind, reasons = self.typed({"src/b.py": "u = 'https://api.newhost.io/x'\nimport os\nk = os.getenv('BRAND_NEW_TOKEN')\n"})
        self.assertEqual(sorted(reasons), ["new environment variable BRAND_NEW_TOKEN", "new hostname api.newhost.io"])


def call(kind="in_envelope_code", proposed="claude/opus", framed="gpt/gpt-6"):
    return gcalls.new_call(1, "Which cache?", ["lru_cache", "custom"], proposed, framed, kind, ["r"], ["a" * 40])


VOTE = lambda model, role, choice: {"model": model, "role": role, "choice": choice, "reason": "because"}


class Council(unittest.TestCase):
    def test_only_in_envelope_code_goes_to_the_council(self):
        for kind in gcalls.TYPES:
            self.assertEqual(call(kind)["decider"], "council" if kind == "in_envelope_code" else "dorian")

    def test_a_unanimous_council_decides_and_a_split_one_escalates(self):
        c = gcalls.council(call(), [VOTE("gpt/gpt-6", "for", "lru_cache"), VOTE("gemini/g3", "against", "lru_cache")], "claude/opus")
        self.assertEqual((c["status"], c["choice"], c["decider"]), ("decided", "lru_cache", "council"))
        c = gcalls.council(call(), [VOTE("gpt/gpt-6", "for", "lru_cache"), VOTE("gemini/g3", "against", "custom")], "claude/opus")
        self.assertEqual((c["status"], c["decider"], c["choice"]), ("escalated", "dorian", None))
        self.assertEqual(len(c["dissent"]), 2)
        self.assertEqual(gcalls.waiting([c]), [c])

    def test_the_council_is_shaped_by_code(self):
        bad = {
            "the builder's family": ([VOTE("claude/x", "for", "custom"), VOTE("gpt/y", "against", "custom")], call()),
            "one family": ([VOTE("gpt/x", "for", "custom"), VOTE("gpt/y", "against", "custom")], call()),
            "one vote argues for": ([VOTE("gpt/x", "for", "custom"), VOTE("gemini/y", "for", "custom")], call()),
            "framed by the proposer's own family": ([VOTE("gpt/x", "for", "custom"), VOTE("gemini/y", "against", "custom")],
                                                    call(framed="claude/sonnet")),
            "isn't one of the options": ([VOTE("gpt/x", "for", "redis"), VOTE("gemini/y", "against", "custom")], call()),
            "two votes": ([VOTE("gpt/x", "for", "custom")], call()),
        }
        for why, (votes, c) in bad.items():
            with self.subTest(why=why):
                with self.assertRaisesRegex(ValueError, why):
                    gcalls.council(c, votes, "claude/opus")
                self.assertEqual(c["status"], "open")
        with self.assertRaisesRegex(ValueError, "isn't open to the council"):
            gcalls.council(call("dependency"), [VOTE("gpt/x", "for", "custom"), VOTE("gemini/y", "against", "custom")], "claude/opus")

    def test_dorian_answers_his_calls_in_his_words(self):
        c = call("external")
        with self.assertRaisesRegex(ValueError, "his own words"):
            gcalls.answer(c, "custom", "")
        with self.assertRaisesRegex(ValueError, "isn't one of the options"):
            gcalls.answer(c, "redis", "use redis")
        self.assertEqual(gcalls.answer(c, "custom", "go custom")["status"], "decided")
        with self.assertRaisesRegex(ValueError, "isn't waiting for Dorian"):
            gcalls.answer(call(), "custom", "mine")                  # an open council call isn't his


class Runner(tgr.RunnerFixture):
    """The runner records calls and waits for Dorian's; reuses the GO-003 fixture."""

    def test_a_call_thats_dorians_holds_the_run_until_he_answers(self):  # GO-005.1-.3
        self.start()
        self.git("switch", "-q", "-c", "build/item-1", "goal/g1")
        head = self.commit("dep", {"package.json": "{}\n"})
        self.git("switch", "-q", "main")
        c = gr.open_call(self.repo, "g1", "Add a dependency?", ["yes", "no"], "claude/opus", "gpt/gpt-6", head, base="main")
        self.assertEqual((c["type"], c["decider"], c["commits"]), ("dependency", "dorian", [head]))
        ok, out = self.next()
        self.assertIsNone(ok)                                            # waiting, not ended
        self.assertEqual(out["waiting"][0]["n"], 1)
        self.assertIsNone(gr.load("g1")["outcome"])
        gr.dorian_answers("g1", 1, "no", "no new dependencies in this goal")
        self.assertEqual(self.next()[1]["step"], "build")
        rec = gr.record("g1")
        self.assertIn("1. Add a dependency? (dependency, decided by dorian): no", rec)
        self.assertIn("no new dependencies in this goal", rec)

    def item_call(self, files, question="Which?", options=("a", "b")):
        self.git("switch", "-q", "-C", "build/item-1", "goal/g1")
        head = self.commit("change", files)
        self.git("switch", "-q", "main")
        return gr.open_call(self.repo, "g1", question, list(options), "claude/opus", "gpt/gpt-6", head, base="main")

    def test_a_lockfile_and_an_unclassified_change_each_wait_for_dorian(self):  # review F4
        self.start()
        for files, kind in (({"package-lock.json": "{}\n"}, "dependency"), ({"docs/notes.md": "n\n"}, "unclassified")):
            with self.subTest(kind=kind):
                c = self.item_call(files)
                self.assertEqual((c["type"], c["decider"]), (kind, "dorian"))
                self.assertIsNone(self.next()[0])
                gr.dorian_answers("g1", c["n"], "a", "fine, take a")
                self.assertEqual(self.next()[1]["step"], "build")

    def test_a_unanimous_council_is_kept_with_its_evidence(self):  # review F1, F4
        self.start()
        c = self.item_call({"goalmod.py": "done = False\nsafe = True\ny = 1\n"}, "Which shape?")
        gr.council_votes("g1", 1, [VOTE("gpt/gpt-6", "for", "a"), VOTE("gemini/g3", "against", "a")])
        st = gr.load("g1")                                              # survives a reload
        self.assertEqual((st["calls"][0]["status"], st["calls"][0]["choice"]), ("decided", "a"))
        self.assertEqual(self.next()[1]["step"], "build")
        rec = gr.record("g1")
        for line in ("1. Which shape? (in_envelope_code, decided by council): a",
                     "options: a, b; proposed by claude/opus, framed by gpt/gpt-6",
                     "type by code: 1 files, all inside Allowed paths", f"commits: {c['commits'][0][:12]}",
                     "vote: gpt/gpt-6 (for): a - because", "vote: gemini/g3 (against): a - because"):
            self.assertIn(line, rec)

    def test_a_split_council_waits_and_shows_its_dissent(self):  # GO-005.3
        self.start()
        self.git("switch", "-q", "-c", "build/item-1", "goal/g1")
        head = self.commit("code", {"goalmod.py": "done = False\nsafe = True\nx = 2\n"})
        self.git("switch", "-q", "main")
        c = gr.open_call(self.repo, "g1", "Which shape?", ["a", "b"], "claude/opus", "gpt/gpt-6", head, base="main")
        self.assertEqual(c["decider"], "council")
        gr.council_votes("g1", 1, [VOTE("gpt/gpt-6", "for", "a"), VOTE("gemini/g3", "against", "b")])
        self.assertIsNone(self.next()[0])
        self.assertIn("dissent: gpt/gpt-6 (for): a", gr.record("g1"))



if __name__ == "__main__":
    unittest.main()
