"""MR-006.4 (review F2): review_host.sh carries GSTACK_HISTORY_DIR into its env file escaped, not interpolated.

ponytail: runs the script's own export line (read from the file, so a change to it is what gets tested)
with awkward values, sources the result in a fresh bash, and compares. The rest of review_host.sh
installs CLIs and clones a branch, which is not this item's to test.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "review_host.sh"


class HistoryExport(unittest.TestCase):
    def test_the_export_line_round_trips_awkward_paths(self):
        line = next(l.strip() for l in SCRIPT.read_text().splitlines() if "GSTACK_HISTORY_DIR=%q" in l)
        for value in ("/tmp/plain", "/Shared drives/MW Plugins/06 – Engineering/peer-reviews",
                      "/tmp/$USER/history", "/tmp/it's \"quoted\"", "/tmp/`id`/$(id)"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as d:
                envf = Path(d) / "env"
                subprocess.run(["bash", "-c", f"{line} > {envf}"], env={**os.environ, "GSTACK_HISTORY_DIR": value}, check=True)
                out = subprocess.run(["bash", "-c", f"unset GSTACK_HISTORY_DIR; source {envf}; printf %s \"$GSTACK_HISTORY_DIR\""],
                                     capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "GSTACK_HISTORY_DIR"})
                self.assertEqual(out.returncode, 0, out.stderr)
                self.assertEqual(out.stdout, value)

    def test_unset_writes_no_export(self):
        line = next(l.strip() for l in SCRIPT.read_text().splitlines() if "GSTACK_HISTORY_DIR=%q" in l)
        env = {k: v for k, v in os.environ.items() if k != "GSTACK_HISTORY_DIR"}
        out = subprocess.run(["bash", "-c", line], capture_output=True, text=True, env=env)
        self.assertEqual((out.returncode, out.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
