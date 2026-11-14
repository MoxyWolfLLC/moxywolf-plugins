# drafted-by: gpt/gpt-6-astra
"""Black-box goal tests for review packet readiness."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


PEER = "plugins/gstack-execution/scripts/peer_review.py"
LEDGER = "plugins/gstack-execution/scripts/check_ledger.py"
CRITERION = "The changed function returns the reviewed value."

HEAD_FILES = {
    "a.py": b"def value():\n    return 'REVIEWED_HEAD_VALUE'\n",
    "notes.txt": b"REVIEWED_HEAD_NOTES\r\nExact bytes: caf\xc3\xa9\r\n",
    "added.txt": b"ONLY_PRESENT_AT_REVIEWED_HEAD\n",
}
CALLER_BYTES = b"from a import value\nLABEL = 'REVIEWED_CALLER'\n"
HELPER_BYTES = b"HELPER = 'REVIEWED_HELPER'\n"

# This executable represents the external reviewer, not candidate code. It
# records the actual offered surface and deliberately declines to score it.
REVIEWER = r"""
import json
import os
import sys
from pathlib import Path

marker = Path(os.environ["PACKET_REVIEWER_MARKER"])
with marker.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\n")

root = Path.cwd().resolve()
fixture = Path(os.environ["PACKET_FIXTURE_ROOT"]).resolve()
if not root.is_relative_to(fixture):
    print("fixture reviewer was not given an external surface", file=sys.stderr)
    sys.exit(93)

files = {}
for path in sorted(root.rglob("*")):
    if path.is_file():
        if not path.resolve().is_relative_to(fixture):
            print("surface file escapes fixture", file=sys.stderr)
            sys.exit(94)
        files[path.relative_to(root).as_posix()] = path.read_bytes().hex()

Path(os.environ["PACKET_SURFACE_CAPTURE"]).write_text(
    json.dumps(files), encoding="utf-8"
)
print("fixture reviewer captured surface; no verdict supplied", file=sys.stderr)
sys.exit(17)
"""


def git(fixture, *args):
    result = subprocess.run(
        ["git", "-C", str(fixture.repo), *args],
        env=fixture.env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise AssertionError(
            "Fixture git command failed:\n" + result.stdout + result.stderr
        )
    return result.stdout.strip()


def candidate(fixture, script, *args, cwd=None, env=None):
    return subprocess.run(
        [sys.executable, str(fixture.candidate / script), *map(str, args)],
        cwd=str(cwd or fixture.candidate),
        env=env or fixture.env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def record_run(fixture, exit_code=0):
    result = candidate(
        fixture,
        LEDGER,
        "run",
        "--repo",
        fixture.repo,
        "--",
        sys.executable,
        "-c",
        "import sys; print('fixture check'); sys.exit(%d)" % exit_code,
        cwd=fixture.repo,
    )
    if result.returncode != exit_code:
        raise AssertionError(
            "Could not record fixture check:\n" + result.stdout + result.stderr
        )
    branch = git(fixture, "branch", "--show-current")
    path = fixture.reviews / "ledger" / "repo" / (branch + ".jsonl")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return path, rows[-1]


def tree_bytes(root):
    """Observe only the candidate's external review output."""
    if not root.exists():
        return {}
    result = {".": None}
    for path in sorted(root.rglob("*")):
        result[path.relative_to(root).as_posix()] = (
            None if path.is_dir() else path.read_bytes()
        )
    return result


def open_packet(fixture, packet=None, flags=(), reviewer=None):
    fixture.packet_file.write_text(
        json.dumps(fixture.packet if packet is None else packet),
        encoding="utf-8",
    )
    env = fixture.env.copy()
    if reviewer is not None:
        env["GSTACK_REVIEWER"] = reviewer
    return candidate(
        fixture,
        PEER,
        "open",
        "--builder",
        "claude",
        "--packet",
        fixture.packet_file,
        "--timeout",
        "20",
        *flags,
        env=env,
    )


def require_open(test, fixture, packet=None, flags=(), reviewer=None):
    result = open_packet(fixture, packet, flags, reviewer)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    state = json.loads(result.stdout)
    test.assertEqual(state["outcome"], "opened", result.stdout)
    test.assertEqual(state["rounds_used"], 0)
    test.assertEqual(state["heads"], [[fixture.head]])
    test.assertFalse(fixture.marker.exists(), "open called a reviewer")
    saved = fixture.reviews / state["review_id"] / "state.json"
    test.assertTrue(saved.is_file(), "successful open retained no review")
    test.assertEqual(
        json.loads(saved.read_text(encoding="utf-8"))["outcome"], "opened"
    )
    return state


def require_new_refusal(test, fixture, packet, message, flags=(), reviewer=None):
    before = tree_bytes(fixture.reviews)
    result = open_packet(fixture, packet, flags, reviewer)
    test.assertEqual(result.returncode, 2, result.stdout + result.stderr)
    test.assertEqual(result.stderr.strip(), message)
    test.assertEqual(result.stdout.strip(), "")
    test.assertEqual(
        tree_bytes(fixture.reviews),
        before,
        "refused open created or modified review records",
    )
    test.assertFalse(fixture.marker.exists(), "refused open called a reviewer")


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix="packet-ready-") as temporary:
        root = Path(temporary).resolve()
        checkout = Path(os.environ["GOAL_CANDIDATE"]).resolve()
        if root.is_relative_to(checkout):
            raise AssertionError("The fixture must be outside GOAL_CANDIDATE")

        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GSTACK_", "GIT_"))
            and key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        f = SimpleNamespace(
            root=root,
            candidate=checkout,
            repo=root / "repo",
            reviews=root / "reviews",
            packet_file=root / "packet.json",
            marker=root / "reviewer-calls.jsonl",
            capture=root / "surface.json",
            env=env,
        )
        f.repo.mkdir()
        binary = root / "bin"
        binary.mkdir()
        scratch = root / "scratch"
        scratch.mkdir()
        for tool in ("codex", "claude", "gemini"):
            executable = binary / tool
            executable.write_text(
                "#!" + sys.executable + "\n" + REVIEWER, encoding="utf-8"
            )
            executable.chmod(0o755)
        env.update(
            {
                "PATH": str(binary) + os.pathsep + os.environ.get("PATH", ""),
                "TMPDIR": str(scratch),
                "PYTHONDONTWRITEBYTECODE": "1",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GSTACK_PEER_REVIEW_DIR": str(f.reviews),
                "GSTACK_REVIEWER": "codex",
                "GSTACK_CODEX_MODEL": "gpt-6-astra",
                "PACKET_FIXTURE_ROOT": str(root),
                "PACKET_REVIEWER_MARKER": str(f.marker),
                "PACKET_SURFACE_CAPTURE": str(f.capture),
            }
        )

        git(f, "init", "-q", "--object-format=sha1", "-b", "review-head")
        git(f, "config", "user.name", "Packet Fixture")
        git(f, "config", "user.email", "packet@example.invalid")
        git(f, "config", "core.hooksPath", os.devnull)
        git(f, "config", "commit.gpgsign", "false")
        git(f, "config", "core.autocrlf", "false")
        initial = {
            "a.py": b"def value():\    return 'BASE_VALUE'\n".replace(
                b"\\    ", b"\n    "
            ),
            "notes.txt": b"BASE_NOTES\n",
            "caller.py": CALLER_BYTES,
            "helper.py": HELPER_BYTES,
            "obsolete.txt": b"BASE_OBSOLETE_FILE\n",
        }
        for name, content in initial.items():
            (f.repo / name).write_bytes(content)
        git(f, "add", ".")
        git(f, "commit", "-qm", "base")
        f.base = git(f, "rev-parse", "HEAD")

        for name, content in HEAD_FILES.items():
            (f.repo / name).write_bytes(content)
        (f.repo / "obsolete.txt").unlink()
        git(f, "add", "-A")
        git(f, "commit", "-qm", "reviewed change")
        f.head = git(f, "rev-parse", "HEAD")
        f.ledger_file, f.run = record_run(f)

        f.packet = {
            "outcome": "Return the reviewed value",
            "acceptance_criteria": [CRITERION],
            "repos": [
                {"path": str(f.repo), "base": f.base, "head": f.head}
            ],
            "changed_behavior": "The function returns the reviewed value.",
            "exclusions": [],
            "tests": {
                "commands": ["fixture check"],
                "results": "passed",
                "environment": "isolated fixture",
                "ledger_runs": [{"repo": str(f.repo), "run_id": f.run["id"]}],
            },
            "release_owner": "packet-fixture-owner",
            "data_use": {
                "owner": "packet-fixture-owner",
                "classification": "test",
                "allow_repository": True,
                "allow_history": True,
                "allowed_tools": ["codex", "claude"],
            },
            "coverage": {
                "status": "checked",
                "criteria": [
                    {
                        "item": "FIXTURE-001",
                        "criterion_no": 1,
                        "declared": CRITERION,
                        "probability": 0.99,
                    }
                ],
            },
        }
        yield f


class PacketReady(unittest.TestCase):
    def test_open_refuses_missing_data_use_before_dispatch(self):
        """Scenario: Given a packet with no data_use block, when peer_review.py open runs, then it refuses before any reviewer is called and names data_use"""
        cases = (
            "missing",
            "empty",
            "repository-denied",
            "chosen-reviewer-denied",
            "missing-before-coverage-and-ledger",
            "coverage-missing",
            "coverage-empty",
            "coverage-before-ledger",
        )
        for case in cases:
            with self.subTest(case=case), fixture() as f:
                packet = copy.deepcopy(f.packet)
                reviewer = None
                expected = "refused: data_use: missing"
                if case in {"missing", "missing-before-coverage-and-ledger"}:
                    packet.pop("data_use")
                elif case == "empty":
                    packet["data_use"] = {}
                elif case == "repository-denied":
                    packet["data_use"]["allow_repository"] = False
                    expected = (
                        "refused: data_use: denied: data_use: "
                        "repository/history permission and accountable owner required"
                    )
                elif case == "chosen-reviewer-denied":
                    reviewer = "gemini"
                    expected = (
                        "refused: data_use: denied: "
                        "data_use: tool destination denied: gemini"
                    )
                else:
                    expected = "refused: coverage: not attached"

                if case == "coverage-empty":
                    packet["coverage"] = {}
                elif case in {
                    "coverage-missing",
                    "coverage-before-ledger",
                    "missing-before-coverage-and-ledger",
                }:
                    packet.pop("coverage")

                if case in {
                    "coverage-before-ledger",
                    "missing-before-coverage-and-ledger",
                }:
                    row = dict(f.run, head=f.base)
                    f.ledger_file.write_text(
                        json.dumps(row) + "\n", encoding="utf-8"
                    )
                require_new_refusal(
                    self, f, packet, expected, reviewer=reviewer
                )

    def test_open_refuses_ledger_run_behind_head(self):
        """Scenario: Given a packet whose named ledger run is at a commit older than the head being sent, when open runs, then it refuses and names the ledger run and both commits"""
        for case in ("older", "abbreviated", "no-commit", "first-stale-run"):
            with self.subTest(case=case), fixture() as f:
                packet = copy.deepcopy(f.packet)
                if case in {"older", "first-stale-run"}:
                    git(f, "checkout", "-qb", "evidence-base", f.base)
                    _, stale = record_run(f)
                    self.assertEqual(stale["head"], f.base)
                    self.assertEqual(git(f, "rev-parse", "HEAD"), f.base)
                    self.assertNotEqual(f.base, f.head)
                    expected_sha = f.base
                    runs = [{"repo": str(f.repo), "run_id": stale["id"]}]
                    if case == "first-stale-run":
                        _, later = record_run(f)
                        runs = [
                            {"repo": str(f.repo), "run_id": f.run["id"]},
                            {"repo": str(f.repo), "run_id": stale["id"]},
                            {"repo": str(f.repo), "run_id": later["id"]},
                        ]
                    packet["tests"]["ledger_runs"] = runs
                else:
                    stale = dict(f.run)
                    if case == "abbreviated":
                        stale["head"] = f.head[:12]
                        expected_sha = stale["head"]
                    else:
                        stale.pop("head")
                        expected_sha = "none"
                    f.ledger_file.write_text(
                        json.dumps(stale) + "\n", encoding="utf-8"
                    )
                require_new_refusal(
                    self,
                    f,
                    packet,
                    "refused: tests.ledger_runs: run "
                    + stale["id"]
                    + " is at "
                    + expected_sha
                    + ", head is "
                    + f.head,
                )

    def test_surface_shows_head_commit_bytes_from_other_branch(self):
        """Scenario: Given a checkout sitting on a different branch from the packet's head, when open builds the reviewer's surface, then every changed file shows the head commit's bytes"""
        with fixture() as f:
            git(f, "checkout", "-qb", "other-branch", f.base)
            other_files = {
                "a.py": b"def value():\n    return 'OTHER_BRANCH_POISON'\n",
                "notes.txt": b"OTHER_BRANCH_POISON_NOTES\n",
                "caller.py": b"from a import value\nLABEL = 'OTHER_BRANCH_POISON'\n",
                "helper.py": b"HELPER = 'OTHER_BRANCH_POISON'\n",
                "obsolete.txt": b"OTHER_BRANCH_POISON_OBSOLETE\n",
            }
            for name, content in other_files.items():
                (f.repo / name).write_bytes(content)
            git(f, "add", "-A")
            git(f, "commit", "-qm", "different branch contents")
            other_head = git(f, "rev-parse", "HEAD")
            self.assertNotEqual(other_head, f.head)
            self.assertFalse((f.repo / "added.txt").exists())

            packet = copy.deepcopy(f.packet)
            packet["acceptance_criteria"].append(
                "`helper.py` retains its fixture value."
            )
            state = require_open(self, f, packet)
            result = candidate(f, PEER, "round", state["review_id"])
            self.assertTrue(
                f.capture.is_file(),
                "Reviewer never received a surface:\n"
                + result.stdout
                + result.stderr,
            )
            self.assertEqual(
                len(f.marker.read_text(encoding="utf-8").splitlines()), 1
            )
            captured = {
                name: bytes.fromhex(content)
                for name, content in json.loads(
                    f.capture.read_text(encoding="utf-8")
                ).items()
            }
            for name, expected in HEAD_FILES.items():
                with self.subTest(file=name):
                    self.assertEqual(
                        captured.get("changed/0-repo/" + name), expected
                    )
            self.assertEqual(
                captured.get("callers/0-repo/caller.py"), CALLER_BYTES
            )
            self.assertEqual(
                captured.get("dependencies/0-repo/helper.py"), HELPER_BYTES
            )
            for name, content in captured.items():
                self.assertNotIn(b"OTHER_BRANCH_POISON", content, name)

            # A deleted path may be omitted or represented by a deletion
            # notice, but it must not be resurrected from the other branch.
            deleted = captured.get("changed/0-repo/obsolete.txt")
            if deleted is not None:
                self.assertIn(b"deleted", deleted.lower())
            diff = captured["CHANGE.diff"]
            self.assertIn(b"obsolete.txt", diff)
            self.assertIn(b"deleted file mode", diff)
            self.assertEqual(git(f, "rev-parse", "HEAD"), other_head)
            self.assertEqual(git(f, "branch", "--show-current"), "other-branch")
            for name, expected in other_files.items():
                self.assertEqual((f.repo / name).read_bytes(), expected)

    def test_complete_packet_still_opens_and_refused_stays_refused(self):
        """Scenario: A complete packet at its head being refused, or a packet that is refused today being dispatched, must never happen"""
        accepted = (
            "complete",
            "complete-with-checkout-behind",
            "attached-unavailable-coverage",
            "missing-coverage-override",
            "empty-coverage-override",
            "low-coverage-override",
            "off-repo-override",
            "failed-check-override",
        )
        for case in accepted:
            with self.subTest(accepted=case), fixture() as f:
                packet = copy.deepcopy(f.packet)
                flags = ()
                if case == "complete-with-checkout-behind":
                    git(f, "checkout", "-qb", "behind", f.base)
                elif case == "attached-unavailable-coverage":
                    packet["coverage"] = {
                        "status": "unavailable",
                        "why": "fixture scorer unavailable",
                    }
                elif case in {
                    "missing-coverage-override",
                    "empty-coverage-override",
                    "low-coverage-override",
                }:
                    if case == "missing-coverage-override":
                        packet.pop("coverage")
                    elif case == "empty-coverage-override":
                        packet["coverage"] = {}
                    else:
                        packet["coverage"]["criteria"][0]["probability"] = 0.1
                    packet["exclusions"] = [
                        "This fixture review accepts narrow coverage."
                    ]
                    flags = ("--accept-narrow-packet",)
                elif case == "off-repo-override":
                    packet["acceptance_criteria"] = [
                        "The application works on the Release Owner's Mac."
                    ]
                    flags = ("--accept-off-repo-criterion",)
                elif case == "failed-check-override":
                    record_run(f, exit_code=1)
                    flags = ("--accept-open-failure", "Known fixture failure")
                state = require_open(self, f, packet, flags)
                if case == "low-coverage-override":
                    self.assertTrue(state["coverage_overridden"])
                elif case == "off-repo-override":
                    self.assertEqual(
                        state["off_repo_overridden"],
                        packet["acceptance_criteria"],
                    )
                elif case == "failed-check-override":
                    self.assertEqual(state["ledger_status"], "overridden")
                    self.assertEqual(
                        state["open_failures_overridden"], "Known fixture failure"
                    )

        refused = (
            ("unchanged", "missing_commits"),
            ("empty-criteria", "acceptance_criteria"),
            ("duplicate-criteria", "acceptance_criteria"),
            ("unaccountable-owner", "release_owner"),
            ("low-coverage", "packet_narrower_than_item"),
            ("checked-empty-coverage", "packet_narrower_than_item"),
            ("missing-ledger-run", "0123456789ab"),
            ("foreign-ledger-repo", "tests.ledger_runs"),
            ("same-family-reviewer", "reviewer_not_independent"),
            ("off-repo", "unevidenced_off_repo_criterion"),
            ("missing-model-selection", "model_selection_missing"),
            ("failed-check", "open_check_failure"),
        )
        for case, diagnostic in refused:
            with self.subTest(refused=case), fixture() as f:
                packet = copy.deepcopy(f.packet)
                reviewer = None
                if case == "unchanged":
                    packet["repos"][0]["base"] = f.head
                elif case == "empty-criteria":
                    packet["acceptance_criteria"] = []
                elif case == "duplicate-criteria":
                    packet["acceptance_criteria"] = [CRITERION, CRITERION]
                elif case == "unaccountable-owner":
                    packet["release_owner"] = "team"
                    packet["data_use"]["owner"] = "team"
                elif case == "low-coverage":
                    packet["coverage"]["criteria"][0]["probability"] = 0.1
                elif case == "checked-empty-coverage":
                    packet["coverage"]["criteria"] = []
                elif case == "missing-ledger-run":
                    packet["tests"]["ledger_runs"][0]["run_id"] = "0123456789ab"
                elif case == "foreign-ledger-repo":
                    packet["tests"]["ledger_runs"][0]["repo"] = "not-listed"
                elif case == "same-family-reviewer":
                    reviewer = "claude"
                elif case == "off-repo":
                    packet["acceptance_criteria"] = [
                        "The application works on the Release Owner's Mac."
                    ]
                elif case == "missing-model-selection":
                    packet["items"] = ["FIXTURE-001"]
                elif case == "failed-check":
                    record_run(f, exit_code=1)

                before = tree_bytes(f.reviews)
                result = open_packet(f, packet, reviewer=reviewer)
                self.assertNotEqual(
                    result.returncode, 0, result.stdout + result.stderr
                )
                self.assertIn(diagnostic, result.stdout + result.stderr)
                self.assertEqual(tree_bytes(f.reviews), before)
                self.assertFalse(
                    f.marker.exists(), "a previously refused packet was dispatched"
                )


if __name__ == "__main__":
    unittest.main()
