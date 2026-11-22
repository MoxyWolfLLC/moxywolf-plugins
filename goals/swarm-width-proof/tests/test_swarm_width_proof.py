# drafted-by: gpt/gpt-6-astra
"""Check proof artifacts and declarations, not runtime concurrency or spend."""

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


@contextmanager
def exported_files(test_case, *paths):
    """Inspect only an archive exported outside the candidate checkout."""
    candidate = os.environ.get("GOAL_CANDIDATE")
    test_case.assertTrue(candidate, "GOAL_CANDIDATE must name the candidate checkout")
    with tempfile.TemporaryDirectory(prefix="swarm-width-proof-") as temporary:
        archive_path = Path(temporary) / "export.tar"
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "tarfile",
                "-c",
                str(archive_path),
                *paths,
            ],
            cwd=candidate,
            capture_output=True,
            text=True,
            timeout=120,
        )
        test_case.assertEqual(
            result.returncode,
            0,
            f"Candidate artifact export failed for {paths!r}:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        with tarfile.open(archive_path, "r:") as archive:
            yield archive


def exported_bytes(test_case, archive, path):
    """Read a regular file from the external archive, rejecting links."""
    matches = [member for member in archive.getmembers() if member.name == path]
    test_case.assertEqual(len(matches), 1, f"Expected exactly one file: {path}")
    member = matches[0]
    test_case.assertTrue(member.isfile(), f"Expected a regular file: {path}")
    with archive.extractfile(member) as stream:
        return stream.read()


class SwarmWidthProof(unittest.TestCase):
    def test_ten_item_files_exist_with_their_own_number(self):
        """Verify each numbered artifact contains only its own number.
        Scenario: Given 10 independent items and a width of 10 on a host whose limit allows 10, then 10 workers run at the same time and all 10 items merge
        """
        paths = tuple(
            f"proof/swarm-width/item-{number:02d}.txt"
            for number in range(1, 11)
        )
        with exported_files(self, *paths) as archive:
            for number, path in enumerate(paths, start=1):
                with self.subTest(path=path):
                    content = exported_bytes(self, archive, path)
                    expected = str(number).encode("ascii")
                    self.assertIn(
                        content,
                        (expected, expected + b"\n"),
                        f"{path} must contain only the line {number}",
                    )

    def test_proof_folder_holds_exactly_the_ten_item_files(self):
        """Verify the proof directory contains exactly the ten regular files.
        Scenario: Given 10 independent items and a width of 10 on a host whose limit allows 10, then 10 workers run at the same time and all 10 items merge
        """
        folder = "proof/swarm-width"
        expected = [
            f"{folder}/item-{number:02d}.txt"
            for number in range(1, 11)
        ]
        with exported_files(self, folder) as archive:
            members = archive.getmembers()
            roots = [
                member for member in members
                if member.name.rstrip("/") == folder
            ]
            self.assertEqual(len(roots), 1)
            self.assertTrue(roots[0].isdir(), "Proof folder must be a directory")
            children = [
                member for member in members
                if member.name.rstrip("/") != folder
            ]
            self.assertCountEqual(
                [member.name for member in children],
                expected,
                "Proof folder must contain exactly ten items and no other entries",
            )
            for member in children:
                with self.subTest(path=member.name):
                    self.assertTrue(
                        member.isfile(),
                        f"{member.name} must be a regular file",
                    )

    def test_deps_declare_ten_independent_items_at_width_ten(self):
        """Verify ten distinct writes with no dependency ordering.
        Scenario: Given 10 independent items and a width of 10 on a host whose limit allows 10, then 10 workers run at the same time and all 10 items merge
        """
        path = "goals/swarm-width-proof/DEPS.json"
        with exported_files(self, path) as archive:
            declaration = json.loads(
                exported_bytes(self, archive, path).decode("utf-8")
            )

        self.assertEqual(declaration["version"], 1)
        self.assertIs(type(declaration["max_workers"]), int)
        self.assertEqual(declaration["max_workers"], 10)
        items = declaration["items"]
        self.assertIsInstance(items, dict)
        self.assertEqual(set(items), {str(number) for number in range(1, 11)})
        for number in range(1, 11):
            with self.subTest(item=number):
                item = items[str(number)]
                self.assertEqual(item["id"], f"item-{number:02d}")
                self.assertEqual(
                    item["writes"],
                    [f"proof/swarm-width/item-{number:02d}.txt"],
                )
                self.assertEqual(item["start_after"], [])
                self.assertEqual(item["integrate_after"], [])
                self.assertEqual(item["contracts"], [])

    def test_swarm_and_goal_brief_scripts_are_unchanged(self):
        """Verify the protected scripts against the brief's literal hashes.
        Scenario: Changing plugins/gstack-execution/scripts/swarm.py (sha256 68b7183073d7767c96c3bdf82b0c9a618cd8f12aa5c9874fd31798f2744340f6) or goal_brief.py (sha256 77578c79b16419489ba5f2c072c8219e74c536e86c124504e48446599a0d4b8a) must never happen
        """
        expected = {
            "plugins/gstack-execution/scripts/swarm.py": (
                "68b7183073d7767c96c3bdf82b0c9a618cd8f12aa5c9874fd31798f2744340f6"
            ),
            "plugins/gstack-execution/scripts/goal_brief.py": (
                "77578c79b16419489ba5f2c072c8219e74c536e86c124504e48446599a0d4b8a"
            ),
        }
        with exported_files(self, *expected) as archive:
            for path, digest in expected.items():
                with self.subTest(path=path):
                    content = exported_bytes(self, archive, path)
                    self.assertEqual(
                        hashlib.sha256(content).hexdigest(),
                        digest,
                        f"Protected script changed: {path}",
                    )


if __name__ == "__main__":
    unittest.main()
