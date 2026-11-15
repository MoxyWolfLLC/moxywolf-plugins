import copy
import json
import os
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


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
Path(os.environ["HOLDOUT_CAPTURE"]).write_text(json.dumps(files))
with Path(os.environ["HOLDOUT_CALLS"]).open("a") as stream:
    stream.write("called\n")
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


def _success(result):
    if result.returncode != 0:
        raise AssertionError(
            f"Exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def _git(f, *args):
    return _success(_run(["git", *args], f.repo, f.env))


def _write_files(root, files):
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _commit(f, files, message):
    _write_files(f.repo, files)
    _git(f, "add", "-A")
    _git(f, "commit", "-qm", message)
    return _git(f, "rev-parse", "HEAD")


def _snapshot(root):
    entries = {}
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[name] = ("symlink", os.readlink(path))
        elif path.is_dir():
            entries[name] = ("directory",)
        else:
            entries[name] = ("file", path.read_bytes())
    return root.exists(), entries


@contextmanager
def _fixture():
    candidate = Path(os.environ["GOAL_CANDIDATE"]).absolute()
    with tempfile.TemporaryDirectory(prefix="packet-holdout-", dir="/tmp") as tmp:
        root = Path(tmp).resolve()
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GSTACK_", "GIT_"))
        }
        f = SimpleNamespace(
            candidate=candidate,
            root=root,
            repo=root / "repo",
            reviews=root / "reviews",
            packet_file=root / "packet.json",
            capture=root / "capture.json",
            calls=root / "calls.txt",
            env=env,
        )
        binary_dir = root / "bin"
        temporary_dir = root / "temporary"
        for directory in (f.repo, binary_dir, temporary_dir):
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
            "GSTACK_PEER_REVIEW_DIR": str(f.reviews),
            "GSTACK_REVIEWER": "codex",
            "GSTACK_CODEX_MODEL": "gpt-6-astra",
            "HOLDOUT_CAPTURE": str(f.capture),
            "HOLDOUT_CALLS": str(f.calls),
        })
        _git(f, "init", "-q", "-b", "packet")
        _git(f, "config", "user.email", "holdout@example.invalid")
        _git(f, "config", "user.name", "Holdout Fixture")
        _git(f, "config", "commit.gpgsign", "false")
        _git(f, "config", "core.hooksPath", str(root / "no-hooks"))
        f.base = _commit(f, BASE_FILES, "base")
        (f.repo / "src/removed.js").unlink()
        f.head = _commit(f, HEAD_FILES, "packet head")
        f.packet = {
            "outcome": "Increment the exported value.",
            "acceptance_criteria": [CRITERION],
            "repos": [{
                "path": str(f.repo),
                "base": f.base,
                "head": f.head,
            }],
            "changed_behavior": "The exported value adds one to delta.",
            "exclusions": [],
            "tests": {
                "commands": [],
                "results": "",
                "environment": "isolated offline fixture",
                "ledger_runs": [],
            },
            "release_owner": "holdout-owner",
            "data_use": {
                "owner": "holdout-owner",
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
        yield f


def _peer(f, *args, env=None):
    return _run(
        [sys.executable, SCRIPTS / "peer_review.py", *args],
        f.candidate,
        f.env if env is None else env,
    )


def _open(f, packet=None, flags=(), env=None, builder="claude"):
    f.packet_file.write_text(json.dumps(f.packet if packet is None else packet))
    return _peer(
        f,
        "open",
        "--builder", builder,
        "--packet", f.packet_file,
        "--timeout", "30",
        *flags,
        env=env,
    )


def _opened(test, f, **kwargs):
    result = _open(f, **kwargs)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    state = json.loads(result.stdout)
    test.assertEqual(state["outcome"], "opened", state)
    test.assertEqual(state["rounds_used"], 0)
    test.assertFalse(f.calls.exists(), "open dispatched a reviewer")
    return state


def _ledger_rows(f):
    return [
        json.loads(line)
        for path in f.reviews.rglob("*.jsonl")
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _ledger_run(f):
    before = {row["id"] for row in _ledger_rows(f)}
    _success(_run(
        [
            sys.executable,
            f.candidate / SCRIPTS / "check_ledger.py",
            "run", "--repo", f.repo, "--",
            sys.executable, "-c", "print('holdout check passed')",
        ],
        f.repo,
        f.env,
    ))
    added = [row for row in _ledger_rows(f) if row["id"] not in before]
    if len(added) != 1:
        raise AssertionError(f"Expected one new ledger run, got {added!r}")
    return added[0]


def _run_ref(f, row, basename=False):
    return {
        "repo": f.repo.name if basename else str(f.repo),
        "run_id": row["id"],
    }


def _refused(test, f, result, before, message):
    test.assertEqual(result.returncode, 2, result.stdout + result.stderr)
    test.assertEqual(result.stdout, "")
    test.assertEqual(result.stderr, message + "\n")
    test.assertEqual(_snapshot(f.reviews), before, "refusal changed review storage")
    test.assertFalse(f.calls.exists(), "refusal dispatched a reviewer")
    test.assertFalse(f.capture.exists(), "refusal exposed a surface")


def _stale_message(row, head):
    return (
        f"refused: tests.ledger_runs: run {row['id']} "
        f"is at {row['head']}, head is {head}"
    )


class Holdout(unittest.TestCase):
    def test_open_preflight_order_precedes_recursion_and_validation(self):
        with _fixture() as f:
            first = _ledger_run(f)
            second = _ledger_run(f)
            later = _commit(
                f, {"src/value.js": b"export const value = 9;\n"}, "later"
            )
            packet = copy.deepcopy(f.packet)
            packet["repos"][0]["head"] = later
            packet["tests"]["ledger_runs"] = [
                _run_ref(f, second, basename=True),
                _run_ref(f, first),
            ]
            packet.pop("outcome")
            packet.pop("coverage")
            packet.pop("data_use")
            env = dict(f.env, GSTACK_PEER_REVIEW_SESSION="1")
            flags = ("--max-rounds", "0")
            before = _snapshot(f.reviews)

            _refused(
                self, f, _open(f, packet, flags, env), before,
                "refused: data_use: missing",
            )
            packet["data_use"] = copy.deepcopy(f.packet["data_use"])
            packet["data_use"]["allow_history"] = False
            _refused(
                self, f, _open(f, packet, flags, env), before,
                "refused: data_use: denied: "
                "data_use: repository/history permission and accountable owner required",
            )
            packet["data_use"] = copy.deepcopy(f.packet["data_use"])
            _refused(
                self, f, _open(f, packet, flags, env), before,
                "refused: coverage: not attached",
            )
            packet["coverage"] = {"status": "unavailable", "why": "fixture"}
            _refused(
                self, f, _open(f, packet, flags, env), before,
                _stale_message(second, later),
            )
            packet["tests"]["ledger_runs"].reverse()
            _refused(
                self, f, _open(f, packet, flags, env), before,
                _stale_message(first, later),
            )

    def test_permissions_use_selected_reviewer_and_remain_enforced_at_round(self):
        selections = (
            ("claude", "gemini", "gemini"),
            ("codex", None, "claude"),
            ("claude", None, "codex"),
        )
        for builder, forced, selected in selections:
            with self.subTest(builder=builder, forced=forced), _fixture() as f:
                env = dict(f.env)
                env.pop("GSTACK_REVIEWER")
                if forced is not None:
                    env["GSTACK_REVIEWER"] = forced
                packet = copy.deepcopy(f.packet)
                packet["data_use"]["allowed_tools"] = [builder]
                before = _snapshot(f.reviews)
                _refused(
                    self, f,
                    _open(f, packet, env=env, builder=builder),
                    before,
                    "refused: data_use: denied: "
                    f"data_use: tool destination denied: {selected}",
                )
                packet["data_use"]["allowed_tools"] = [selected]
                state = _opened(
                    self, f, packet=packet, env=env, builder=builder
                )
                self.assertEqual(state["reviewer"], selected)

        for key, value in (
            ("owner", "someone-else"),
            ("classification", ""),
            ("allow_repository", False),
            ("allow_history", False),
        ):
            with self.subTest(permission=key), _fixture() as f:
                packet = copy.deepcopy(f.packet)
                packet["data_use"][key] = value
                before = _snapshot(f.reviews)
                _refused(
                    self, f, _open(f, packet), before,
                    "refused: data_use: denied: "
                    "data_use: repository/history permission and accountable owner required",
                )

        with _fixture() as f:
            state = _opened(self, f)
            retained = f.reviews / state["review_id"] / "packet.json"
            packet = json.loads(retained.read_text())
            packet["data_use"]["allowed_tools"] = ["claude"]
            retained.write_text(json.dumps(packet))
            result = _peer(f, "round", state["review_id"])
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["outcome"], "data_use_denied")
            self.assertEqual(
                record["error"], "data_use: tool destination denied: codex"
            )
            self.assertFalse(f.calls.exists())

    def test_coverage_attachment_override_and_foreign_repository_validation(self):
        cases = (
            "missing",
            "empty",
            "unavailable",
            "unlabelled",
            "unchecked",
            "scored-narrow",
        )
        for case in cases:
            with self.subTest(coverage=case), _fixture() as f:
                packet = copy.deepcopy(f.packet)
                flags = ()
                if case == "missing":
                    packet.pop("coverage")
                elif case == "empty":
                    packet["coverage"] = {}
                elif case == "unavailable":
                    packet["coverage"] = {
                        "status": "unavailable",
                        "why": "The scorer was unavailable.",
                    }
                elif case == "unlabelled":
                    packet["coverage"] = {"why": "An attached unlabelled report."}
                elif case == "unchecked":
                    packet["coverage"] = {
                        "status": "not_run",
                        "criteria": [{
                            "item": "fixture",
                            "criterion_no": 1,
                            "declared": CRITERION,
                            "probability": 1.0,
                        }],
                    }
                else:
                    packet["coverage"]["criteria"][0]["probability"] = 0.0

                if case in ("missing", "empty", "scored-narrow"):
                    packet["exclusions"] = [
                        "This fixture intentionally accepts a narrow packet."
                    ]
                    flags = ("--accept-narrow-packet",)

                state = _opened(self, f, packet=packet, flags=flags)
                self.assertEqual(
                    state["coverage_checked"], case == "scored-narrow"
                )
                if case == "scored-narrow":
                    self.assertTrue(state["coverage_overridden"])
                retained = json.loads(
                    (f.reviews / state["review_id"] / "packet.json").read_text()
                )
                self.assertEqual(retained.get("coverage"), packet.get("coverage"))
                self.assertEqual(retained["exclusions"], packet["exclusions"])

        with _fixture() as f:
            packet = copy.deepcopy(f.packet)
            packet["tests"]["ledger_runs"] = [{
                "repo": str(f.root / "not-in-the-packet"),
                "run_id": "0123456789ab",
            }]
            before = _snapshot(f.reviews)
            result = _open(f, packet)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertTrue(
                result.stderr.startswith("malformed_packet:"),
                result.stderr,
            )
            self.assertIn("tests.ledger_runs", result.stderr)
            self.assertEqual(_snapshot(f.reviews), before)
            self.assertFalse(f.calls.exists())

    def test_named_round_runs_precede_every_existing_round_guard(self):
        for barrier in ("first-round", "recursion", "closed", "exhausted", "disposition"):
            with self.subTest(barrier=barrier), _fixture() as f:
                first = _ledger_run(f)
                second = _ledger_run(f)
                state = _opened(self, f)
                later = _commit(
                    f, {"src/value.js": b"export const value = 11;\n"}, "later"
                )
                directory = f.reviews / state["review_id"]
                env = dict(f.env)
                if barrier == "recursion":
                    env["GSTACK_PEER_REVIEW_SESSION"] = "1"
                elif barrier == "closed":
                    state["outcome"] = "no_blocking_findings"
                elif barrier == "exhausted":
                    state["rounds_used"] = state["max_rounds"]
                elif barrier == "disposition":
                    state.update(
                        outcome="blocking_findings",
                        rounds_used=1,
                        adjudicated_round=1,
                        heads=[[f.head], [f.head]],
                    )
                    (directory / "round-1.json").write_text(json.dumps({
                        "round": 1,
                        "outcome": "blocking_findings",
                        "findings": [{
                            "id": "F1",
                            "severity": "blocking",
                            "file": "src/value.js",
                            "line": 1,
                            "what": "A disposition is required.",
                        }],
                    }))
                (directory / "state.json").write_text(json.dumps(state))
                before = _snapshot(f.reviews)
                result = _peer(
                    f, "round", state["review_id"],
                    "--head", f"{f.repo}={later}",
                    "--ledger-run", f"{f.repo.name}={second['id']}",
                    "--ledger-run", f"{f.repo}={first['id']}",
                    env=env,
                )
                _refused(
                    self, f, result, before, _stale_message(second, later)
                )

    def test_first_round_head_controls_all_surface_bytes_and_symlink_checks(self):
        for explicit_run in (False, True):
            with self.subTest(explicit_run=explicit_run), _fixture() as f:
                old_run = _ledger_run(f)
                f.packet["tests"]["ledger_runs"] = [_run_ref(f, old_run)]
                state = _opened(self, f)
                later_value = (
                    b"import { delta } from './dep.js';\n"
                    b"export const value = delta + 7;\n"
                )
                later = _commit(
                    f, {"src/value.js": later_value}, "first-round override"
                )
                fresh_run = _ledger_run(f) if explicit_run else None
                _git(f, "checkout", "-qb", "other", f.base)
                poison = b"HOLDOUT_CHECKOUT_BYTES_MUST_NOT_BE_SURFACED"
                _write_files(f.repo, {
                    "src/value.js": poison,
                    "src/added.js": poison,
                    "src/removed.js": poison,
                    "docs/evidence.md": poison,
                })
                (f.repo / "src/dep.js").unlink()
                (f.repo / "src/caller.js").unlink()
                repo_ref = str(f.repo) if explicit_run else f.repo.name
                args = [
                    "round", state["review_id"],
                    "--head", f"{repo_ref}={later}",
                ]
                if fresh_run is not None:
                    args += [
                        "--ledger-run", f"{f.repo.name}={fresh_run['id']}"
                    ]
                result = _peer(f, *args)
                self.assertTrue(
                    f.capture.is_file(),
                    "The first-round override did not reach the reviewer:\n"
                    + result.stdout + result.stderr,
                )
                self.assertEqual(f.calls.read_text().splitlines(), ["called"])
                captured = {
                    name: bytes.fromhex(content)
                    for name, content in json.loads(f.capture.read_text()).items()
                }
                expected = {
                    "changed/0-repo/src/value.js": later_value,
                    "changed/0-repo/src/added.js": HEAD_FILES["src/added.js"],
                    "callers/0-repo/src/caller.js": BASE_FILES["src/caller.js"],
                    "dependencies/0-repo/src/dep.js": BASE_FILES["src/dep.js"],
                    "dependencies/0-repo/docs/evidence.md": BASE_FILES["docs/evidence.md"],
                }
                for name, content in expected.items():
                    self.assertIn(name, captured)
                    self.assertEqual(captured[name], content, name)
                for name, content in captured.items():
                    self.assertNotIn(poison, content, name)
                diff = captured["CHANGE.diff"].decode()
                self.assertIn("src/removed.js", diff)
                self.assertIn("-export const obsolete = true;", diff)
                record = json.loads(result.stdout)
                self.assertEqual(record["repos"][0]["head"], later)

        with self.subTest(case="committed-escaping-symlink"), _fixture() as f:
            (f.root / "secret.txt").write_text("outside-repository-secret")
            os.symlink("../../secret.txt", f.repo / "src/leak.js")
            link_head = _commit(f, {}, "escaping symlink")
            f.packet["repos"][0]["head"] = link_head
            _git(f, "checkout", "-qb", "without-link", f.head)
            (f.repo / "src/leak.js").write_text("ordinary checkout file")
            state = _opened(self, f)
            result = _peer(f, "round", state["review_id"])
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["outcome"], "data_use_denied")
            self.assertFalse(f.calls.exists())
            self.assertFalse(f.capture.exists())


if __name__ == "__main__":
    unittest.main()
