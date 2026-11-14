# drafted-by: gpt/gpt-6-astra
"""Black-box goal tests for review packet readiness."""

import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


CLI = "plugins/gstack-execution/scripts/peer_review.py"
RUN_ID = "a0b1c2d3e4f5"
STALE_RUN_ID = "111122223333"
CRITERION = "compute(1) returns 2, matching the contract in `context.py`."

HEAD_FILES = {
    "a.py": b"def compute(value):\n    return value + 1\n",
    "NOTES.md": b"# Reviewed head\nPreserve these trailing newlines.\n\n",
    "added.txt": b"Present at the reviewed head without a final newline",
    "assets.bin": b"\x00\xffHEAD\x80\n\n",
    "caller.py": b"import a\nRESULT = a.compute(1)  # HEAD_CALLER\n",
    "context.py": b"EXPECTED = 2  # HEAD_CONTEXT\n",
}
CHANGED_FILES = ("a.py", "NOTES.md", "added.txt", "assets.bin")

REVIEWER_SOURCE = r'''
import base64
import json
import os
import sys
from pathlib import Path

with Path(os.environ["PACKET_TEST_CALLS"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\n")

args = sys.argv[1:]
surface = Path(args[args.index("-C") + 1]).resolve()
fixture_root = Path(os.environ["PACKET_TEST_ROOT"]).resolve()
surface.relative_to(fixture_root)
files = {}
for path in surface.rglob("*"):
    if path.is_file():
        path.resolve().relative_to(fixture_root)
        files[path.relative_to(surface).as_posix()] = (
            base64.b64encode(path.read_bytes()).decode("ascii")
        )
Path(os.environ["PACKET_TEST_CAPTURE"]).write_text(
    json.dumps(files), encoding="utf-8"
)
reply = {
    "verdict": "no_blocking_findings",
    "acceptance": [{
        "criterion": os.environ["PACKET_TEST_CRITERION"],
        "met": True,
        "evidence": "changed/0-repo/a.py:2",
    }],
    "findings": [],
    "blocker_resolutions": [],
    "regressions_from_fixes": [],
    "unknowns": [],
    "notes": "Local fixture reviewer read the supplied surface.",
}
serialized = json.dumps(reply)
if "--output-last-message" in args:
    destination = Path(args[args.index("--output-last-message") + 1])
    destination.resolve().relative_to(fixture_root)
    destination.write_text(serialized, encoding="utf-8")
print(serialized)
print("model: gpt-6-astra", file=sys.stderr)
'''


def _git(fixture, *args):
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false",
         "-C", str(fixture.repo), *args],
        env=fixture.env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise AssertionError(
            f"Fixture git command failed: {args!r}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


def _commit(fixture, message):
    _git(fixture, "add", "-A")
    _git(fixture, "commit", "-qm", message)
    return _git(fixture, "rev-parse", "HEAD")


def _write_run(fixture, head, run_id=RUN_ID, exit_code=0):
    """Write a literal ledger fixture and its matching receipt."""
    directory = fixture.reviews / "ledger" / "repo"
    receipts = directory / "packet-head.receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt = b"fixture check completed\n"
    (receipts / f"{run_id}.log").write_bytes(receipt)
    record = {
        "id": run_id,
        "repo": "local:" + str(fixture.repo),
        "identity": {"cwd": ".", "argv": ["fixture-check", run_id]},
        "head": head,
        "exit_code": exit_code,
        "started": 1700000000,
        "ended": 1700000001,
        "receipt": {
            "sha256": hashlib.sha256(receipt).hexdigest(),
            "bytes": len(receipt),
            "truncated": False,
        },
    }
    with (directory / "packet-head.jsonl").open(
        "a", encoding="utf-8"
    ) as stream:
        stream.write(json.dumps(record) + "\n")


@contextmanager
def _fixture(ledger_at_base=False):
    # Do not inherit a temporary-directory location inside the candidate.
    with tempfile.TemporaryDirectory(
        prefix="packet-ready-", dir="/tmp"
    ) as temporary:
        root = Path(temporary).resolve()
        fixture = SimpleNamespace(
            root=root,
            repo=root / "repo",
            reviews=root / "reviews",
            calls=root / "reviewer-calls.jsonl",
            capture=root / "reviewer-surface.json",
            packet_path=root / "packet.json",
        )
        fixture.repo.mkdir()
        binaries = root / "bin"
        binaries.mkdir()
        temporary_files = root / "tmp"
        temporary_files.mkdir()
        fixture.env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("GSTACK_", "GIT_", "PYTHON"))
        }
        fixture.env.update({
            "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GSTACK_PEER_REVIEW_DIR": str(fixture.reviews),
            "GSTACK_REVIEWER": "codex",
            "GSTACK_CODEX_MODEL": "gpt-6-astra",
            "TMPDIR": str(temporary_files),
            "PACKET_TEST_ROOT": str(root),
            "PACKET_TEST_CALLS": str(fixture.calls),
            "PACKET_TEST_CAPTURE": str(fixture.capture),
            "PACKET_TEST_CRITERION": CRITERION,
        })
        reviewer = binaries / "codex"
        reviewer.write_text(
            "#!" + sys.executable + "\n" + REVIEWER_SOURCE,
            encoding="utf-8",
        )
        reviewer.chmod(0o755)

        _git(fixture, "init", "-q", "-b", "packet-head")
        _git(fixture, "config", "user.name", "Packet Fixture")
        _git(fixture, "config", "user.email", "packet@example.invalid")
        _git(fixture, "config", "core.hooksPath", os.devnull)
        _git(fixture, "config", "core.autocrlf", "false")
        base_files = {
            "a.py": b"def compute(value):\n    return value\n",
            "NOTES.md": b"# Base notes\n",
            "caller.py": HEAD_FILES["caller.py"],
            "context.py": HEAD_FILES["context.py"],
            "retired.py": b"RETIRED = 'base-only implementation'\n",
        }
        for name, content in base_files.items():
            (fixture.repo / name).write_bytes(content)
        fixture.base = _commit(fixture, "base")
        for name, content in HEAD_FILES.items():
            (fixture.repo / name).write_bytes(content)
        (fixture.repo / "retired.py").unlink()
        fixture.head = _commit(fixture, "reviewed head")

        _write_run(
            fixture, fixture.base if ledger_at_base else fixture.head
        )
        fixture.packet = {
            "outcome": "compute adds one",
            "acceptance_criteria": [CRITERION],
            "repos": [{
                "path": str(fixture.repo),
                "base": fixture.base,
                "head": fixture.head,
            }],
            "changed_behavior": "compute returns its argument plus one",
            "exclusions": [],
            "tests": {
                "commands": ["fixture-check"],
                "results": "fixture check completed",
                "environment": "isolated test repository",
                "ledger_runs": [{
                    "repo": str(fixture.repo),
                    "run_id": RUN_ID,
                }],
            },
            "release_owner": "Fixture Human",
            "data_use": {
                "owner": "Fixture Human",
                "classification": "test",
                "allow_repository": True,
                "allow_history": True,
                "allowed_tools": ["codex", "claude"],
            },
            "coverage": {
                "status": "checked",
                "criteria": [{
                    "item": "fixture",
                    "criterion_no": 1,
                    "declared": CRITERION,
                    "probability": 1.0,
                }],
            },
        }
        yield fixture


def _run(fixture, *args):
    return subprocess.run(
        [sys.executable, "-B", CLI, *map(str, args)],
        cwd=os.environ["GOAL_CANDIDATE"],
        env=fixture.env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _open(fixture, packet=None, *flags):
    fixture.packet_path.write_text(
        json.dumps(fixture.packet if packet is None else packet),
        encoding="utf-8",
    )
    return _run(
        fixture, "open", "--builder", "claude",
        "--packet", fixture.packet_path, "--timeout", "20", *flags,
    )


def _diagnostic(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _tree(path):
    """Inspect only the externally supplied review directory."""
    if not path.exists():
        return None
    return {
        entry.relative_to(path).as_posix():
            entry.read_bytes() if entry.is_file() else None
        for entry in path.rglob("*")
    }


def _assert_not_dispatched(test, fixture):
    test.assertFalse(
        fixture.calls.exists(), "A reviewer was called for a refused packet."
    )
    test.assertFalse(fixture.capture.exists())


def _assert_refusal(test, fixture, packet, message, exit_code=None):
    before = _tree(fixture.reviews)
    result = _open(fixture, packet)
    diagnostic = _diagnostic(result)
    if exit_code is None:
        test.assertNotEqual(result.returncode, 0, diagnostic)
    else:
        test.assertEqual(result.returncode, exit_code, diagnostic)
    test.assertIn(message, result.stderr, diagnostic)
    test.assertNotIn("Traceback (most recent call last)", result.stderr)
    test.assertEqual(
        _tree(fixture.reviews), before,
        "Refusing open created or changed review-directory contents.",
    )
    _assert_not_dispatched(test, fixture)
    return result


def _assert_opened(test, fixture, packet=None, flags=()):
    result = _open(fixture, packet, *flags)
    test.assertEqual(result.returncode, 0, _diagnostic(result))
    state = json.loads(result.stdout)
    test.assertEqual(state["outcome"], "opened", _diagnostic(result))
    test.assertEqual(state["rounds_used"], 0)
    test.assertEqual(state["reviewer"], "codex")
    test.assertEqual(state["heads"], [[fixture.head]])
    review_id = state["review_id"]
    test.assertTrue(review_id)
    test.assertNotIn(review_id, (".", ".."))
    test.assertEqual(Path(review_id).name, review_id)
    stored = json.loads(
        (fixture.reviews / review_id / "state.json").read_text(
            encoding="utf-8"
        )
    )
    test.assertEqual(stored["outcome"], "opened")
    return state


class PacketReady(unittest.TestCase):
    def test_open_refuses_missing_data_use_before_dispatch(self):
        """Scenario: Given a packet with no data_use block, when peer_review.py open runs, then it refuses before any reviewer is called and names data_use"""
        for variant in ("absent", "empty", "denied", "coverage absent"):
            with self.subTest(variant=variant), _fixture() as fixture:
                packet = copy.deepcopy(fixture.packet)
                if variant == "absent":
                    del packet["data_use"]
                    message = "refused: data_use missing"
                elif variant == "empty":
                    packet["data_use"] = {}
                    message = "refused: data_use missing"
                elif variant == "denied":
                    packet["data_use"]["allowed_tools"] = ["claude"]
                    message = "refused: data_use_denied:"
                else:
                    del packet["coverage"]
                    message = "refused: coverage not attached"
                result = _assert_refusal(
                    self, fixture, packet, message, exit_code=2
                )
                if variant == "denied":
                    reason = result.stderr.split(message, 1)[1].strip()
                    self.assertTrue(reason, "The denial must explain its reason.")
                    self.assertIn("codex", reason)

    def test_open_refuses_ledger_run_behind_head(self):
        """Scenario: Given a packet whose named ledger run is at a commit older than the head being sent, when open runs, then it refuses and names the ledger run and both commits"""
        for checkout_at_base in (False, True):
            with self.subTest(checkout_at_base=checkout_at_base):
                with _fixture(ledger_at_base=True) as fixture:
                    if checkout_at_base:
                        _git(
                            fixture, "checkout", "-qb",
                            "behind-checkout", fixture.base,
                        )
                    _assert_refusal(
                        self, fixture, fixture.packet,
                        f"refused: ledger run {RUN_ID} is at {fixture.base}, "
                        f"head is {fixture.head}",
                        exit_code=2,
                    )

        # Replacement evidence must be checked before a reviewer is called.
        with self.subTest(command="round"), _fixture() as fixture:
            state = _assert_opened(self, fixture)
            _write_run(fixture, fixture.base, STALE_RUN_ID)
            result = _run(
                fixture, "round", state["review_id"],
                "--ledger-run", f"{fixture.repo}={STALE_RUN_ID}",
            )
            self.assertEqual(result.returncode, 2, _diagnostic(result))
            self.assertIn(
                f"refused: ledger run {STALE_RUN_ID} is at {fixture.base}, "
                f"head is {fixture.head}",
                result.stderr,
                _diagnostic(result),
            )
            _assert_not_dispatched(self, fixture)

    def test_surface_shows_head_commit_bytes_from_other_branch(self):
        """Scenario: Given a checkout sitting on a different branch from the packet's head, when open builds the reviewer's surface, then every changed file shows the head commit's bytes"""
        with _fixture() as fixture:
            _git(fixture, "checkout", "-qb", "other-branch", fixture.base)
            for name in HEAD_FILES:
                (fixture.repo / name).write_bytes(
                    b"# OTHER_BRANCH_BYTES\n"
                    b"import a\nVALUE = 'not the reviewed head'\n"
                )
            (fixture.repo / "retired.py").write_bytes(
                b"RETIRED = 'OTHER_BRANCH_BYTES must not be resurrected'\n"
            )
            _commit(fixture, "unrelated branch")
            (fixture.repo / "a.py").write_bytes(
                b"def compute(value):\n"
                b"    return 'DIRTY_WORKTREE_BYTES'\n"
            )

            state = _assert_opened(self, fixture)
            result = _run(fixture, "round", state["review_id"])
            self.assertTrue(fixture.capture.exists(), _diagnostic(result))
            encoded = json.loads(
                fixture.capture.read_text(encoding="utf-8")
            )
            files = {
                name: base64.b64decode(content)
                for name, content in encoded.items()
            }

            for name in CHANGED_FILES:
                with self.subTest(changed_file=name):
                    key = f"changed/0-repo/{name}"
                    self.assertIn(key, files)
                    self.assertEqual(files[key], HEAD_FILES[name])
            self.assertEqual(
                files.get("callers/0-repo/caller.py"),
                HEAD_FILES["caller.py"],
                "Callers must also come from the packet's head.",
            )
            self.assertEqual(
                files.get("dependencies/0-repo/context.py"),
                HEAD_FILES["context.py"],
                "Criterion dependencies must also come from the packet's head.",
            )
            self.assertIn(b"retired.py", files["CHANGE.diff"])
            self.assertIn(b"deleted file mode", files["CHANGE.diff"])
            deleted = files.get("changed/0-repo/retired.py")
            if deleted is not None:
                self.assertIn(b"deleted", deleted.lower())
                self.assertNotIn(b"OTHER_BRANCH_BYTES", deleted)
            for name, content in files.items():
                if name.startswith(("changed/", "callers/", "dependencies/")):
                    with self.subTest(surface_file=name):
                        self.assertNotIn(b"OTHER_BRANCH_BYTES", content)
                        self.assertNotIn(b"DIRTY_WORKTREE_BYTES", content)
            self.assertEqual(result.returncode, 0, _diagnostic(result))

    def test_complete_packet_still_opens_and_refused_stays_refused(self):
        """Scenario: A complete packet at its head being refused, or a packet that is refused today being dispatched, must never happen"""
        with self.subTest(case="complete packet"), _fixture() as fixture:
            state = _assert_opened(self, fixture)
            self.assertTrue(state["coverage_checked"])
            self.assertEqual(state["ledger_status"], "clear")
            _assert_not_dispatched(self, fixture)

            # Establish that the local reviewer actually runs and reads its surface.
            result = _run(fixture, "round", state["review_id"])
            self.assertEqual(result.returncode, 0, _diagnostic(result))
            self.assertEqual(
                json.loads(result.stdout)["outcome"], "no_blocking_findings"
            )
            self.assertTrue(fixture.capture.exists(), _diagnostic(result))
            self.assertEqual(
                len(fixture.calls.read_text(encoding="utf-8").splitlines()), 1
            )

        cases = (
            ("narrow", "packet_narrower_than_item"),
            ("empty coverage", "packet_narrower_than_item"),
            ("off repository", "unevidenced_off_repo_criterion"),
            ("failed check", "open_check_failure"),
            ("missing ledger run", "malformed_packet"),
            ("same family", "reviewer_not_independent"),
            ("invalid owner", "malformed_packet"),
            ("duplicate criteria", "malformed_packet"),
            ("unchanged commits", "missing_commits"),
        )
        for case, message in cases:
            with self.subTest(case=case), _fixture() as fixture:
                packet = copy.deepcopy(fixture.packet)
                override = ()
                if case == "narrow":
                    packet["coverage"]["criteria"][0]["probability"] = 0.1
                    packet["exclusions"] = ["Fixture accepts narrower coverage."]
                    override = ("--accept-narrow-packet",)
                elif case == "empty coverage":
                    packet["coverage"]["criteria"] = []
                elif case == "off repository":
                    packet["acceptance_criteria"] = [
                        "The builder's Mac runs the application."
                    ]
                    override = ("--accept-off-repo-criterion",)
                elif case == "failed check":
                    _write_run(
                        fixture, fixture.head,
                        run_id="ffff00001111", exit_code=1,
                    )
                    override = (
                        "--accept-open-failure",
                        "Fixture owner accepts this known failing check.",
                    )
                elif case == "missing ledger run":
                    packet["tests"]["ledger_runs"][0]["run_id"] = "999988887777"
                elif case == "same family":
                    fixture.env["GSTACK_REVIEWER"] = "claude"
                elif case == "invalid owner":
                    packet["release_owner"] = "team"
                elif case == "duplicate criteria":
                    packet["acceptance_criteria"] = [CRITERION, CRITERION]
                else:
                    packet["repos"][0]["base"] = fixture.head

                _assert_refusal(self, fixture, packet, message)
                if override:
                    state = _assert_opened(
                        self, fixture, packet, flags=override
                    )
                    if case == "narrow":
                        self.assertTrue(state["coverage_overridden"])
                    elif case == "off repository":
                        self.assertIn(
                            packet["acceptance_criteria"][0],
                            state["off_repo_overridden"],
                        )
                    else:
                        self.assertEqual(
                            state["open_failures_overridden"], override[1]
                        )
                    _assert_not_dispatched(self, fixture)

        with self.subTest(case="coverage override"), _fixture() as fixture:
            packet = copy.deepcopy(fixture.packet)
            del packet["coverage"]
            packet["exclusions"] = [
                "Fixture owner explicitly accepts a packet without coverage."
            ]
            state = _assert_opened(
                self, fixture, packet, flags=("--accept-narrow-packet",)
            )
            self.assertFalse(state["coverage_checked"])
            _assert_not_dispatched(self, fixture)


if __name__ == "__main__":
    unittest.main()
