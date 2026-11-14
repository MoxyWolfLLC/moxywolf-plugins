# drafted-by: gpt/gpt-6-astra
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from types import SimpleNamespace


SCRIPTS = Path("plugins/gstack-execution/scripts")
CRITERION = "src/value.js supplies the revised value; docs/evidence.md describes it."

BASE_FILES = {
    "src/value.js": b"import { delta } from './dep.js';\nexport const value = delta;\n",
    "src/dep.js": b"export const delta = 1;\n",
    "src/caller.js": b"import { value } from './value.js';\nexport const result = value;\n",
    "src/removed.js": b"export const obsolete = true;\n",
    "docs/evidence.md": b"The value is incremented by one.\n",
}
HEAD_FILES = {
    "src/value.js": b"import { delta } from './dep.js';\nexport const value = delta + 1;\n",
    "src/added.js": b"export const addedAtPacketHead = true;\n",
}

REVIEWER_SOURCE = r"""
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
root = Path(args[args.index("-C") + 1]) if "-C" in args else Path.cwd()
files = {
    p.relative_to(root).as_posix(): p.read_bytes().hex()
    for p in root.rglob("*")
    if p.is_file()
}
Path(os.environ["PACKET_READY_CAPTURE"]).write_text(json.dumps(files))
with Path(os.environ["PACKET_READY_CALLS"]).open("a") as stream:
    stream.write("called\n")
# Capturing the offered surface is sufficient; this stub grants no approval.
if "--output-last-message" in args:
    Path(args[args.index("--output-last-message") + 1]).write_text("{}")
print("model: gpt-6-astra", file=sys.stderr)
print("{}")
"""


def _run(argv, cwd, env):
    return subprocess.run(
        [str(arg) for arg in argv],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _successful(result):
    if result.returncode:
        raise AssertionError(
            f"Command exited {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def _git(fixture, *args):
    return _successful(_run(["git", *args], fixture.repo, fixture.env))


def _write_files(repo, files):
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _snapshot(root):
    return {
        path.relative_to(root).as_posix(): (
            ("directory",) if path.is_dir() else ("file", path.read_bytes())
        )
        for path in root.rglob("*")
    }


@contextmanager
def _fixture():
    candidate = Path(os.environ["GOAL_CANDIDATE"]).resolve()
    with tempfile.TemporaryDirectory(prefix="packet-ready-", dir="/tmp") as temporary:
        root = Path(temporary).resolve()
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GSTACK_", "GIT_"))
        }
        fixture = SimpleNamespace(
            candidate=candidate,
            root=root,
            repo=root / "repo",
            reviews=root / "reviews",
            packet_file=root / "packet.json",
            capture=root / "captured-surface.json",
            calls=root / "reviewer-calls.txt",
            env=env,
        )
        binary_dir = root / "bin"
        temporary_dir = root / "temporary"
        for directory in (fixture.repo, fixture.reviews, binary_dir, temporary_dir):
            directory.mkdir()
        reviewer = binary_dir / "codex"
        reviewer.write_text("#!" + sys.executable + "\n" + REVIEWER_SOURCE)
        reviewer.chmod(0o755)
        env.update({
            "PATH": str(binary_dir) + os.pathsep + os.environ.get("PATH", ""),
            "TMPDIR": str(temporary_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GSTACK_PEER_REVIEW_DIR": str(fixture.reviews),
            "GSTACK_REVIEWER": "codex",
            "GSTACK_CODEX_MODEL": "gpt-6-astra",
            "PACKET_READY_CAPTURE": str(fixture.capture),
            "PACKET_READY_CALLS": str(fixture.calls),
        })
        _git(fixture, "init", "-q", "-b", "packet")
        _git(fixture, "config", "user.email", "packet-ready@example.invalid")
        _git(fixture, "config", "user.name", "Packet Ready Fixture")
        _git(fixture, "config", "commit.gpgsign", "false")
        _git(fixture, "config", "core.hooksPath", str(root / "no-hooks"))
        _write_files(fixture.repo, BASE_FILES)
        _git(fixture, "add", ".")
        _git(fixture, "commit", "-qm", "base")
        fixture.base = _git(fixture, "rev-parse", "HEAD")
        _write_files(fixture.repo, HEAD_FILES)
        (fixture.repo / "src/removed.js").unlink()
        _git(fixture, "add", "-A")
        _git(fixture, "commit", "-qm", "packet head")
        fixture.head = _git(fixture, "rev-parse", "HEAD")
        fixture.packet = {
            "outcome": "Increment the exported value.",
            "acceptance_criteria": [CRITERION],
            "repos": [{
                "path": str(fixture.repo),
                "base": fixture.base,
                "head": fixture.head,
            }],
            "changed_behavior": "The exported value adds one to delta.",
            "exclusions": [],
            "tests": {
                "commands": [],
                "results": "",
                "environment": "isolated offline fixture",
                "ledger_runs": [],
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
                "criteria": [{
                    "item": "fixture",
                    "criterion_no": 1,
                    "declared": CRITERION,
                    "probability": 1.0,
                }],
            },
        }
        yield fixture


def _peer(fixture, *args, env=None):
    return _run(
        [sys.executable, SCRIPTS / "peer_review.py", *args],
        fixture.candidate,
        fixture.env if env is None else env,
    )


def _open(fixture, packet=None, *flags, env=None):
    fixture.packet_file.write_text(json.dumps(
        fixture.packet if packet is None else packet
    ))
    return _peer(
        fixture,
        "open",
        "--builder", "claude",
        "--packet", str(fixture.packet_file),
        "--timeout", "30",
        *flags,
        env=env,
    )


def _ledger_run(fixture, code="print('packet check passed')", expected_exit=0):
    before = {
        row["id"]
        for path in fixture.reviews.rglob("*.jsonl")
        for line in path.read_text().splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }
    result = _run(
        [
            sys.executable,
            fixture.candidate / SCRIPTS / "check_ledger.py",
            "run", "--repo", fixture.repo, "--",
            sys.executable, "-c", code,
        ],
        fixture.repo,
        fixture.env,
    )
    if result.returncode != expected_exit:
        raise AssertionError(
            f"Ledger command exited {result.returncode}, expected {expected_exit}: "
            f"{result.stdout}\n{result.stderr}"
        )
    new_rows = [
        (path, json.loads(line))
        for path in fixture.reviews.rglob("*.jsonl")
        for line in path.read_text().splitlines()
        if line.strip() and json.loads(line)["id"] not in before
    ]
    if len(new_rows) != 1:
        raise AssertionError(f"Expected one new ledger record, got {new_rows!r}")
    return new_rows[0]


def _name_run(fixture, row, packet=None):
    target = fixture.packet if packet is None else packet
    target["tests"]["ledger_runs"] = [{
        "repo": str(fixture.repo),
        "run_id": row["id"],
    }]


def _assert_opened(test, fixture, packet=None, *flags):
    result = _open(fixture, packet, *flags)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    state = json.loads(result.stdout)
    test.assertEqual(state["outcome"], "opened", state)
    test.assertEqual(state["rounds_used"], 0)
    test.assertEqual(state["reviewer"], "codex")
    test.assertTrue((fixture.reviews / state["review_id"] / "state.json").is_file())
    test.assertFalse(fixture.calls.exists(), "open called the reviewer")
    return state


def _assert_new_refusal(test, fixture, result, before, message):
    test.assertEqual(result.returncode, 2, result.stdout + result.stderr)
    test.assertEqual(result.stderr.strip(), message)
    test.assertEqual(result.stdout.strip(), "")
    test.assertEqual(_snapshot(fixture.reviews), before)
    test.assertFalse(fixture.calls.exists(), "a refused packet reached the reviewer")


class PacketReady(unittest.TestCase):
    def test_open_refuses_missing_data_use_before_dispatch(self):
        """Scenario: Given a packet with no data_use block, when peer_review.py open runs, then it refuses before any reviewer is called and names data_use"""
        cases = (
            "missing",
            "empty",
            "denied",
            "missing-before-coverage-and-validation",
            "coverage-missing",
            "coverage-empty",
        )
        for case in cases:
            with self.subTest(case=case), _fixture() as fixture:
                packet = copy.deepcopy(fixture.packet)
                flags = []
                if case in ("missing", "missing-before-coverage-and-validation"):
                    packet.pop("data_use")
                    message = "refused: data_use: missing"
                elif case == "empty":
                    packet["data_use"] = {}
                    message = "refused: data_use: missing"
                elif case == "denied":
                    packet["data_use"]["allowed_tools"] = ["claude"]
                    message = (
                        "refused: data_use: denied: "
                        "data_use: tool destination denied: codex"
                    )
                else:
                    if case == "coverage-missing":
                        packet.pop("coverage")
                    else:
                        packet["coverage"] = {}
                    message = "refused: coverage: not attached"
                if case == "missing-before-coverage-and-validation":
                    packet.pop("coverage")
                    packet.pop("release_owner")
                    flags = ["--max-rounds", "0"]
                before = _snapshot(fixture.reviews)
                result = _open(fixture, packet, *flags)
                _assert_new_refusal(self, fixture, result, before, message)

    def test_open_refuses_ledger_run_behind_head(self):
        """Scenario: Given a packet whose named ledger run is at a commit older than the head being sent, when open runs, then it refuses and names the ledger run and both commits"""
        for case in ("older-commit", "abbreviated-commit", "missing-commit"):
            with self.subTest(case=case), _fixture() as fixture:
                if case == "older-commit":
                    _git(fixture, "checkout", "-qb", "older", fixture.base)
                ledger_path, row = _ledger_run(fixture)
                _name_run(fixture, row)
                recorded = copy.deepcopy(row)
                if case == "abbreviated-commit":
                    recorded["head"] = fixture.head[:12]
                elif case == "missing-commit":
                    recorded.pop("head")
                ledger_path.write_text(json.dumps(recorded) + "\n")
                run_head = recorded.get("head", "none")
                if case == "older-commit":
                    self.assertEqual(run_head, fixture.base)
                    self.assertNotEqual(run_head, fixture.head)
                    # The checkout agrees with the stale run, not the packet.
                    self.assertEqual(_git(fixture, "rev-parse", "HEAD"), run_head)
                before = _snapshot(fixture.reviews)
                result = _open(fixture)
                _assert_new_refusal(
                    self, fixture, result, before,
                    f"refused: tests.ledger_runs: run {row['id']} "
                    f"is at {run_head}, head is {fixture.head}",
                )

        with self.subTest(case="first-round-head-override"), _fixture() as fixture:
            _, row = _ledger_run(fixture)
            _name_run(fixture, row)
            state = _assert_opened(self, fixture)
            _write_files(fixture.repo, {
                "src/value.js": b"export const value = 3;\n",
            })
            _git(fixture, "add", ".")
            _git(fixture, "commit", "-qm", "later head")
            later = _git(fixture, "rev-parse", "HEAD")
            before = _snapshot(fixture.reviews)
            result = _peer(
                fixture, "round", state["review_id"],
                "--head", f"{fixture.repo}={later}",
                "--ledger-run", f"{fixture.repo}={row['id']}",
            )
            _assert_new_refusal(
                self, fixture, result, before,
                f"refused: tests.ledger_runs: run {row['id']} "
                f"is at {fixture.head}, head is {later}",
            )

    def test_surface_shows_head_commit_bytes_from_other_branch(self):
        """Scenario: Given a checkout sitting on a different branch from the packet's head, when open builds the reviewer's surface, then every changed file shows the head commit's bytes"""
        with _fixture() as fixture:
            _, row = _ledger_run(fixture)
            _name_run(fixture, row)
            _git(fixture, "checkout", "-qb", "other", fixture.base)
            poison = b"OTHER_BRANCH_BYTES_MUST_NOT_REACH_REVIEWER"
            _write_files(fixture.repo, {
                "src/value.js": b"// " + poison + b"\nexport const value = -999;\n",
                "src/removed.js": b"// " + poison + b"\n",
                "docs/evidence.md": poison + b"\n",
            })
            _git(fixture, "rm", "-q", "src/dep.js", "src/caller.js")
            _git(fixture, "add", "-A")
            _git(fixture, "commit", "-qm", "different checkout")
            self.assertNotEqual(_git(fixture, "rev-parse", "HEAD"), fixture.head)

            state = _assert_opened(self, fixture)
            result = _peer(fixture, "round", state["review_id"])
            self.assertTrue(
                fixture.capture.is_file(),
                "Reviewer never received a surface:\n"
                + result.stdout + result.stderr,
            )
            self.assertEqual(fixture.calls.read_text().splitlines(), ["called"])
            captured = {
                name: bytes.fromhex(content)
                for name, content in json.loads(fixture.capture.read_text()).items()
            }
            expected = {
                "changed/0-repo/src/value.js": HEAD_FILES["src/value.js"],
                "changed/0-repo/src/added.js": HEAD_FILES["src/added.js"],
                "callers/0-repo/src/caller.js": BASE_FILES["src/caller.js"],
                "dependencies/0-repo/src/dep.js": BASE_FILES["src/dep.js"],
                "dependencies/0-repo/docs/evidence.md": BASE_FILES["docs/evidence.md"],
            }
            for name, content in expected.items():
                with self.subTest(surface_file=name):
                    self.assertIn(name, captured)
                    self.assertEqual(captured[name], content)
            for name, content in captured.items():
                self.assertNotIn(poison, content, f"Checkout bytes leaked into {name}")
            self.assertIn("src/removed.js", captured["CHANGE.diff"].decode())

    def test_complete_packet_still_opens_and_refused_stays_refused(self):
        """Scenario: A complete packet at its head being refused, or a packet that is refused today being dispatched, must never happen"""
        with _fixture() as fixture:
            _, row = _ledger_run(fixture)
            self.assertEqual(row["head"], fixture.head)
            _name_run(fixture, row)
            state = _assert_opened(self, fixture)
            self.assertTrue(state["coverage_checked"])
            self.assertEqual(state["heads"], [[fixture.head]])

        cases = (
            ("narrow", "packet_narrower_than_item"),
            ("unchanged", "missing_commits"),
            ("missing-owner", "malformed_packet"),
            ("invalid-round-limit", "malformed_packet"),
            ("same-family-reviewer", "reviewer_not_independent"),
            ("open-check-failure", "open_check_failure"),
        )
        for case, refusal in cases:
            with self.subTest(case=case), _fixture() as fixture:
                _, row = _ledger_run(fixture)
                _name_run(fixture, row)
                packet = copy.deepcopy(fixture.packet)
                flags = []
                env = dict(fixture.env)
                if case == "narrow":
                    packet["coverage"]["criteria"][0]["probability"] = 0.0
                    packet["exclusions"] = ["This fixture deliberately narrows coverage."]
                elif case == "unchanged":
                    packet["repos"][0]["base"] = fixture.head
                elif case == "missing-owner":
                    packet.pop("release_owner")
                elif case == "invalid-round-limit":
                    flags = ["--max-rounds", "4"]
                elif case == "same-family-reviewer":
                    env["GSTACK_REVIEWER"] = "claude"
                else:
                    _ledger_run(fixture, "import sys; sys.exit(7)", expected_exit=7)

                before = _snapshot(fixture.reviews)
                result = _open(fixture, packet, *flags, env=env)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                # An earlier data-use gate may also reject the missing owner.
                if case != "missing-owner":
                    self.assertIn(refusal, result.stderr)
                else:
                    self.assertTrue(result.stderr.strip())
                self.assertEqual(_snapshot(fixture.reviews), before)
                self.assertFalse(fixture.calls.exists())

                if case == "narrow":
                    state = _assert_opened(
                        self, fixture, packet, "--accept-narrow-packet"
                    )
                    self.assertTrue(state["coverage_overridden"])
                elif case == "open-check-failure":
                    reason = "The fixture intentionally preserves this failing check."
                    state = _assert_opened(
                        self, fixture, packet, "--accept-open-failure", reason
                    )
                    self.assertEqual(state["open_failures_overridden"], reason)

        with self.subTest(case="missing-coverage-override"), _fixture() as fixture:
            packet = copy.deepcopy(fixture.packet)
            packet.pop("coverage")
            packet["exclusions"] = ["This narrow fixture scores no design items."]
            _assert_opened(self, fixture, packet, "--accept-narrow-packet")


if __name__ == "__main__":
    unittest.main()
