#!/usr/bin/env python3
"""XE-035 acceptance: a file a criterion names reaches the reviewer before anything the change
merely mentions.

CS-001's second review is the case. Its criteria named nine files. The surface on disk carried 25
callers and 25 mentioned files, the api reviewer was sent the callers, and it was sent neither
DESIGN.md nor anything under dependencies/, which is where the criterion-named files sat.
"""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr

API = "openrouter-gpt"
LINE = "x" * 99 + "\n"                                        # 100 characters
NAMED = [f"plugins/p{i}/check{i}.py" for i in range(9)]       # CS-001 named nine
MENTIONED = [f"docs/mentioned{i:02}.md" for i in range(30)]   # more than the 25-file cap
PRE = "0-plugins-repo/"
DESIGN, MARKET = f"changed/{PRE}DESIGN.md", f"changed/{PRE}.claude-plugin/marketplace.json"


class CriterionFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="xe035-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "plugins-repo"; self.repo.mkdir()
        self.sh("init", "-q"); self.sh("config", "user.email", "t@t"); self.sh("config", "user.name", "t")
        # a large DESIGN.md that mentions 30 files, and a 47,000-character marketplace.json
        self.write("DESIGN.md", "status: planned\n" + " ".join(MENTIONED) + "\n" + LINE * 3300)
        self.write(".claude-plugin/marketplace.json", "a" * 99 + "\n" + LINE * 469)
        for i, n in enumerate(NAMED):                         # three of the nine would also be callers
            self.write(n, ("import marketplace\n" if i < 3 else "") + LINE * 100)
        for n in MENTIONED:
            self.write(n, "m\n")
        for i in range(30):
            self.write(f"tools/caller{i:02}.py", "import marketplace\n" + LINE * 120)
        self.write("docs/huge.txt", LINE * 4100)              # larger than the api cap on its own
        self.sh("add", "."); self.sh("commit", "-qm", "base")
        self.base = self.sh("rev-parse", "HEAD")
        self.write("DESIGN.md", "status: building\n" + " ".join(MENTIONED) + "\n" + LINE * 3300)
        self.write(".claude-plugin/marketplace.json", "b" * 99 + "\n" + LINE * 469)
        self.sh("commit", "-qam", "head")
        self.repos = [{"path": str(self.repo), "base": self.base, "head": self.sh("rev-parse", "HEAD")}]
        self.criteria = [f"`{n}` passes." for n in NAMED]
        self.named = [f"dependencies/{PRE}{n}" for n in NAMED]

    def sh(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()

    def write(self, rel, text):
        f = self.repo / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text)

    def surface(self, criteria, **kw):
        out = self.tmp / f"out-{len(list(self.tmp.iterdir()))}"; out.mkdir()
        return pr.build_surface(self.repos, out, criteria=criteria, **kw)

    def sent(self, criteria):
        surf, stats = self.surface(criteria)
        text, sent = pr.surface_as_text(API, surf, stats["criterion_files"])
        return text, {e["path"]: e for e in sent}

    # ---- criterion 1 ----
    def test_named_files_sit_outside_the_cap_and_take_no_caller_slot(self):
        surf, stats = self.surface(self.criteria)
        self.assertEqual(stats["criterion_files"], self.named)
        for p in self.named:
            self.assertTrue((surf / p).exists(), p)
        self.assertEqual(list((surf / "callers").rglob("check*.py")), [], "a named file took a caller slot")
        self.assertEqual((stats["callers"], stats["callers_withheld"]), (25, 5))
        # 30 files DESIGN.md merely mentions: 25 fit the cap, 5 are withheld, and the nine named are on top
        self.assertEqual((stats["dependencies"], stats["dependencies_withheld"]), (9 + 25, 5))
        self.assertIn("names by path: 9, all here and outside the cap", (surf / "SURFACE.md").read_text())

    def test_a_cap_of_one_still_carries_all_nine(self):
        surf, stats = self.surface(self.criteria, cap=1)
        self.assertEqual(stats["criterion_files"], self.named)
        self.assertEqual((stats["dependencies"], stats["dependencies_withheld"]), (9 + 1, 29))

    def test_named_files_are_sent_before_any_caller(self):
        text, by = self.sent(self.criteria)
        callers = [p for p, e in by.items() if p.startswith("callers/") and e["sent"]]
        self.assertTrue(callers)
        self.assertLess(max(text.index(f"=== {p} ===") for p in self.named),
                        min(text.index(f"=== {p} ===") for p in callers))

    # ---- criteria 2 and 4: CS-001's shape ----
    def test_cs001_shape_sends_all_nine_and_the_manifest_names_each(self):
        text, by = self.sent(self.criteria)
        for p in self.named:
            self.assertEqual((by[p]["sent"], by[p].get("criterion_named")), (True, True), p)
            self.assertIn(f"=== {p} ===\n", text)
        # DESIGN.md is over the threshold and not named, so it goes as its hunks and the manifest says so
        self.assertEqual((by[DESIGN]["sent"], by[DESIGN]["as"]), (True, "diff_hunks"))
        self.assertGreater(by[DESIGN]["whole_chars"], 330_000)
        self.assertLess(by[DESIGN]["chars"], 1_000)
        self.assertIn("+status: building", text, "the hunks the manifest points at are in CHANGE.diff")
        # only as many files give way as the named ones need: marketplace.json still goes whole
        self.assertEqual((by[MARKET]["sent"], by[MARKET]["chars"], "as" in by[MARKET]), (True, 47_000, False))
        self.assertLessEqual(sum(e["chars"] for e in by.values() if e["sent"]), pr.API_SURFACE_CAP)
        unsent = [e for e in by.values() if not e["sent"]]
        self.assertTrue(unsent and all(e["path"].startswith("callers/") and e["why"] for e in unsent), unsent)

    def test_a_large_changed_file_goes_whole_when_no_named_file_needs_the_room(self):
        _, by = self.sent(["the build passes"])
        self.assertEqual([p for p, e in by.items() if "as" in e or e.get("criterion_named")], [])
        self.assertEqual((by[DESIGN]["sent"], by[DESIGN]["chars"] > 330_000), (True, True))

    def test_a_named_changed_file_stays_whole_and_another_gives_way(self):
        _, by = self.sent(["`DESIGN.md` records the status."] + self.criteria[:3])
        self.assertEqual((by[DESIGN]["sent"], by[DESIGN].get("criterion_named"), "as" in by[DESIGN]), (True, True, False))
        self.assertEqual(by[MARKET].get("as"), "diff_hunks")
        self.assertTrue(all(by[p]["sent"] for p in self.named[:3]))

    # ---- criterion 3 ----
    HUGE = ["`docs/huge.txt` is unchanged."]

    def test_a_named_file_that_cannot_fit_is_unusable_and_named(self):
        surf, stats = self.surface(self.criteria + self.HUGE)   # on disk it is all there: a cli reviewer has no cap
        self.assertTrue((surf / f"dependencies/{PRE}docs/huge.txt").exists())
        with self.assertRaises(pr.ReviewError) as cm:
            pr.surface_as_text(API, surf, stats["criterion_files"])
        self.assertEqual(cm.exception.outcome, "unusable")
        self.assertIn("docs/huge.txt", cm.exception.detail)

    def test_a_named_file_that_cannot_be_read_is_unusable_and_named(self):
        (self.repo / NAMED[4]).unlink()                          # tracked, and gone from the checkout
        with self.assertRaises(pr.ReviewError) as cm:
            self.surface(self.criteria)
        self.assertEqual(cm.exception.outcome, "unusable")
        self.assertIn(NAMED[4], cm.exception.detail)

    def open(self, criteria, reviewer=None):
        """`peer_review.py open` through main(), as the build loop runs it. Returns (exit, state)."""
        pk = {"outcome": "o", "acceptance_criteria": criteria, "repos": self.repos, "changed_behavior": "b",
              "exclusions": [], "tests": {}, "release_owner": "dorianatmoxywolf"}
        f = self.tmp / "packet.json"; f.write_text(json.dumps(pk))
        root = Path(tempfile.mkdtemp(prefix="reviews-", dir=self.tmp))
        env = {k: v for k, v in os.environ.items() if k != "GSTACK_REVIEWER"} | ({"GSTACK_REVIEWER": reviewer} if reviewer else {})
        code = None
        with mock.patch.object(pr, "REVIEW_DIR", root), mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(sys, "argv", ["peer_review.py", "open", "--builder", "claude", "--packet", str(f)]), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                pr.main()
            except SystemExit as e:
                code = e.code
        states = list(root.glob("*/state.json"))
        return code, (json.loads(states[0].read_text()) if states else None), root

    def test_the_review_opens_as_unusable_and_takes_no_round(self):
        code, state, root = self.open(self.criteria + self.HUGE, reviewer=API)
        self.assertTrue(str(code).startswith("unusable: ") and "docs/huge.txt" in str(code), code)
        self.assertEqual(state["outcome"], "unusable")
        self.assertIn("docs/huge.txt", state["error"])
        with mock.patch.object(pr, "REVIEW_DIR", root), self.assertRaises(pr.ReviewError) as cm:
            pr.cmd_round(mock.Mock(review_id=state["review_id"], head=[], ci_run=[]))
        self.assertEqual(cm.exception.outcome, "review_closed")

    def test_the_same_packet_opens_for_a_reviewer_that_reads_the_surface_from_disk(self):
        code, state, _ = self.open(self.criteria + self.HUGE)   # claude builds, so codex is the intended reviewer
        self.assertEqual((code, state["outcome"], state["reviewer"]), (None, "opened", "codex"))

    def test_an_unreadable_named_file_opens_as_unusable_for_any_reviewer(self):
        (self.repo / NAMED[4]).unlink()
        code, state, _ = self.open(self.criteria)
        self.assertEqual(state["outcome"], "unusable")
        self.assertIn(NAMED[4], state["error"])
        self.assertTrue(str(code).startswith("unusable: "))


if __name__ == "__main__":
    unittest.main()
