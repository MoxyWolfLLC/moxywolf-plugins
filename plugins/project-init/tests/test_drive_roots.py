"""SM-012: each Mac finds its own Drive roots, and project-init names two roots by tail, never Taskade.

Criterion 6: drive_roots.py over a fake CloudStorage, plus a text scan of criterion 1's files. The scan
fails when it examines nothing (EV-001).
"""
import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("drive_roots", PLUGIN / "scripts" / "drive_roots.py")
dr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dr)

HOMES = [
    "skills/session-start/SKILL.md", "skills/session-end/SKILL.md", "skills/project-init/SKILL.md",
    "commands/session-start.md", "commands/session-end.md", "commands/init-project.md",
    "commands/refresh-project-instructions.md",
]
ABS_DRIVE = re.compile(r"/Users/[^/`\s]+/Library/CloudStorage/GoogleDrive-")


def make(cloud, name, both=True, index=False):
    acct = cloud / name
    (acct / "My Drive").mkdir(parents=True)
    if both:
        (acct / dr.GITHUB).mkdir(parents=True)
        (acct / dr.VAULT).mkdir(parents=True)
    if index:
        f = acct / "Shared drives" / dr.INDEX
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# index\n")
    return acct


class Resolve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cloud = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_picks_the_plain_folder_over_gtemp_and_a_copy_without_index(self):
        plain = make(self.cloud, "GoogleDrive-dorianc@moxywolf.com", index=True)
        make(self.cloud, "GoogleDrive-dorianc%moxywolf.com@gtempaccount.com", both=False)
        make(self.cloud, "GoogleDrive-dorianc@moxywolf.com-107552934203480843396")
        out = dr.resolve(self.cloud)
        self.assertEqual(out, {"status": "ok", "github": str(plain / dr.GITHUB), "vault": str(plain / dr.VAULT)})

    def test_gtempaccount_is_skipped_even_when_it_holds_shared_drives(self):
        plain = make(self.cloud, "GoogleDrive-dorianc@moxywolf.com", index=True)
        make(self.cloud, "GoogleDrive-dorianc%moxywolf.com@gtempaccount.com", index=True)
        self.assertEqual(dr.resolve(self.cloud)["github"], str(plain / dr.GITHUB))
        shutil.rmtree(plain / dr.GITHUB)
        self.assertEqual(dr.resolve(self.cloud)["status"], "not_found")

    def test_two_with_index_is_ambiguous(self):
        make(self.cloud, "GoogleDrive-a@x.com", index=True)
        make(self.cloud, "GoogleDrive-a@x.com-1", index=True)
        out = dr.resolve(self.cloud)
        self.assertEqual(out["status"], "ambiguous")
        self.assertEqual(len(out["candidates"]), 2)

    def test_two_without_index_is_ambiguous_not_a_guess(self):
        make(self.cloud, "GoogleDrive-a@x.com")
        make(self.cloud, "GoogleDrive-a@x.com-1")
        self.assertEqual(dr.resolve(self.cloud)["status"], "ambiguous")

    def test_none_is_not_found_with_a_reason(self):
        make(self.cloud, "GoogleDrive-a@x.com", both=False)
        out = dr.resolve(self.cloud)
        self.assertEqual(out["status"], "not_found")
        self.assertIn("GoogleDrive-a@x.com", out["reason"])


class Homes(unittest.TestCase):
    def test_no_home_names_an_absolute_drive_path_or_taskade(self):
        examined, hits = 0, []
        for h in HOMES:
            text = (PLUGIN / h).read_text(encoding="utf-8")
            examined += 1
            for n, line in enumerate(text.splitlines(), 1):
                if ABS_DRIVE.search(line) or "taskade" in line.lower():
                    hits.append(f"{h}:{n}")
        print(f"examined {examined} files, {len(hits)} hits")
        self.assertGreater(examined, 0, "examined nothing")
        self.assertEqual(hits, [])

    def test_session_start_names_both_tails_and_the_script(self):
        text = (PLUGIN / HOMES[0]).read_text(encoding="utf-8")
        for s in (dr.GITHUB, dr.VAULT, "drive_roots.py", "@gtempaccount.com"):
            self.assertIn(s, text)

    def test_the_check_catches_what_it_should(self):
        self.assertTrue(ABS_DRIVE.search("`/Users/doriancougias/Library/CloudStorage/GoogleDrive-dorianc@moxywolf.com/Shared drives/GitHub`"))
        self.assertFalse(ABS_DRIVE.search("`Shared drives/GitHub`"))


if __name__ == "__main__":
    unittest.main()
