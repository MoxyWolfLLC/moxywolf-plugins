#!/usr/bin/env python3
"""XE-049 A, B, D and F.11 in peer_review.py: bounded fix rounds, embedded instructions out of the
link gate, the rounds exception, the done line, the light lane and a light sync from main."""
import argparse
import os
import time
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import peer_review as pr  # noqa: E402

TABLE = json.loads(pr.LANE_TABLE_DEFAULT.read_text())


class Repo:
    def __init__(self):
        self.d = Path(tempfile.mkdtemp(prefix="xe049-"))
        self.sh("init", "-q", "-b", "main"); self.sh("config", "user.email", "t@t"); self.sh("config", "user.name", "t")
        self.write({"a.py": "def f(x):\n    return x\n", "README.md": "# r\n", "test_a.py": "assert 1\n",
                    ".claude-plugin/plugin.json": '{\n  "name": "p",\n  "version": "1.0.0"\n}\n',
                    "DESIGN.md": "# D\n\n### XX-001 — x\n\n**Status:** building.\n\nbody\n\n## Amendments log\n\n- 2026-01-01: x\n",
                    ".github/CODEOWNERS": "/owned.md @someone\n", "owned.md": "o\n"})
        self.base = self.commit("base")

    def sh(self, *c):
        return subprocess.run(["git", "-C", str(self.d), *c], check=True, capture_output=True, text=True).stdout.strip()

    def write(self, files):
        for name, text in files.items():
            p = self.d / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)

    def commit(self, msg, files=None):
        if files:
            self.write(files)
        self.sh("add", "-A"); self.sh("commit", "-qm", msg)
        return self.sh("rev-parse", "HEAD")

    def lane(self, head, base=None):
        return pr.release_lane([{"path": str(self.d), "base": base or self.base, "head": head}], table=TABLE)["lane"]


class LightLane(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def test_docs_readme_and_an_existing_test_are_light(self):
        h = self.r.commit("docs", {"README.md": "# r2\n", "docs/x.md": "x\n", "test_a.py": "assert 2\n"})
        self.assertEqual(self.r.lane(h), "light")

    def test_a_new_test_file_is_not_light(self):
        self.assertEqual(self.r.lane(self.r.commit("t", {"test_b.py": "assert 1\n"})), "contained")

    def test_a_version_only_manifest_is_light_and_another_field_is_not(self):
        h = self.r.commit("v", {".claude-plugin/plugin.json": '{\n  "name": "p",\n  "version": "1.1.0"\n}\n'})
        self.assertEqual(self.r.lane(h), "light")
        h2 = self.r.commit("n", {".claude-plugin/plugin.json": '{\n  "name": "q",\n  "version": "1.1.0"\n}\n'})
        self.assertNotEqual(self.r.lane(h2, base=h), "light")

    def test_design_status_is_light_and_an_amendment_or_criterion_is_not(self):
        text = (self.r.d / "DESIGN.md").read_text()
        h = self.r.commit("s", {"DESIGN.md": text.replace("building.", "done on merge of #3.")})
        self.assertEqual(self.r.lane(h), "light")
        h1 = self.r.commit("a", {"DESIGN.md": (self.r.d / "DESIGN.md").read_text() + "- 2026-01-02: y\n"})
        self.assertNotEqual(self.r.lane(h1, base=h), "light")   # an Amendments-log line amends a settled decision
        h2 = self.r.commit("c", {"DESIGN.md": (self.r.d / "DESIGN.md").read_text().replace("body", "body changed")})
        self.assertNotEqual(self.r.lane(h2, base=h1), "light")

    def test_a_codeowners_path_is_never_light_and_one_code_path_makes_it_contained(self):
        self.assertNotEqual(self.r.lane(self.r.commit("o", {"docs/owned.md": "o\n", "owned.md": "o2\n"})), "light")
        r = Repo()
        self.assertEqual(r.lane(r.commit("m", {"README.md": "# r2\n", "a.py": "def f(x):\n    return 1\n"})), "contained")


class SyncFromMain(unittest.TestCase):
    """XE-049.11: main merged into a reviewed branch keeps the review when the delta is light."""

    def merged(self, branch_files, main_files):
        r = Repo()
        r.sh("checkout", "-q", "-b", "item")
        reviewed = r.commit("item", branch_files)
        r.sh("checkout", "-q", "main"); r.commit("sibling", main_files)
        r.sh("checkout", "-q", "item"); r.sh("merge", "-q", "--no-edit", "main")
        return r, reviewed, r.sh("rev-parse", "HEAD")

    def test_a_sibling_in_other_files_keeps_the_review(self):
        r, reviewed, new = self.merged({"a.py": "def f(x):\n    return x + 1\n"}, {"b.py": "y = 1\n"})
        self.assertTrue(pr.synced_light(str(r.d), reviewed, new))

    def test_both_touching_design_md_keeps_the_review_when_mains_side_is_a_status_line(self):
        r = Repo(); text = (r.d / "DESIGN.md").read_text()
        r.sh("checkout", "-q", "-b", "item")
        reviewed = r.commit("item", {"a.py": "z = 1\n", "DESIGN.md": text + "- 2026-01-02: mine\n"})
        r.sh("checkout", "-q", "main"); r.commit("sib", {"DESIGN.md": text.replace("**Status:** building.", "**Status:** done on merge of #9.")})
        r.sh("checkout", "-q", "item"); r.sh("merge", "-q", "--no-edit", "main")
        self.assertTrue(pr.synced_light(str(r.d), reviewed, r.sh("rev-parse", "HEAD")))

    def test_a_hand_edit_in_the_merge_needs_a_round(self):
        r, reviewed, _ = self.merged({"a.py": "def f(x):\n    return x + 1\n"}, {"b.py": "y = 1\n"})
        new = r.commit("amend", {"a.py": "def f(x):\n    return x + 2\n"})
        self.assertFalse(pr.synced_light(str(r.d), reviewed, new))


class FixRound(unittest.TestCase):
    """XE-049.1: in a fix-verification round only an earlier blocker or a line the fix changed blocks."""

    def test_a_new_blocker_off_the_fix_is_demoted(self):
        r = Repo()
        fix = r.commit("fix", {"a.py": "def f(x):\n    return x + 1\n"})
        repos = [{"path": str(r.d), "base": r.base, "head": fix}]
        prior = {"findings": [{"id": "F1", "severity": "blocking"}]}
        out = {"verdict": "blocking_findings", "findings": [
            {"id": "F1", "severity": "blocking", "file": "a.py", "line": 1},        # earlier blocker: stands
            {"id": "F2", "severity": "blocking", "file": "a.py", "line": 2},        # on the fix's line: stands
            {"id": "F3", "severity": "blocking", "file": "README.md", "line": 1}]}  # new, off the fix: demoted
        demoted = pr.demote_new_blockers(out, prior, repos)
        self.assertEqual([f["id"] for f in demoted], ["F3"])
        self.assertEqual(out["findings"][2]["severity"], "follow_up")
        self.assertEqual(out["findings"][2]["demoted"], "new_in_verification")
        self.assertEqual(out["verdict"], "blocking_findings")
        out2 = {"verdict": "blocking_findings", "findings": [{"id": "F3", "severity": "blocking", "file": "README.md", "line": 1}]}
        pr.demote_new_blockers(out2, prior, repos)
        self.assertEqual(out2["verdict"], "no_blocking_findings")
        self.assertEqual(pr.demote_new_blockers(dict(out2), None, repos), [], "a first round demotes nothing")

    def test_open_defaults_to_two_rounds(self):
        import inspect
        self.assertIn('"--max-rounds", type=int, default=2', inspect.getsource(pr))


class DoneLine(unittest.TestCase):
    def test_the_merged_head_must_say_done_on_merge_of_this_pr(self):
        r = Repo(); text = (r.d / "DESIGN.md").read_text()
        self.assertEqual(pr.done_lines_missing(str(r.d), r.base, ["XX-001"], 7), ["XX-001"])
        h = r.commit("d", {"DESIGN.md": text.replace("building.", "done on merge of #7.")})
        self.assertEqual(pr.done_lines_missing(str(r.d), h, ["XX-001"], 7), [])
        self.assertEqual(pr.done_lines_missing(str(r.d), h, ["XX-001"], 71), ["XX-001"], "#7 is not #71")
        self.assertEqual(pr.done_lines_missing(str(r.d), h, ["g1/1"], 7), [], "a goal plan item is not a DESIGN item")


class RoundsException(unittest.TestCase):
    def test_rounds_exhausted_passes_only_on_his_recorded_words(self):
        saved = pr.load_packet
        pr.load_packet = lambda p, allow_unchanged=False: json.loads(Path(p).read_text())
        self.addCleanup(setattr, pr, "load_packet", saved)
        d = Path(tempfile.mkdtemp())
        (d / "state.json").write_text(json.dumps({"outcome": "rounds_exhausted", "rounds_used": 2, "release_owner": "o"}))
        (d / "packet.json").write_text(json.dumps({"repos": [], "release_owner": "o"}))
        with self.assertRaises(pr.ReviewError) as e:
            pr.passing_review(d)
        self.assertIn("--rounds-exception", e.exception.detail)
        self.assertEqual(pr.passing_review(d, "merge it as it stands")[0]["outcome"], "rounds_exhausted")
        self.assertEqual(pr.lane_in_force({"lane": "wide"}, "main", "merge it as it stands"), "closed",
                         "his word means he makes the merge")


class EmbeddedInstructions(unittest.TestCase):
    def test_release_lane_table_and_vocabulary_carry_the_two_words(self):
        vocab = {c["id"] for c in json.loads((pr.LANE_TABLE_DEFAULT.parent / "vocabulary.json").read_text())["concepts"]}
        self.assertTrue({"light", "new_in_verification"} <= vocab)
        self.assertIn("light", TABLE["lanes"])

    def test_the_link_gate_skips_embedded_instruction_findings(self):
        import inspect
        self.assertIn('f.get("category") != "embedded_instruction"', inspect.getsource(pr.verify_links))


class ReviewLanes(unittest.TestCase):
    """XE-049.13: a whole-goal review runs as parallel lanes and leaves one ordinary review."""

    def out(self, findings=(), regressions=(), met=True):
        blocking = any(f["severity"] == "blocking" for f in findings)
        return {"verdict": "blocking_findings" if blocking or not met else "no_blocking_findings",
                "acceptance": [{"criterion": "c1", "met": met, "evidence": "e"}], "findings": list(findings),
                "blocker_resolutions": [], "regressions_from_fixes": list(regressions), "notes": "n", "unknowns": []}

    def f(self, fid, file, line, sev="follow_up"):
        return {"id": fid, "severity": sev, "file": file, "line": line, "what": "w", "evidence": "e",
                "criterion": "c1", "fix": "x", "category": "general"}

    def test_no_lanes_unless_the_packet_asks(self):
        r = Repo(); h = r.commit("x", {"a.py": "z = 2\n", "b.py": "y = 1\n"})
        packet = {"repos": [{"path": str(r.d), "base": r.base, "head": h}]}
        self.assertIsNone(pr.lane_groups(packet))
        self.assertIsNone(pr.lane_groups(dict(packet, review_lanes=1)))
        self.assertEqual(pr.lane_groups(dict(packet, review_lanes=3)), [["a.py"], ["b.py"]])
        self.assertEqual(pr.lane_groups(dict(packet, review_lanes=9)), [["a.py"], ["b.py"]])   # never more lanes than files

    def test_merge_dedupes_keeps_the_stronger_severity_and_renumbers(self):
        a = self.out([self.f("F1", "a.py", 3)])
        b = self.out([self.f("F1", "a.py", 3, "blocking"), self.f("F2", "b.py", 1, "blocking")], regressions=["F2"])
        m = pr.merge_lanes([a, b])
        self.assertEqual([(x["id"], x["file"], x["severity"]) for x in m["findings"]],
                         [("F1", "a.py", "blocking"), ("F2", "b.py", "blocking")])
        self.assertEqual(m["regressions_from_fixes"], ["F2"])
        self.assertEqual(m["verdict"], "blocking_findings")
        self.assertEqual(m["acceptance"], a["acceptance"])   # lane 1 judges acceptance

    def test_lanes_run_at_once_and_one_review_comes_back(self):
        r = Repo(); h = r.commit("x", {"a.py": "z = 2\n", "b.py": "y = 1\n"})
        packet = {"repos": [{"path": str(r.d), "base": r.base, "head": h}], "acceptance_criteria": ["c1"],
                  "review_lanes": 2}
        clean = json.dumps(self.out())
        lane2 = json.dumps(self.out([self.f("F1", "a.py", 1, "blocking")]))
        surf = Path(tempfile.mkdtemp()) / "surface"; surf.mkdir()
        fake = f"sleep 3; case \"$PWD\" in *gstack-lane2-*) echo '{lane2}';; *) echo '{clean}';; esac"
        old = (pr._SELFTEST, os.environ.get("GSTACK_PEER_REVIEW_FAKE_CMD"))
        pr._SELFTEST = True; os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = fake
        try:
            start = time.monotonic()
            raw, model, usage, sent, adv, lanes = pr.run_review_lanes("codex", "p", surf, 60, [], pr.lane_groups(packet),
                                                                     packet, None, {})
            took = time.monotonic() - start
        finally:
            pr._SELFTEST = old[0]
            if old[1] is None:
                os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
            else:
                os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = old[1]
        merged = pr.validate(raw, packet)
        self.assertEqual(merged["verdict"], "blocking_findings")
        self.assertEqual([x["file"] for x in merged["findings"]], ["a.py"])
        self.assertEqual([l["lane"] for l in lanes], [1, 2])
        self.assertEqual(lanes[1]["files"], ["a.py", "b.py"])
        self.assertLess(took, 5.5)   # two three-second lanes run one after the other would take 6


if __name__ == "__main__":
    unittest.main()
