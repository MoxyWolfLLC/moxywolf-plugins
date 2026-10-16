"""BP-001 criteria 5 and 6: hub_term.py registers a term in hub-links and pins it in a target.

Runs on a copy of a fixture map.ts and test file. The build, test and package-manager commands are
stubbed through hub_term.run, and git runs against a local bare repository, so nothing here reaches
npm or GitHub.

ponytail: stdlib unittest, tempdirs.
"""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import hub_term  # noqa: E402
import ship  # noqa: E402

MAP = """export const SITES = {
  stigviewer: 'https://stigviewer.com',
  frontierfounder: 'https://thefrontierfounder.com',
} as const

export const HUB_LINKS: HubLink[] = [
  {
    pattern: /governed[\\s-]+autonomy/i,
    owner: 'frontierfounder',
    path: '/series/ai-governance',
  },
  // future pillar terms — one entry each
]
"""
TEST = "import assert from 'node:assert'\n\n// ---- segmentText ----\n"


def sh(cwd, *cmd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Hub:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.origin, self.path = root / "origin.git", root / "hub-links"
        sh(root, "git", "init", "-q", "--bare", "-b", "main", str(self.origin))
        sh(root, "git", "clone", "-q", str(self.origin), str(self.path))
        for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
            sh(self.path, "git", "config", k, v)
        (self.path / "src").mkdir()
        (self.path / "test").mkdir()
        (self.path / "node_modules").mkdir()
        (self.path / "src/map.ts").write_text(MAP)
        (self.path / "test/hub-links.test.ts").write_text(TEST)
        sh(self.path, "git", "add", "src", "test")
        sh(self.path, "git", "commit", "-qm", "init")
        sh(self.path, "git", "push", "-q", "origin", "HEAD:main")


class Register(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.fail_on = None
        self._run = hub_term.run

        def fake(cmd, cwd):
            self.calls.append(cmd)
            return (1, "boom") if self.fail_on and self.fail_on in cmd else (0, "ok")
        hub_term.run = fake

    def tearDown(self):
        hub_term.run = self._run

    def reg(self, h, term="auditable decision record"):
        return hub_term.register(h.path, term, "opencontrols", "https://opencontrols.ai",
                                 "/series/permission-engineering")

    def test_adds_site_entry_and_test_then_pushes(self):
        h = Hub()
        out = self.reg(h)
        src = (h.path / "src/map.ts").read_text()
        self.assertIn("  opencontrols: 'https://opencontrols.ai',\n} as const", src)
        self.assertIn("pattern: /auditable\\s+decision\\s+records?/i,", src)
        self.assertLess(src.index("auditable"), src.index("future pillar terms"))
        test = (h.path / "test/hub-links.test.ts").read_text()
        self.assertIn("assert.equal(link.href, '/series/permission-engineering')", test)
        self.assertIn("'https://opencontrols.ai/series/permission-engineering'", test)
        self.assertEqual([c[1] for c in self.calls], ["run", "test"])
        head = sh(h.path, "git", "rev-parse", "HEAD")
        self.assertIn(head, out)
        self.assertEqual(ship.remote_sha(h.path, "main"), head)

    def test_the_new_pattern_matches_the_term_and_its_plural(self):
        pat = hub_term.pattern_for("Auditable Decision Record")
        self.assertTrue(re.fullmatch(pat, "auditable decision records", re.I))
        self.assertTrue(re.fullmatch(pat, "Auditable  decision record", re.I))

    def test_existing_term_is_a_no_op(self):
        h = Hub()
        before = sh(h.path, "git", "rev-parse", "HEAD")
        self.assertEqual(self.reg(h, "governed autonomy"), "already registered")
        self.assertEqual(sh(h.path, "git", "rev-parse", "HEAD"), before)
        self.assertEqual(self.calls, [])

    def test_existing_site_is_not_added_twice(self):
        h = Hub()
        hub_term.register(h.path, "frontier founder", "frontierfounder", "https://thefrontierfounder.com",
                          "/series/the-frontier-founder")
        self.assertEqual((h.path / "src/map.ts").read_text().count("frontierfounder:"), 1)

    def test_failing_test_restores_files_and_commits_nothing(self):
        h = Hub()
        before = sh(h.path, "git", "rev-parse", "HEAD")
        self.fail_on = "test"
        with self.assertRaisesRegex(ship.Refusal, "nothing committed"):
            self.reg(h)
        self.assertEqual((h.path / "src/map.ts").read_text(), MAP)
        self.assertEqual((h.path / "test/hub-links.test.ts").read_text(), TEST)
        self.assertEqual(sh(h.path, "git", "rev-parse", "HEAD"), before)

    def test_missing_marker_refuses(self):
        h = Hub()
        (h.path / "src/map.ts").write_text(MAP.replace("  // future pillar terms — one entry each\n", ""))
        with self.assertRaisesRegex(ship.Refusal, "marker"):
            self.reg(h)


class Pin(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._run = hub_term.run
        hub_term.run = lambda cmd, cwd: (self.calls.append(cmd), (0, ""))[1]

    def tearDown(self):
        hub_term.run = self._run

    def target(self, lock, site):
        d = Path(tempfile.mkdtemp())
        (d / lock).write_text("")
        (d / "PostBody.tsx").write_text(f"rehypePlugins={{[[rehypeHubLinks, {{ site: '{site}' }}]]}}")
        return d

    def test_pnpm_pin_and_matching_site(self):
        d = self.target("pnpm-lock.yaml", "opencontrols")
        hub_term.pin(d, "opencontrols", "PostBody.tsx")
        self.assertEqual(self.calls, [["pnpm", "update", "@moxywolf/hub-links", "--lockfile-only"]])

    def test_npm_pin(self):
        d = self.target("package-lock.json", "opencontrols")
        hub_term.pin(d, "opencontrols", "PostBody.tsx")
        self.assertEqual(self.calls[0][:2], ["npm", "update"])

    def test_wrong_site_refuses_naming_both_and_leaves_the_file(self):
        d = self.target("pnpm-lock.yaml", "frontierfounder")
        with self.assertRaisesRegex(ship.Refusal, r"\['frontierfounder'\].*'opencontrols'"):
            hub_term.pin(d, "opencontrols", "PostBody.tsx")
        self.assertIn("'frontierfounder'", (d / "PostBody.tsx").read_text())

    def test_no_lockfile_refuses(self):
        d = Path(tempfile.mkdtemp())
        with self.assertRaisesRegex(ship.Refusal, "no pnpm-lock"):
            hub_term.pin(d, "opencontrols", "x")


if __name__ == "__main__":
    unittest.main()
