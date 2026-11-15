# drafted-by: gpt/gpt-6-astra
"""Black-box packet readiness tests. All fixtures live outside the candidate."""

import base64
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


SCRIPTS = Path("plugins/gstack-execution/scripts")
CRITERION = "module.py returns the input plus one."

BASE_FILES = {
    "module.py": b"# dependency.txt\n"
                 b"def increment(value):\n    return value\n",
    "caller.py": b"import module\nresult = module.increment(1)\n",
    "dependency.txt": b"Dependency bytes from the packet head.\n\n",
    "evidence.md": b"Criterion evidence from the packet head.\n\n",
    "removed.txt": b"This file is removed by the reviewed change.\n",
}
HEAD_MODULE = (
    b"# dependency.txt\n"
    b"def increment(value):\n    return value + 1\n\n"
)

# This executable observes the actual CLI review surface. It deliberately returns
# no verdict: these tests examine dispatch and bytes, not reviewer scoring.
REVIEWER_SOURCE = r'''
import base64
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
root = Path(args[args.index("-C") + 1])
with Path(os.environ["PACKET_TEST_CALLS"]).open("a", encoding="utf-8") as log:
    log.write("called\n")
files = {}
for path in sorted(root.rglob("*")):
    if path.is_file():
        files[path.relative_to(root).as_posix()] = base64.b64encode(
            path.read_bytes()
        ).decode("ascii")
Path(os.environ["PACKET_TEST_CAPTURE"]).write_text(
    json.dumps(files), encoding="utf-8"
)
print("fixture reviewer captured the surface", file=sys.stderr)
sys.exit(17)
'''


def _diagnostic(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _git(case, *args):
    result = subprocess.run(
        ["git", "-C", str(case.repo), *args],
        env=case.env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise AssertionError(_diagnostic(result))
    return result.stdout.strip()


def _commit(case, message):
    _git(case, "add", "-A")
    _git(case, "commit", "-qm", message)
    return _git(case, "rev-parse", "HEAD")


def _program(case, script, *args, cwd=None, extra_env=None):
    env = dict(case.env)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-B", str(case.candidate / SCRIPTS / script), *args],
        cwd=str(case.candidate if cwd is None else cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _open(case, packet=None, flags=(), extra_env=None):
    case.packet_file.write_text(
        json.dumps(case.packet if packet is None else packet), encoding="utf-8"
    )
    return _program(
        case,
        "peer_review.py",
        "open",
        "--builder", "claude",
        "--packet", str(case.packet_file),
        "--timeout", "30",
        *flags,
        extra_env=extra_env,
    )


def _tree(root):
    """Snapshot only candidate outputs in the external fixture directory."""
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix():
            None if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


def _assert_opened(test, case, result):
    test.assertEqual(result.returncode, 0, _diagnostic(result))
    state = json.loads(result.stdout)
    test.assertEqual(state["outcome"], "opened", state)
    test.assertEqual(state["rounds_used"], 0, state)
    test.assertTrue(
        (case.reviews / state["review_id"] / "state.json").is_file()
    )
    test.assertFalse(case.calls.exists(), "open dispatched a reviewer")
    return state


def _assert_early_refusal(test, case, packet, message, flags=(), extra_env=None):
    before = _tree(case.reviews)
    result = _open(case, packet, flags, extra_env)
    test.assertEqual(result.returncode, 2, _diagnostic(result))
    test.assertEqual(result.stderr.strip(), message, _diagnostic(result))
    test.assertEqual(result.stdout.strip(), "", _diagnostic(result))
    test.assertEqual(_tree(case.reviews), before, "refusal wrote review state")
    test.assertFalse(case.calls.exists(), "refusal called a reviewer")


def _record_run(case, exit_code=0):
    before = set()
    for path in case.reviews.glob("ledger/**/*.jsonl"):
        before.update(
            json.loads(line)["id"]
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    result = _program(
        case,
        "check_ledger.py",
        "run", "--repo", str(case.repo), "--",
        sys.executable, "-c",
        f"print('fixture check'); raise SystemExit({exit_code})",
        cwd=case.repo,
    )
    if result.returncode != exit_code:
        raise AssertionError(_diagnostic(result))
    added = []
    for path in case.reviews.glob("ledger/**/*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["id"] not in before:
                    added.append((path, row))
    if len(added) != 1:
        raise AssertionError(f"expected one recorded run, found {added!r}")
    return added[0]


def _set_run_head(path, run_id, head):
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        if row["id"] == run_id:
            if head is None:
                row.pop("head", None)
            else:
                row["head"] = head
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


@contextmanager
def _case():
    with tempfile.TemporaryDirectory(prefix="packet-ready-") as directory:
        root = Path(directory).resolve()
        case = SimpleNamespace(
            root=root,
            candidate=Path(os.environ["GOAL_CANDIDATE"]).absolute(),
            repo=root / "repo",
            reviews=root / "reviews",
            packet_file=root / "packet.json",
            calls=root / "reviewer-calls.txt",
            capture=root / "captured-surface.json",
        )
        case.repo.mkdir()
        bin_dir = root / "bin"
        bin_dir.mkdir()
        temp_dir = root / "tmp"
        temp_dir.mkdir()
        reviewer = bin_dir / "codex"
        reviewer.write_text(
            "#!" + sys.executable + "\n" + REVIEWER_SOURCE, encoding="utf-8"
        )
        reviewer.chmod(0o755)

        case.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GSTACK_", "GIT_"))
            and key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        case.env.update({
            "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", os.defpath),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GSTACK_PEER_REVIEW_DIR": str(case.reviews),
            "GSTACK_REVIEWER": "codex",
            "GSTACK_CODEX_MODEL": "gpt-6-astra",
            "PACKET_TEST_CALLS": str(case.calls),
            "PACKET_TEST_CAPTURE": str(case.capture),
            "TMPDIR": str(temp_dir),
            "TMP": str(temp_dir),
            "TEMP": str(temp_dir),
        })
        _git(case, "init", "-q")
        _git(case, "checkout", "-qb", "packet-head")
        for key, value in (
            ("user.name", "Packet Fixture"),
            ("user.email", "packet@example.invalid"),
            ("commit.gpgsign", "false"),
            ("core.autocrlf", "false"),
            ("core.hooksPath", str(root / "no-hooks")),
            ("maintenance.auto", "false"),
            ("gc.auto", "0"),
        ):
            _git(case, "config", key, value)
        for name, data in BASE_FILES.items():
            (case.repo / name).write_bytes(data)
        case.base = _commit(case, "base")
        (case.repo / "module.py").write_bytes(HEAD_MODULE)
        case.head = _commit(case, "reviewed change")
        case.packet = {
            "outcome": "Increment the input by one.",
            "acceptance_criteria": [CRITERION],
            "repos": [{
                "path": str(case.repo),
                "base": case.base,
                "head": case.head,
            }],
            "changed_behavior": "The increment function adds one.",
            "exclusions": [],
            "tests": {
                "commands": [],
                "results": "Deterministic packet fixture.",
                "environment": "isolated temporary repository",
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
        yield case


class PacketReady(unittest.TestCase):
    def test_open_refuses_missing_data_use_before_dispatch(self):
        """Scenario: Given a packet with no data_use block, when peer_review.py open runs, then it refuses before any reviewer is called and names data_use"""
        with _case() as case:
            for session in (False, True):
                env = {"GSTACK_PEER_REVIEW_SESSION": "1"} if session else {}
                for policy in ("absent", "empty", "denied"):
                    with self.subTest(session=session, policy=policy):
                        packet = copy.deepcopy(case.packet)
                        if policy == "absent":
                            packet.pop("data_use")
                        elif policy == "empty":
                            packet["data_use"] = {}
                        else:
                            packet["data_use"]["allowed_tools"] = ["claude"]
                        message = (
                            "refused: data_use: denied: "
                            "data_use: tool destination denied: codex"
                            if policy == "denied"
                            else "refused: data_use: missing"
                        )
                        _assert_early_refusal(
                            self, case, packet, message, extra_env=env
                        )

                with self.subTest(session=session, precedence="data_use"):
                    packet = copy.deepcopy(case.packet)
                    packet.pop("data_use")
                    packet.pop("coverage")
                    packet["acceptance_criteria"] = []
                    _assert_early_refusal(
                        self, case, packet, "refused: data_use: missing",
                        flags=("--max-rounds", "0"), extra_env=env,
                    )

                for coverage in ("absent", "empty"):
                    with self.subTest(session=session, coverage=coverage):
                        packet = copy.deepcopy(case.packet)
                        if coverage == "absent":
                            packet.pop("coverage")
                        else:
                            packet["coverage"] = {}
                        # Coverage must win over both validation and session guards.
                        packet["acceptance_criteria"] = []
                        _assert_early_refusal(
                            self, case, packet, "refused: coverage: not attached",
                            flags=("--max-rounds", "0"), extra_env=env,
                        )

    def test_open_refuses_ledger_run_behind_head(self):
        """Scenario: Given a packet whose named ledger run is at a commit older than the head being sent, when open runs, then it refuses and names the ledger run and both commits"""
        with _case() as case:
            _git(case, "checkout", "-qb", "old-evidence", case.base)
            stale_path, stale = _record_run(case)
            self.assertEqual(stale["head"], case.base)
            _git(case, "checkout", "-q", "packet-head")
            _, fresh = _record_run(case)
            self.assertEqual(fresh["head"], case.head)

            packet = copy.deepcopy(case.packet)
            packet["tests"]["ledger_runs"] = [
                {"repo": str(case.repo), "run_id": fresh["id"]},
                {"repo": str(case.repo), "run_id": stale["id"]},
            ]
            # The checkout agrees with the stale run, but the packet does not.
            _git(case, "checkout", "-q", "old-evidence")
            self.assertEqual(_git(case, "rev-parse", "HEAD"), case.base)

            for recorded_head in (case.base, case.head[:12], None):
                _set_run_head(stale_path, stale["id"], recorded_head)
                for session in (False, True):
                    with self.subTest(recorded_head=recorded_head, session=session):
                        env = (
                            {"GSTACK_PEER_REVIEW_SESSION": "1"} if session else {}
                        )
                        shown = recorded_head if recorded_head is not None else "none"
                        _assert_early_refusal(
                            self, case, packet,
                            f"refused: tests.ledger_runs: run {stale['id']} "
                            f"is at {shown}, head is {case.head}",
                            extra_env=env,
                        )

            _set_run_head(stale_path, stale["id"], case.base)
            with self.subTest(precedence="coverage-before-ledger"):
                missing_coverage = copy.deepcopy(packet)
                missing_coverage.pop("coverage")
                _assert_early_refusal(
                    self, case, missing_coverage,
                    "refused: coverage: not attached",
                    extra_env={"GSTACK_PEER_REVIEW_SESSION": "1"},
                )

            # The same early gate must protect a first round's explicit head.
            with self.subTest(first_round_head_override=True):
                clean = copy.deepcopy(case.packet)
                clean["repos"][0]["head"] = case.base
                clean["repos"][0]["base"] = case.head
                clean["tests"]["ledger_runs"] = [
                    {"repo": str(case.repo), "run_id": stale["id"]}
                ]
                state = _assert_opened(self, case, _open(case, clean))
                before = _tree(case.reviews)
                result = _program(
                    case, "peer_review.py", "round", state["review_id"],
                    "--head", f"{case.repo}={case.head}",
                    "--ledger-run", f"{case.repo}={stale['id']}",
                    extra_env={"GSTACK_PEER_REVIEW_SESSION": "1"},
                )
                self.assertEqual(result.returncode, 2, _diagnostic(result))
                self.assertEqual(
                    result.stderr.strip(),
                    f"refused: tests.ledger_runs: run {stale['id']} "
                    f"is at {case.base}, head is {case.head}",
                )
                self.assertEqual(_tree(case.reviews), before)
                self.assertFalse(case.calls.exists())

    def test_surface_shows_head_commit_bytes_from_other_branch(self):
        """Scenario: Given a checkout sitting on a different branch from the packet's head, when open builds the reviewer's surface, then every changed file shows the head commit's bytes"""
        with _case() as case:
            changed = {
                "module.py": HEAD_MODULE,
                "head_only.py": b"VALUE = 'present only at the packet head'\n\n",
                "with space.txt": b"Head bytes for a space in the filename.\n\n",
                "with\ttab.txt": b"Head bytes for a tab in the filename.\n\n",
                "with\nnewline.txt": b"Head bytes for a newline in the filename.\n\n",
            }
            for name, data in changed.items():
                (case.repo / name).write_bytes(data)
            (case.repo / "removed.txt").unlink()
            case.head = _commit(case, "head-only files and unusual names")
            case.packet["repos"][0]["head"] = case.head
            case.packet["acceptance_criteria"].append(
                "evidence.md supplies the criterion evidence."
            )

            _git(case, "checkout", "-qb", "other-branch", case.base)
            wrong = b"Other branch bytes must never reach the reviewer.\n"
            for name in ("module.py", "caller.py", "dependency.txt", "removed.txt"):
                (case.repo / name).write_bytes(wrong)
            (case.repo / "evidence.md").unlink()
            (case.repo / "worktree_only.py").write_bytes(b"import module\n")
            _commit(case, "different branch content")
            self.assertNotEqual(_git(case, "rev-parse", "HEAD"), case.head)
            # Also distinguish committed head bytes from uncommitted bytes.
            (case.repo / "module.py").write_bytes(
                b"Uncommitted checkout content must not be reviewed.\n"
            )

            state = _assert_opened(self, case, _open(case))
            result = _program(
                case, "peer_review.py", "round", state["review_id"]
            )
            self.assertTrue(case.capture.is_file(), _diagnostic(result))
            self.assertEqual(
                case.calls.read_text(encoding="utf-8").splitlines(), ["called"]
            )
            captured = {
                name: base64.b64decode(data)
                for name, data in json.loads(
                    case.capture.read_text(encoding="utf-8")
                ).items()
            }
            for name, expected in changed.items():
                with self.subTest(changed_file=name):
                    path = "changed/0-repo/" + name
                    self.assertIn(path, captured)
                    self.assertEqual(captured[path], expected)

            for path, expected in (
                ("callers/0-repo/caller.py", BASE_FILES["caller.py"]),
                ("dependencies/0-repo/dependency.txt", BASE_FILES["dependency.txt"]),
                ("dependencies/0-repo/evidence.md", BASE_FILES["evidence.md"]),
            ):
                with self.subTest(supporting_file=path):
                    self.assertIn(path, captured)
                    self.assertEqual(captured[path], expected)

            self.assertFalse(
                any(name.endswith("/worktree_only.py") for name in captured),
                "caller discovery used the other branch's tracked files",
            )
            self.assertNotIn(wrong, captured.values())
            self.assertNotIn(
                b"Uncommitted checkout content must not be reviewed.\n",
                captured.values(),
            )
            self.assertNotEqual(
                captured.get("changed/0-repo/removed.txt"), wrong,
                "a file deleted at the packet head was read from the checkout",
            )

    def test_complete_packet_still_opens_and_refused_stays_refused(self):
        """Scenario: A complete packet at its head being refused, or a packet that is refused today being dispatched, must never happen"""
        with _case() as case:
            _, run = _record_run(case)
            case.packet["tests"]["ledger_runs"] = [
                {"repo": str(case.repo), "run_id": run["id"]}
            ]
            state = _assert_opened(self, case, _open(case))
            self.assertEqual(state["heads"], [[case.head]])
            self.assertTrue(state["coverage_checked"])
            self.assertEqual(state["reviewer"], "codex")

            refusals = []

            packet = copy.deepcopy(case.packet)
            packet["acceptance_criteria"] = []
            refusals.append(("empty criteria", packet, (), {}, "malformed_packet"))

            packet = copy.deepcopy(case.packet)
            packet["repos"][0]["base"] = case.head
            refusals.append(("no change", packet, (), {}, "missing_commits"))

            packet = copy.deepcopy(case.packet)
            packet["coverage"]["criteria"][0]["probability"] = 0.1
            refusals.append((
                "narrow coverage", packet, (), {}, "packet_narrower_than_item"
            ))

            refusals.append((
                "invalid round budget", copy.deepcopy(case.packet),
                ("--max-rounds", "4"), {}, "malformed_packet",
            ))
            refusals.append((
                "same reviewer family", copy.deepcopy(case.packet), (),
                {"GSTACK_REVIEWER": "claude"}, "reviewer_not_independent",
            ))
            refusals.append((
                "reviewer session", copy.deepcopy(case.packet), (),
                {"GSTACK_PEER_REVIEW_SESSION": "1"}, "review",
            ))

            for name, packet, flags, env, reason in refusals:
                with self.subTest(existing_refusal=name):
                    before = _tree(case.reviews)
                    result = _open(case, packet, flags, env)
                    self.assertNotEqual(result.returncode, 0, _diagnostic(result))
                    self.assertIn(reason, result.stderr, _diagnostic(result))
                    self.assertEqual(_tree(case.reviews), before)
                    self.assertFalse(case.calls.exists())

            with self.subTest(override="narrow coverage"):
                packet = copy.deepcopy(case.packet)
                packet["coverage"]["criteria"][0]["probability"] = 0.1
                packet["exclusions"] = ["Fixture explicitly accepts narrow coverage."]
                state = _assert_opened(
                    self, case,
                    _open(case, packet, flags=("--accept-narrow-packet",)),
                )
                self.assertTrue(state["coverage_overridden"])

            with self.subTest(override="no coverage"):
                packet = copy.deepcopy(case.packet)
                packet.pop("coverage")
                packet["exclusions"] = ["Fixture scores no design items."]
                _assert_opened(
                    self, case,
                    _open(case, packet, flags=("--accept-narrow-packet",)),
                )

            with self.subTest(attached_report="unavailable"):
                packet = copy.deepcopy(case.packet)
                packet["coverage"] = {
                    "status": "unavailable",
                    "why": "Fixture scorer unavailable.",
                }
                state = _assert_opened(self, case, _open(case, packet))
                self.assertFalse(state["coverage_checked"])

            with self.subTest(existing_refusal="open check failure"):
                _record_run(case, exit_code=7)
                before = _tree(case.reviews)
                result = _open(case)
                self.assertNotEqual(result.returncode, 0, _diagnostic(result))
                self.assertIn("open_check_failure", result.stderr)
                self.assertEqual(_tree(case.reviews), before)
                self.assertFalse(case.calls.exists())

                reason = "Fixture failure is deliberately retained for this test."
                state = _assert_opened(
                    self, case,
                    _open(case, flags=("--accept-open-failure", reason)),
                )
                self.assertEqual(state["open_failures_overridden"], reason)
                self.assertEqual(state["ledger_status"], "overridden")


if __name__ == "__main__":
    unittest.main()
