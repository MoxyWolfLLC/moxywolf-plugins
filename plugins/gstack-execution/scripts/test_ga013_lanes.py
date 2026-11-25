"""GA-013 part A: one policy table. The table is checked before it decides anything, the closed lane
covers how git reads the tree and the table itself, symlinks and submodules close the lane, an observe
lane decides nothing, and CODEOWNERS is generated from the table."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import codeowners  # noqa: E402
import peer_review as pr  # noqa: E402

DEFAULT = json.loads(pr.LANE_TABLE_DEFAULT.read_text(encoding="utf-8"))
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=ENV).stdout.strip()


REPOS = []


def tearDownModule():
    for r in REPOS:
        r.tmp.cleanup()


class Repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        REPOS.append(self)
        self.path = Path(self.tmp.name)
        git(self.path, "init", "-q", "-b", "main")
        (self.path / "README.md").write_text("x\n")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "base")
        self.base = git(self.path, "rev-parse", "HEAD")

    def commit(self):
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "change")
        return git(self.path, "rev-parse", "HEAD")

    def lane(self, head):
        return pr.release_lane([{"path": str(self.path), "base": self.base, "head": head}])


def refused(t, default=None):
    try:
        pr.check_lane_table(t, "t", default)
    except pr.ReviewError as e:
        return str(e)
    return ""


class TableCheck(unittest.TestCase):
    def test_the_default_passes(self):
        self.assertEqual(refused(DEFAULT), "")

    def test_an_unknown_key_is_refused_by_name(self):
        for where, t in (("top", {**DEFAULT, "ownd": []}),
                         ("lane", {**DEFAULT, "lanes": {**DEFAULT["lanes"], "wide": {**DEFAULT["lanes"]["wide"], "pathz": []}}})):
            with self.subTest(where):
                self.assertIn("unknown key", refused(t))

    def test_a_rule_without_a_purpose_is_refused(self):
        t = copy.deepcopy(DEFAULT)
        del t["lanes"]["wide"]["purpose"]
        self.assertIn("lane wide has no purpose", refused(t))
        t = copy.deepcopy(DEFAULT)
        t["owned"][0]["purpose"] = " "
        self.assertIn("owned[0] has no purpose", refused(t))

    def test_an_owned_rule_has_no_mode(self):
        t = copy.deepcopy(DEFAULT)
        t["owned"][0]["mode"] = "observe"
        self.assertIn("unknown key 'mode' in owned[0]", refused(t))

    def test_a_repository_table_keeps_every_default_closed_path_and_effect(self):
        for key, drop in (("paths", "**/migrations/**"), ("paths", "**/.gitattributes"), ("effects", "adds_symlink")):
            with self.subTest(drop):
                t = copy.deepcopy(DEFAULT)
                t["lanes"]["closed"][key].remove(drop)
                self.assertIn(f"drops the default closed {key}", refused(t, DEFAULT))

    def test_a_repository_table_may_not_observe_the_closed_lane_but_may_add_paths(self):
        t = copy.deepcopy(DEFAULT)
        t["lanes"]["closed"]["mode"] = "observe"
        self.assertIn("sets the closed lane to observe", refused(t, DEFAULT))
        t = copy.deepcopy(DEFAULT)
        t["lanes"]["closed"]["paths"].append("docs/db/**")
        self.assertEqual(refused(t, DEFAULT), "")


class Lanes(unittest.TestCase):
    def test_each_new_closed_path_resolves_closed(self):
        for name in (".gitattributes", ".gitmodules", "sub/.gitattributes", ".gstack/release-lanes.json",
                     "plugins/gstack-execution/skills/gstack-execution/references/release-lanes.json"):
            with self.subTest(name):
                r = Repo()
                p = r.path / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(DEFAULT) if name.endswith(".json") else "* text=auto\n")
                self.assertEqual(r.lane(r.commit())["lane"], "closed")

    def test_a_new_symlink_closes_the_lane(self):
        r = Repo()
        os.symlink("README.md", r.path / "link")
        got = r.lane(r.commit())
        self.assertEqual(got["lane"], "closed")
        self.assertIn("adds_symlink", [m.get("effect") for m in got["matched"]])

    def test_a_submodule_pointer_closes_the_lane(self):
        r = Repo()
        git(r.path, "update-index", "--add", "--cacheinfo", f"160000,{r.base},vendor/sub")
        git(r.path, "commit", "-q", "-m", "submodule")
        got = r.lane(git(r.path, "rev-parse", "HEAD"))
        self.assertEqual(got["lane"], "closed")
        self.assertIn("changes_submodule", [m.get("effect") for m in got["matched"]])

    def test_an_ordinary_file_stays_contained(self):
        r = Repo()
        (r.path / "app.txt").write_text("y\n")
        got = r.lane(r.commit())
        self.assertEqual(got["lane"], "contained")
        self.assertNotIn("would_lane", got)

    def test_an_observe_lane_is_recorded_and_decides_nothing(self):
        r = Repo()
        t = copy.deepcopy(DEFAULT)
        t["lanes"]["wide"]["mode"] = "observe"
        (r.path / ".gstack").mkdir()
        (r.path / "lib").mkdir()
        (r.path / "lib" / "x.py").write_text("y = 1\n")
        r.commit()
        r.base = git(r.path, "rev-parse", "HEAD")
        (r.path / ".gstack" / "release-lanes.json").write_text(json.dumps(t))
        r.base = r.commit()   # the table is in place before the change under review
        (r.path / "lib" / "x.py").write_text("y = 2\n")
        got = r.lane(r.commit())
        self.assertEqual(got["lane"], "contained")
        self.assertEqual(got["would_lane"], "wide")


class CodeOwners(unittest.TestCase):
    def test_check_passes_on_a_generated_file_and_fails_on_a_hand_edit(self):
        r = Repo()
        (r.path / ".github").mkdir()
        self.assertEqual(codeowners.main(["generate", "--repo", str(r.path)]), 0)
        self.assertEqual(codeowners.main(["check", "--repo", str(r.path)]), 0)
        f = r.path / ".github" / "CODEOWNERS"
        f.write_text(f.read_text() + "/extra.py @someone\n")
        self.assertEqual(codeowners.main(["check", "--repo", str(r.path)]), 1)

    def test_the_generated_file_is_todays_rules_plus_the_four_new_paths(self):
        rules = codeowners.rules(codeowners.render(DEFAULT))
        new = [(p, ("@dorianatmoxywolf",)) for p in (".gitattributes", ".gitmodules", "/.gstack/release-lanes.json",
               "/plugins/gstack-execution/skills/gstack-execution/references/release-lanes.json")]
        self.assertEqual(rules[-4:], new)
        self.assertIn(("/goals/*--s1/", ()), rules)


if __name__ == "__main__":
    unittest.main()
