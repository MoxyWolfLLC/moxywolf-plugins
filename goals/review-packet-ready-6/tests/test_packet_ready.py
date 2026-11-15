# drafted-by: gpt/gpt-6-astra
"""Black-box packet-readiness tests using disposable repositories and CLI calls."""

import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


SCRIPTS = "plugins/gstack-execution/scripts"
CRITERION = "`widget.py` returns 2; `evidence.txt` describes the expected behavior."
HEAD_WIDGET = '# Dependency: settings.json\n\ndef make():\n    return 2\n'
HEAD_CALLER = "import widget\nassert widget.make() == 2\n"
HEAD_SETTINGS = '{"expected": 2}\n'
HEAD_EVIDENCE = "The expected result is 2.\n"

# This executable observes the actual CLI dispatch boundary. It only reads the
# temporary review surface passed through -C, never the candidate checkout.
REVIEWER = r"""
import base64
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
root = Path(args[args.index("-C") + 1])
files = {}
for group in ("changed", "callers", "dependencies"):
    directory = root / group
    if directory.exists():
        for path in directory.rglob("*"):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = (
                    base64.b64encode(path.read_bytes()).decode("ascii")
                )
with open(os.environ["PACKET_TEST_CALLS"], "a", encoding="utf-8") as out:
    out.write(json.dumps({"files": files}) + "\n")

# No review verdict is needed to observe dispatch. Deliberately stop after
# capturing the surface so these tests do not depend on scoring or read tracking.
print("packet test observer finished", file=sys.stderr)
sys.exit(23)
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


def _diagnostic(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _git(case, fixture, *args):
    result = _run(["git", "-C", fixture.repo, *args],
                  fixture.root, fixture.env)
    case.assertEqual(result.returncode, 0, _diagnostic(result))
    return result.stdout.strip()


def _commit(case, fixture, message):
    _git(case, fixture, "add", "-A")
    _git(case, fixture, "commit", "-qm", message)
    return _git(case, fixture, "rev-parse", "HEAD")


def _fixture(case, directory, unusual=False):
    root = Path(directory)
    candidate = Path(os.path.abspath(os.environ["GOAL_CANDIDATE"]))
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GSTACK_", "GOAL_", "GIT_"))
        and key not in {"PYTHONPATH", "PYTHONHOME"}
    }
    reviews = root / "reviews"
    calls = root / "reviewer-calls.jsonl"
    binaries = root / "bin"
    scratch = root / "scratch"
    binaries.mkdir()
    scratch.mkdir()
    observer = binaries / "codex"
    observer.write_text(
        "#!" + sys.executable + "\n" + REVIEWER, encoding="utf-8"
    )
    observer.chmod(0o755)
    env.update({
        "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
        "GSTACK_PEER_REVIEW_DIR": str(reviews),
        "GSTACK_REVIEWER": "codex",
        "GSTACK_CODEX_MODEL": "gpt-6-astra",
        "PACKET_TEST_CALLS": str(calls),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "TMPDIR": str(scratch),
    })
    repo = root / "repo"
    repo.mkdir()
    fixture = SimpleNamespace(
        root=root, candidate=candidate, repo=repo, reviews=reviews,
        calls=calls, env=env, unusual={},
    )
    _git(case, fixture, "init", "-q", "-b", "build/packet")
    for key, value in (
        ("user.name", "Packet Test"),
        ("user.email", "packet@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", str(root / "no-hooks")),
        ("maintenance.auto", "false"),
        ("gc.auto", "0"),
    ):
        _git(case, fixture, "config", key, value)

    (repo / "widget.py").write_text(
        '# Dependency: settings.json\n\ndef make():\n    return 1\n',
        encoding="utf-8",
    )
    (repo / "caller.py").write_text(HEAD_CALLER, encoding="utf-8")
    (repo / "settings.json").write_text(HEAD_SETTINGS, encoding="utf-8")
    (repo / "evidence.txt").write_text(HEAD_EVIDENCE, encoding="utf-8")
    fixture.base = _commit(case, fixture, "base")

    (repo / "widget.py").write_text(HEAD_WIDGET, encoding="utf-8")
    if unusual:
        fixture.unusual = {
            "introduced.py": b"INTRODUCED = 'head only'\n",
            "space name.txt": b"space-name head bytes\n",
            "tab\tname.txt": b"tab-name head bytes\n",
            "line\nname.txt": b"newline-name head bytes\n",
        }
        for name, body in fixture.unusual.items():
            (repo / name).write_bytes(body)
    fixture.head = _commit(case, fixture, "packet head")
    case.assertRegex(fixture.head, r"^[0-9a-f]{40}$")
    return fixture


def _packet(fixture, run_id):
    return {
        "outcome": "The widget returns the expected value.",
        "acceptance_criteria": [CRITERION],
        "repos": [{
            "path": str(fixture.repo),
            "base": fixture.base,
            "head": fixture.head,
        }],
        "changed_behavior": "The widget now returns 2.",
        "exclusions": [],
        "tests": {
            "commands": ["fixture check"],
            "results": "The recorded fixture check passed.",
            "environment": "Disposable offline repository.",
            "ledger_runs": [{
                "repo": str(fixture.repo),
                "run_id": run_id,
            }],
        },
        "release_owner": "packet-test-owner",
        "data_use": {
            "owner": "packet-test-owner",
            "classification": "test",
            "allow_repository": True,
            "allow_history": True,
            "allowed_tools": ["codex", "claude"],
        },
        "coverage": {
            "status": "checked",
            "criteria": [{
                "item": "packet-fixture",
                "criterion_no": 1,
                "declared": CRITERION,
                "probability": 1.0,
            }],
        },
    }


def _record_run(case, fixture, exit_code=0):
    # check_ledger requires both a named branch and a cwd inside this fixture
    # repository. Only the executable path points into GOAL_CANDIDATE.
    branch = _git(case, fixture, "symbolic-ref", "--short", "HEAD")
    case.assertTrue(branch)
    result = _run(
        [
            sys.executable,
            fixture.candidate / SCRIPTS / "check_ledger.py",
            "run", "--repo", fixture.repo, "--",
            sys.executable, "-c",
            f"import sys; print('fixture check'); sys.exit({exit_code})",
        ],
        fixture.repo,
        fixture.env,
    )
    case.assertEqual(result.returncode, exit_code, _diagnostic(result))
    ledger = fixture.reviews / "ledger" / "repo" / (branch + ".jsonl")
    case.assertTrue(ledger.is_file(), _diagnostic(result))
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    case.assertEqual(row["head"], _git(case, fixture, "rev-parse", "HEAD"))
    case.assertEqual(row["exit_code"], exit_code)
    return row["id"]


def _peer(fixture, *args, extra_env=None):
    env = dict(fixture.env)
    env.update(extra_env or {})
    return _run(
        [sys.executable, fixture.candidate / SCRIPTS / "peer_review.py", *args],
        fixture.candidate,
        env,
    )


def _open(fixture, packet, *flags, extra_env=None):
    packet_file = fixture.root / "packet.json"
    packet_file.write_text(json.dumps(packet), encoding="utf-8")
    return _peer(
        fixture, "open", "--builder", "claude",
        "--packet", packet_file, "--timeout", "20", *flags,
        extra_env=extra_env,
    )


def _tree(root):
    if not root.exists():
        return None
    return {
        path.relative_to(root).as_posix():
            None if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


def _refused_without_writes(case, fixture, result, before, message,
                            exact=False):
    if exact:
        case.assertEqual(result.returncode, 2, _diagnostic(result))
        case.assertEqual(result.stderr.strip(), message, _diagnostic(result))
    else:
        case.assertNotEqual(result.returncode, 0, _diagnostic(result))
        case.assertIn(message, result.stderr, _diagnostic(result))
    case.assertEqual(result.stdout.strip(), "", _diagnostic(result))
    case.assertEqual(_tree(fixture.reviews), before,
                     "A refusal created or changed review-directory contents.")
    case.assertFalse(fixture.calls.exists(), "A refused packet called a reviewer.")


def _opened(case, fixture, packet, *flags):
    result = _open(fixture, packet, *flags)
    case.assertEqual(result.returncode, 0, _diagnostic(result))
    state = json.loads(result.stdout)
    case.assertEqual(state["outcome"], "opened")
    case.assertEqual(state["rounds_used"], 0)
    case.assertEqual(state["heads"], [[packet["repos"][0]["head"]]])
    retained = fixture.reviews / state["review_id"] / "state.json"
    case.assertEqual(
        json.loads(retained.read_text(encoding="utf-8"))["outcome"], "opened"
    )
    return state


class PacketReady(unittest.TestCase):
    def test_open_refuses_missing_data_use_before_dispatch(self):
        """
        Scenario: Given a packet with no data_use block, when peer_review.py open runs, then it refuses before any reviewer is called and names data_use
        """
        with tempfile.TemporaryDirectory(prefix="packet-data-use-") as directory:
            fixture = _fixture(self, directory)
            run_id = _record_run(self, fixture)
            complete = _packet(fixture, run_id)

            for empty in (False, True):
                for reviewer_session in (False, True):
                    with self.subTest(empty=empty, session=reviewer_session):
                        packet = copy.deepcopy(complete)
                        if empty:
                            packet["data_use"] = {}
                        else:
                            packet.pop("data_use")
                        flags = ()
                        extra_env = {}
                        if reviewer_session:
                            # The new field check must precede all of these
                            # independently invalid conditions.
                            packet.pop("coverage")
                            packet.pop("acceptance_criteria")
                            flags = ("--max-rounds", "0")
                            extra_env["GSTACK_PEER_REVIEW_SESSION"] = "1"
                        before = _tree(fixture.reviews)
                        result = _open(
                            fixture, packet, *flags, extra_env=extra_env
                        )
                        _refused_without_writes(
                            self, fixture, result, before,
                            "refused: data_use: missing", exact=True,
                        )

            with self.subTest(data_use="denies chosen reviewer"):
                packet = copy.deepcopy(complete)
                packet["data_use"]["allowed_tools"] = ["claude"]
                before = _tree(fixture.reviews)
                result = _open(fixture, packet)
                _refused_without_writes(
                    self, fixture, result, before,
                    "refused: data_use: denied: "
                    "data_use: tool destination denied: codex",
                    exact=True,
                )

            for empty in (False, True):
                with self.subTest(coverage_empty=empty):
                    packet = copy.deepcopy(complete)
                    if empty:
                        packet["coverage"] = {}
                    else:
                        packet.pop("coverage")
                    before = _tree(fixture.reviews)
                    result = _open(fixture, packet)
                    _refused_without_writes(
                        self, fixture, result, before,
                        "refused: coverage: not attached", exact=True,
                    )

    def test_open_refuses_ledger_run_behind_head(self):
        """
        Scenario: Given a packet whose named ledger run is at a commit older than the head being sent, when open runs, then it refuses and names the ledger run and both commits
        """
        with tempfile.TemporaryDirectory(prefix="packet-stale-run-") as directory:
            fixture = _fixture(self, directory)
            run_id = _record_run(self, fixture)
            recorded_head = fixture.head
            (fixture.repo / "widget.py").write_text(
                HEAD_WIDGET + "\n# A later committed change.\n",
                encoding="utf-8",
            )
            fixture.head = _commit(self, fixture, "advance packet head")
            packet = _packet(fixture, run_id)
            expected = (
                f"refused: tests.ledger_runs: run {run_id} is at "
                f"{recorded_head}, head is {fixture.head}"
            )
            self.assertNotEqual(recorded_head, fixture.head)

            for position in ("packet-head", "run-head-branch", "detached"):
                with self.subTest(checkout=position):
                    if position == "run-head-branch":
                        _git(self, fixture, "checkout", "-q", "-b",
                             "inspection", recorded_head)
                    elif position == "detached":
                        _git(self, fixture, "checkout", "-q", "--detach",
                             recorded_head)
                    before = _tree(fixture.reviews)
                    result = _open(fixture, packet)
                    _refused_without_writes(
                        self, fixture, result, before, expected, exact=True
                    )

            with self.subTest(precedes_reviewer_session_and_old_checks=True):
                before = _tree(fixture.reviews)
                result = _open(
                    fixture, packet, "--max-rounds", "0",
                    extra_env={"GSTACK_PEER_REVIEW_SESSION": "1"},
                )
                _refused_without_writes(
                    self, fixture, result, before, expected, exact=True
                )

    def test_surface_shows_head_commit_bytes_from_other_branch(self):
        """
        Scenario: Given a checkout sitting on a different branch from the packet's head, when open builds the reviewer's surface, then every changed file shows the head commit's bytes
        """
        with tempfile.TemporaryDirectory(prefix="packet-surface-") as directory:
            fixture = _fixture(self, directory, unusual=True)
            run_id = _record_run(self, fixture)
            packet = _packet(fixture, run_id)

            # Record the ledger on build/packet first, then move away. The
            # current branch has neither the new files nor the head's caller.
            _git(self, fixture, "checkout", "-q", "-b",
                 "unrelated-branch", fixture.base)
            (fixture.repo / "widget.py").write_text(
                "def unrelated():\n    return -100\n", encoding="utf-8"
            )
            (fixture.repo / "caller.py").write_text(
                "UNRELATED = True\n", encoding="utf-8"
            )
            (fixture.repo / "settings.json").write_text(
                '{"expected": -100}\n', encoding="utf-8"
            )
            (fixture.repo / "evidence.txt").unlink()
            other_head = _commit(self, fixture, "unrelated branch")
            self.assertNotEqual(other_head, fixture.head)

            # Also distinguish committed bytes from uncommitted checkout bytes.
            (fixture.repo / "widget.py").write_text(
                "WORKTREE_ONLY = True\n", encoding="utf-8"
            )
            state = _opened(self, fixture, packet)
            self.assertFalse(fixture.calls.exists())

            # open checks fitness; round exposes the actual surface at the
            # external reviewer boundary. The observer deliberately exits 23.
            result = _peer(fixture, "round", state["review_id"])
            self.assertTrue(fixture.calls.is_file(), _diagnostic(result))
            calls = [
                json.loads(line)
                for line in fixture.calls.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(calls), 1, _diagnostic(result))
            files = {
                name: base64.b64decode(body)
                for name, body in calls[0]["files"].items()
            }
            expected = {
                "changed/0-repo/widget.py": HEAD_WIDGET.encode("utf-8"),
                "callers/0-repo/caller.py": HEAD_CALLER.encode("utf-8"),
                "dependencies/0-repo/settings.json":
                    HEAD_SETTINGS.encode("utf-8"),
                "dependencies/0-repo/evidence.txt":
                    HEAD_EVIDENCE.encode("utf-8"),
            }
            expected.update({
                "changed/0-repo/" + name: body
                for name, body in fixture.unusual.items()
            })
            for name, body in expected.items():
                with self.subTest(surface_file=name):
                    self.assertIn(name, files, _diagnostic(result))
                    self.assertEqual(files[name], body)
            self.assertEqual(
                {name for name in files if name.startswith("changed/")},
                {name for name in expected if name.startswith("changed/")},
            )

    def test_complete_packet_still_opens_and_refused_stays_refused(self):
        """
        Scenario: A complete packet at its head being refused, or a packet that is refused today being dispatched, must never happen
        """
        with tempfile.TemporaryDirectory(prefix="packet-invariant-") as directory:
            fixture = _fixture(self, directory)
            run_id = _record_run(self, fixture)
            complete = _packet(fixture, run_id)
            _opened(self, fixture, complete)

            # Run identity belongs to its recorded commit, not the checkout's
            # current HEAD. No ledger recording occurs while detached.
            _git(self, fixture, "checkout", "-q", "--detach", fixture.base)
            _opened(self, fixture, complete)
            _git(self, fixture, "checkout", "-q", "build/packet")

            # Existing explicit coverage overrides must continue to open.
            narrow = copy.deepcopy(complete)
            narrow["coverage"]["criteria"][0]["probability"] = 0.0
            narrow["exclusions"] = ["This fixture intentionally narrows coverage."]
            state = _opened(self, fixture, narrow, "--accept-narrow-packet")
            self.assertTrue(state["coverage_overridden"])

            unattached = copy.deepcopy(complete)
            unattached.pop("coverage")
            unattached["exclusions"] = [
                "This fixture scores no design items; coverage is intentionally absent."
            ]
            _opened(self, fixture, unattached, "--accept-narrow-packet")

            cases = []
            malformed = copy.deepcopy(complete)
            malformed.pop("release_owner")
            cases.append(("missing owner", malformed, (), {}, "malformed_packet"))

            unchanged = copy.deepcopy(complete)
            unchanged["repos"][0]["base"] = fixture.head
            cases.append(("no change", unchanged, (), {}, "missing_commits"))

            cases.append((
                "uncovered criterion", narrow, (), {}, "packet_narrower_than_item"
            ))
            cases.append((
                "round limit", complete, ("--max-rounds", "4"), {},
                "max_rounds",
            ))
            cases.append((
                "same reviewer family", complete, (),
                {"GSTACK_REVIEWER": "claude"}, "reviewer_not_independent",
            ))
            cases.append((
                "reviewer recursion", complete, (),
                {"GSTACK_PEER_REVIEW_SESSION": "1"}, "review",
            ))

            for label, packet, flags, extra_env, message in cases:
                with self.subTest(existing_refusal=label):
                    before = _tree(fixture.reviews)
                    result = _open(
                        fixture, packet, *flags, extra_env=extra_env
                    )
                    _refused_without_writes(
                        self, fixture, result, before, message
                    )

            # A real failing check remains a refusal even when the packet's
            # named passing evidence is at exactly the requested head.
            _record_run(self, fixture, exit_code=3)
            before = _tree(fixture.reviews)
            result = _open(fixture, complete)
            _refused_without_writes(
                self, fixture, result, before, "open_check_failure"
            )


if __name__ == "__main__":
    unittest.main()
