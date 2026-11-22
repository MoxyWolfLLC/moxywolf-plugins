"""Check proof artifacts and frozen plugin/governance files.

The baseline covers 1,058 files. These checks do not establish historical
worker concurrency, merges, host limits, elapsed time, or spend: PLAN.md
defines no observable interface for that evidence.

Baseline hashes were verified during drafting; this module was not run
against a completed candidate.
"""

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


_EXPORT = r"""
import sys
import tarfile

def keep(member):
    # Exclude installed dependencies and interpreter/test caches.
    ignored = {"node_modules", "__pycache__", ".pytest_cache"}
    if ignored.intersection(member.name.split("/")):
        return None
    return member

with tarfile.open(sys.argv[1], "w") as archive:
    for path in sys.argv[2:]:
        archive.add(path, arcname=path, filter=keep)
"""


@contextmanager
def exported_files(case, *paths):
    candidate = os.environ.get("GOAL_CANDIDATE")
    case.assertTrue(candidate, "GOAL_CANDIDATE must name the candidate checkout")
    with tempfile.TemporaryDirectory(prefix="swarm-width-holdout-") as temporary:
        destination = Path(temporary) / "artifacts.tar"
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                _EXPORT,
                str(destination),
                *paths,
            ],
            cwd=candidate,
            capture_output=True,
            text=True,
            timeout=120,
        )
        case.assertEqual(
            result.returncode,
            0,
            f"Artifact export failed for {paths!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        with tarfile.open(destination, "r:") as archive:
            yield archive


class Holdout(unittest.TestCase):
    def test_all_ten_proof_files_have_only_their_own_line(self):
        folder = "proof/swarm-width"
        expected = {
            f"{folder}/item-{number:02d}.txt": str(number).encode("ascii")
            for number in range(1, 11)
        }
        with exported_files(self, folder) as archive:
            members = archive.getmembers()
            roots = [
                member
                for member in members
                if member.name.rstrip("/") == folder
            ]
            self.assertEqual(len(roots), 1)
            self.assertTrue(roots[0].isdir())

            children = [
                member
                for member in members
                if member.name.rstrip("/") != folder
            ]
            self.assertCountEqual(
                [member.name for member in children],
                list(expected),
            )
            for member in children:
                with self.subTest(path=member.name):
                    self.assertTrue(member.isfile(), "Links are not proof files")
                    with archive.extractfile(member) as stream:
                        content = stream.read()
                    number = expected[member.name]
                    self.assertIn(content, (number, number + b"\n"))

    def test_plugin_and_governance_paths_remain_unchanged(self):
        # PLAN.md permits only the numbered proof files to change.
        # Freeze more than the two scripts covered by the public tests,
        # including both manifests, hooks, and CODEOWNERS.
        roots = ("plugins", ".claude-plugin", "hooks", ".github")
        expected_count = 1058
        expected_digest = (
            "f9598cc247bdc8ee5fa04545de90d315f45a1d2c6a2154f8845057861d568755"
        )

        with exported_files(self, *roots) as archive:
            rows = []
            seen = set()
            for member in archive.getmembers():
                self.assertNotIn(
                    member.name, seen, f"Duplicate archive entry: {member.name}"
                )
                seen.add(member.name)
                if member.isdir():
                    continue
                self.assertTrue(
                    member.isfile(),
                    f"Protected path is not a regular file: {member.name}",
                )
                with archive.extractfile(member) as stream:
                    digest = hashlib.sha256(stream.read()).hexdigest()
                rows.append((member.name, digest))

        self.assertEqual(
            len(rows),
            expected_count,
            "A protected file was added or removed",
        )
        manifest = json.dumps(
            sorted(rows),
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        self.assertEqual(
            hashlib.sha256(manifest).hexdigest(),
            expected_digest,
            "Plugin code, metadata, hooks, or governance files changed; "
            "the plan permits only the ten proof files",
        )


if __name__ == "__main__":
    unittest.main()
