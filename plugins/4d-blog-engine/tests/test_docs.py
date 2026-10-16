"""BP-001 criteria 7 and 8: the skills ship, the writer never pushes, and wired targets say how.

ponytail: reads the files as text; the scripts' behaviour is in test_ship.py and test_hub_term.py.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted(ROOT.glob("skills/*/SKILL.md")) + sorted(ROOT.glob("commands/*.md"))


def text(rel):
    return (ROOT / rel).read_text()


class NoManualPush(unittest.TestCase):
    def test_found_the_docs(self):
        self.assertGreater(len(DOCS), 10)

    def test_no_manual_push_anywhere(self):
        manual = re.compile(r"Push origin|Push button|click\s+Push|GitHub Desktop to (deploy|push|publish)"
                            r"|(writer|you|Dorian)\s+(then\s+)?push(es)?\b", re.I)
        hits = [f"{p.relative_to(ROOT)}: {m.group(0)}" for p in DOCS for m in manual.finditer(p.read_text())]
        self.assertEqual(hits, [])

    def test_no_unsigned_override(self):
        s = text("skills/blog-publish/SKILL.md") + text("commands/blog-publish.md")
        self.assertNotIn("--force", s)



class NamesItsScripts(unittest.TestCase):
    def test_blog_publish_ships_and_pins(self):
        s = text("skills/blog-publish/SKILL.md")
        for needle in ("ship.py\" push", "ship.py\" merge", "ship.py\" verify-live", "hub_term.py\" pin"):
            self.assertIn(needle, s)

    def test_term_registration_runs_the_script(self):
        for rel in ("skills/4d-blog-engine/SKILL.md", "commands/blog-pillar.md", "commands/blog-term.md"):
            self.assertIn("hub_term.py\" register", text(rel), rel)
            self.assertNotIn("rebuild + tag", text(rel), rel)


FAKE_SHIP = """import json, os, subprocess, sys
with open(os.environ["SHIP_LOG"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1] == "push":
    repo = sys.argv[sys.argv.index("--repo") + 1]
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"pushed b: remote == local == {head}")
    subprocess.run(["git", "-C", repo, "commit", "-q", "--allow-empty", "-m", "moved after push"], check=True)
"""


class ShipBlockRuns(unittest.TestCase):
    """Runs the blog-publish ship block itself, with ship.py faked, so the workflow is what's tested."""

    def run_block(self, protected):
        skill = text("skills/blog-publish/SKILL.md")
        block = re.search(r"\*\*Then ship it\*\*.*?```bash\n(.*?)```", skill, re.S).group(1)
        block = block.replace('"<default_branch_protected>"', "true" if protected else "false")
        d = Path(tempfile.mkdtemp())
        (d / "scripts").mkdir()
        (d / "scripts/ship.py").write_text(FAKE_SHIP)
        repo = d / "repo"
        for cmd in (["git", "init", "-q", "-b", "publish/x", str(repo)],
                    ["git", "-C", str(repo), "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-q",
                     "--allow-empty", "-m", "post"]):
            subprocess.run(cmd, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@e"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
        pushed = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        env = {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"], "SHIP_LOG": str(d / "log"),
               "CLAUDE_PLUGIN_ROOT": str(d), "PUBLISHING_REPO_DIR": str(repo), "PIECE_DIR": str(d),
               "HOME": str(d)}
        r = subprocess.run(["bash", "-c", block], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return pushed, [json.loads(line) for line in (d / "log").read_text().splitlines()]

    def test_protected_merges_the_pushed_sha_after_the_branch_moves(self):
        pushed, calls = self.run_block(True)
        self.assertEqual([c[0] for c in calls], ["push", "merge", "verify-live"])
        self.assertNotIn("--state", calls[0])
        self.assertEqual(calls[1][calls[1].index("--head") + 1], pushed)
        self.assertIn("--state", calls[1])

    def test_unprotected_push_records_state_and_never_merges(self):
        _, calls = self.run_block(False)
        self.assertEqual([c[0] for c in calls], ["push", "verify-live"])
        self.assertIn("--state", calls[0])


class WiredTargets(unittest.TestCase):
    def test_wired_targets_carry_the_shipping_fields(self):
        fms = {p.name: m.group(1) for p in sorted((ROOT / "targets").glob("*.md"))
               if (m := re.match(r"---\n(.*?)\n---", p.read_text(), re.S))}
        wired = [n for n, fm in fms.items() if re.search(r"^status: wired\b", fm, re.M)]
        self.assertGreaterEqual(len(wired), 2)
        for name in wired:
            fm = fms[name]
            for field in ("default_branch_protected:", "required_checks:", "auto_linker_file:"):
                self.assertIn(field, fm, f"{name} lacks {field}")


if __name__ == "__main__":
    unittest.main()
