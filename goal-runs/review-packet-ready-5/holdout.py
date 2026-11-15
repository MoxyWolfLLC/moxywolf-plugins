"""Black-box holdouts for review-packet-ready-5."""

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
    "module.py": b"# dependency.txt\ndef increment(value):\n    return value\n",
    "caller.py": b"import module\nresult = module.increment(1)\n",
    "dependency.txt": b"Dependency bytes from the packet head.\n\n",
    "evidence.md": b"Criterion evidence from the packet head.\n\n",
}
HEAD_MODULE = b"# dependency.txt\ndef increment(value):\n    return value + 1\n\n"

REVIEWER_SOURCE = r'''
import base64
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
root = Path(args[args.index("-C") + 1])
with Path(os.environ["HOLDOUT_CALLS"]).open("a", encoding="utf-8") as log:
    log.write("called\n")
files = {}
for path in sorted(root.rglob("*")):
    if path.is_file():
        files[path.relative_to(root).as_posix()] = base64.b64encode(
            path.read_bytes()
        ).decode("ascii")
Path(os.environ["HOLDOUT_CAPTURE"]).write_text(
    json.dumps(files), encoding="utf-8"
)
prompt = args[-1]
packet = json.loads(
    prompt.split("=== PACKET ===\n\n", 1)[1].split("\n\n=== CONTRACT", 1)[0]
)
blocking = os.environ.get("HOLDOUT_BLOCK") == "1"
result = {
    "verdict": "blocking_findings" if blocking else "no_blocking_findings",
    "acceptance": [
        {"criterion": criterion, "met": True, "evidence": "module.py:3"}
        for criterion in packet["acceptance_criteria"]
    ],
    "findings": [],
    "blocker_resolutions": [],
    "regressions_from_fixes": [],
    "notes": "",
}
if blocking:
    result["findings"] = [{
        "id": "F1",
        "severity": "blocking",
        "file": "module.py",
        "line": 3,
        "what": "The increment requires a correction.",
        "evidence": "module.py:3",
        "criterion": packet["acceptance_criteria"][0],
        "fix": "Correct the increment.",
        "category": "general",
    }]
Path(args[args.index("--output-last-message") + 1]).write_text(
    json.dumps(result), encoding="utf-8"
)
print("model: gpt-6-astra", file=sys.stderr)
'''


def _diagnostic(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _tree(root):
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix():
            None if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


def _calls(case):
    return case.calls.read_bytes() if case.calls.exists() else b""


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


def _program(case, script, *args, extra_env=None, cwd=None):
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


def _open_args(case, packet=None, flags=()):
    _write_json(case.packet_file, case.packet if packet is None else packet)
    return (
        "open", "--builder", "claude",
        "--packet", str(case.packet_file), "--timeout", "30", *flags,
    )


def _opened(test, case, packet=None, flags=()):
    before_calls = _calls(case)
    result = _program(
        case, "peer_review.py", *_open_args(case, packet, flags)
    )
    test.assertEqual(result.returncode, 0, _diagnostic(result))
    state = json.loads(result.stdout)
    test.assertEqual(state["outcome"], "opened", state)
    test.assertEqual(state["rounds_used"], 0, state)
    test.assertTrue(
        (case.reviews / state["review_id"] / "state.json").is_file()
    )
    test.assertEqual(_calls(case), before_calls, "open called a reviewer")
    return state


def _refused(test, case, args, message, extra_env=None):
    before = _tree(case.reviews)
    before_calls = _calls(case)
    result = _program(
        case, "peer_review.py", *args, extra_env=extra_env
    )
    test.assertEqual(result.returncode, 2, _diagnostic(result))
    test.assertEqual(result.stdout, "", _diagnostic(result))
    test.assertEqual(result.stderr.splitlines(), [message], _diagnostic(result))
    test.assertEqual(_tree(case.reviews), before, "refusal wrote review state")
    test.assertEqual(_calls(case), before_calls, "refusal dispatched a reviewer")


def _record_run(case):
    before = set()
    for path in case.reviews.glob("ledger/**/*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                before.add(json.loads(line)["id"])
    result = _program(
        case, "check_ledger.py",
        "run", "--repo", str(case.repo), "--",
        sys.executable, "-c", "print('holdout check')",
        cwd=case.repo,
    )
    if result.returncode != 0:
        raise AssertionError(_diagnostic(result))
    added = []
    for path in case.reviews.glob("ledger/**/*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["id"] not in before:
                    added.append((path, row))
    if len(added) != 1:
        raise AssertionError(f"Expected one new ledger run, found {added!r}")
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


def _ledger_message(run_id, run_head, packet_head):
    return (
        f"refused: tests.ledger_runs: run {run_id} "
        f"is at {run_head if run_head is not None else 'none'}, "
        f"head is {packet_head}"
    )


@contextmanager
def _case():
    with tempfile.TemporaryDirectory(prefix="packet-holdout-") as directory:
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
        binary = root / "bin"
        binary.mkdir()
        temporary = root / "tmp"
        temporary.mkdir()
        reviewer = binary / "codex"
        reviewer.write_text(
            "#!" + sys.executable + "\n" + REVIEWER_SOURCE, encoding="utf-8"
        )
        reviewer.chmod(0o755)
        case.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GSTACK_", "GIT_", "HOLDOUT_"))
            and key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        case.env.update({
            "PATH": str(binary) + os.pathsep + os.environ.get("PATH", os.defpath),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GSTACK_PEER_REVIEW_DIR": str(case.reviews),
            "GSTACK_REVIEWER": "codex",
            "GSTACK_CODEX_MODEL": "gpt-6-astra",
            "HOLDOUT_CALLS": str(case.calls),
            "HOLDOUT_CAPTURE": str(case.capture),
            "TMPDIR": str(temporary),
            "TMP": str(temporary),
            "TEMP": str(temporary),
        })
        _git(case, "init", "-q")
        _git(case, "checkout", "-qb", "packet-head")
        for key, value in (
            ("user.name", "Holdout Fixture"),
            ("user.email", "holdout@example.invalid"),
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
                "results": "Deterministic holdout fixture.",
                "environment": "isolated temporary repository",
            },
            "release_owner": "Fixture Human",
            "data_use": {
                "owner": "Fixture Human",
                "classification": "test",
                "allow_repository": True,
                "allow_history": True,
                "allowed_tools": ["codex"],
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


class Holdout(unittest.TestCase):
    def test_open_preserves_permission_reasons_and_first_stale_run_order(self):
        with _case() as case:
            _git(case, "checkout", "-q", "--detach", case.base)
            _, first = _record_run(case)
            _, second = _record_run(case)
            self.assertNotEqual(first["id"], second["id"])
            self.assertEqual(first["head"], case.base)
            self.assertEqual(second["head"], case.base)

            packet = copy.deepcopy(case.packet)
            packet["acceptance_criteria"] = []
            packet["tests"]["ledger_runs"] = [
                {"repo": str(case.repo), "run_id": second["id"]},
                {"repo": str(case.repo), "run_id": first["id"]},
            ]
            session = {"GSTACK_PEER_REVIEW_SESSION": "1"}
            for field, value in (
                ("owner", "Another Owner"),
                ("classification", ""),
                ("allow_repository", False),
                ("allow_history", False),
                ("allow_repository", "true"),
            ):
                with self.subTest(permission=field, value=value):
                    denied = copy.deepcopy(packet)
                    denied["data_use"][field] = value
                    denied.pop("coverage")
                    _refused(
                        self, case,
                        _open_args(case, denied, ("--max-rounds", "0")),
                        "refused: data_use: denied: data_use: "
                        "repository/history permission and accountable owner required",
                        session,
                    )

            for order in (
                (second, first),
                (first, second),
            ):
                packet["tests"]["ledger_runs"] = [
                    {"repo": str(case.repo), "run_id": run["id"]}
                    for run in order
                ]
                for env in ({}, session):
                    with self.subTest(first_run=order[0]["id"], session=bool(env)):
                        _refused(
                            self, case,
                            _open_args(case, packet, ("--max-rounds", "0")),
                            _ledger_message(order[0]["id"], case.base, case.head),
                            env,
                        )

            foreign = copy.deepcopy(case.packet)
            foreign["tests"]["ledger_runs"] = [{
                "repo": str(case.root / "unlisted-repository"),
                "run_id": first["id"],
            }]
            before = _tree(case.reviews)
            result = _program(
                case, "peer_review.py", *_open_args(case, foreign)
            )
            self.assertNotEqual(result.returncode, 0, _diagnostic(result))
            self.assertIn("malformed_packet", result.stderr, _diagnostic(result))
            self.assertNotIn("refused: tests.ledger_runs:", result.stderr)
            self.assertEqual(_tree(case.reviews), before)
            self.assertEqual(_calls(case), b"")

            state = _opened(self, case)
            retained = case.reviews / state["review_id"] / "packet.json"
            edited = _read_json(retained)
            edited["data_use"]["allowed_tools"] = []
            _write_json(retained, edited)
            result = _program(
                case, "peer_review.py", "round", state["review_id"]
            )
            self.assertEqual(result.returncode, 1, _diagnostic(result))
            record = json.loads(result.stdout)
            self.assertEqual(record["outcome"], "data_use_denied", record)
            self.assertIn("tool destination denied: codex", record["error"])
            self.assertEqual(_calls(case), b"")

    def test_round_ledger_refusal_precedes_all_existing_round_guards(self):
        for condition in ("opened", "closed", "exhausted", "undisposed"):
            with self.subTest(condition=condition), _case() as case:
                _git(case, "checkout", "-q", "--detach", case.base)
                ledger_path, stale = _record_run(case)
                _git(case, "checkout", "-q", "packet-head")
                flags = ("--max-rounds", "1") if condition == "exhausted" else ()
                state = _opened(self, case, flags=flags)
                review_id = state["review_id"]

                if condition != "opened":
                    blocking = condition in {"exhausted", "undisposed"}
                    result = _program(
                        case, "peer_review.py", "round", review_id,
                        extra_env={"HOLDOUT_BLOCK": "1" if blocking else "0"},
                    )
                    self.assertEqual(
                        result.returncode, 1 if blocking else 0,
                        _diagnostic(result),
                    )
                    expected = {
                        "closed": "no_blocking_findings",
                        "exhausted": "rounds_exhausted",
                        "undisposed": "blocking_findings",
                    }[condition]
                    self.assertEqual(json.loads(result.stdout)["outcome"], expected)
                    self.assertEqual(_calls(case), b"called\n")

                heads = (
                    (case.base, case.head[:12], None)
                    if condition == "opened" else (case.base,)
                )
                for recorded_head in heads:
                    _set_run_head(ledger_path, stale["id"], recorded_head)
                    for session in (False, True):
                        with self.subTest(
                            recorded_head=recorded_head, session=session
                        ):
                            _refused(
                                self, case,
                                (
                                    "round", review_id,
                                    "--ledger-run", f"{case.repo}={stale['id']}",
                                ),
                                _ledger_message(
                                    stale["id"], recorded_head, case.head
                                ),
                                {"GSTACK_PEER_REVIEW_SESSION": "1"}
                                if session else {},
                            )

    def test_first_round_head_override_changes_surface_and_checks_only_named_runs(self):
        with _case() as case:
            _, old_run = _record_run(case)
            case.packet["tests"]["ledger_runs"] = [{
                "repo": str(case.repo), "run_id": old_run["id"],
            }]
            case.packet["acceptance_criteria"].append(
                "evidence.md supplies the criterion evidence."
            )
            changed = {
                "module.py": (
                    b"# dependency.txt\n"
                    b"def increment(value):\n    return 1 + value\n\n"
                ),
                "round space.txt": b"Head override: space.\n\n",
                "round\ttab.txt": b"Head override: tab.\n\n",
                "round\nnewline.txt": b"Head override: newline.\n\n",
            }
            for name, data in changed.items():
                (case.repo / name).write_bytes(data)
            new_head = _commit(case, "first round override")
            _, new_run = _record_run(case)
            self.assertEqual(new_run["head"], new_head)

            _git(case, "checkout", "-q", "--detach", case.base)
            secret = case.root / "outside.txt"
            secret.write_bytes(b"Do not read checkout symlink bytes.\n")
            (case.repo / "module.py").unlink()
            (case.repo / "module.py").symlink_to(secret)
            (case.repo / "caller.py").write_bytes(b"Wrong checkout caller.\n")
            (case.repo / "dependency.txt").write_bytes(b"Wrong dependency.\n")
            (case.repo / "evidence.md").unlink()

            for explicit_run in (False, True):
                with self.subTest(explicit_run=explicit_run):
                    state = _opened(self, case)
                    args = [
                        "round", state["review_id"],
                        "--head", f"{case.repo}={new_head}",
                    ]
                    if explicit_run:
                        args.extend((
                            "--ledger-run", f"{case.repo}={new_run['id']}"
                        ))
                    before_calls = _calls(case)
                    result = _program(case, "peer_review.py", *args)
                    self.assertEqual(result.returncode, 0, _diagnostic(result))
                    record = json.loads(result.stdout)
                    self.assertEqual(record["outcome"], "no_blocking_findings")
                    self.assertEqual(record["repos"][0]["head"], new_head)
                    self.assertEqual(_calls(case), before_calls + b"called\n")
                    captured = {
                        name: base64.b64decode(data)
                        for name, data in _read_json(case.capture).items()
                    }
                    for name, expected in changed.items():
                        self.assertEqual(
                            captured.get("changed/0-repo/" + name), expected, name
                        )
                    for prefix, name in (
                        ("callers", "caller.py"),
                        ("dependencies", "dependency.txt"),
                        ("dependencies", "evidence.md"),
                    ):
                        self.assertEqual(
                            captured.get(f"{prefix}/0-repo/{name}"),
                            BASE_FILES[name], name,
                        )
                    self.assertNotIn(secret.read_bytes(), captured.values())
                    saved = _read_json(
                        case.reviews / state["review_id"] / "state.json"
                    )
                    self.assertEqual(saved["heads"][-1], [new_head])

    def test_escaping_symlinks_are_judged_at_the_head_with_whole_names(self):
        for name in ("escape space.txt", "escape\ttab.txt", "escape\nline.txt"):
            with self.subTest(name=name), _case() as case:
                secret = case.root / "private.txt"
                secret.write_bytes(b"Private bytes outside the repository.\n")
                (case.repo / name).symlink_to("../private.txt")
                dangerous_head = _commit(case, "escaping symlink at packet head")
                case.packet["repos"][0]["head"] = dangerous_head

                _git(case, "checkout", "-q", "--detach", case.base)
                (case.repo / name).write_bytes(b"Harmless checkout replacement.\n")
                result = _program(
                    case, "peer_review.py", *_open_args(case)
                )
                if result.returncode == 0:
                    state = json.loads(result.stdout)
                    self.assertEqual(state["outcome"], "opened", state)
                    result = _program(
                        case, "peer_review.py", "round", state["review_id"]
                    )
                    self.assertNotEqual(result.returncode, 0, _diagnostic(result))
                    if result.stdout.strip():
                        record = json.loads(result.stdout)
                        self.assertEqual(
                            record["outcome"], "data_use_denied",
                            _diagnostic(result),
                        )
                    else:
                        self.assertIn(
                            "data_use_denied", result.stderr, _diagnostic(result)
                        )
                else:
                    self.assertIn(
                        "data_use_denied", result.stderr, _diagnostic(result)
                    )
                self.assertEqual(_calls(case), b"", "escaping symlink dispatched")
                self.assertFalse(case.capture.exists())

    def test_graph_peer_uses_narrow_override_and_keeps_graph_governance(self):
        with _case() as case:
            workflow = {
                "name": "holdout-peer",
                "nodes": [
                    {
                        "id": "peer",
                        "kind": "peer",
                        "depends_on": [],
                        "inputs": ["packet"],
                        "outputs": ["peer.json"],
                        "effects": ["external_review"],
                        "on_failure": "block",
                        "checks": [CRITERION],
                    },
                    {
                        "id": "report",
                        "kind": "report",
                        "depends_on": ["peer"],
                        "inputs": ["packet", "peer"],
                        "outputs": ["report.json"],
                        "effects": ["local_report"],
                        "on_failure": "block",
                        "checks": ["Report preserves the peer review."],
                        "findings_from": ["peer"],
                    },
                ],
            }
            workflow_file = case.root / "workflow.json"
            graph_packet_file = case.root / "graph-packet.json"
            _write_json(workflow_file, workflow)
            policy = copy.deepcopy(case.packet["data_use"])
            policy["allowed_commands"] = []
            policy["output_roots"] = [str(case.root)]
            packet = {
                "owner": "Fixture Human",
                "builder": "claude",
                "repos": copy.deepcopy(case.packet["repos"]),
                "scope": "Review the increment.",
                "spec": CRITERION,
                "acceptance_criteria": [CRITERION],
                "changed_behavior": "The increment adds one.",
                "timeout": 30,
                "data_use": policy,
                "tests": {
                    "commands": [],
                    "results": "Graph evidence is not peer ledger evidence.",
                    "ledger_runs": [{
                        "repo": str(case.repo),
                        "run_id": "graph-only-not-a-peer-run",
                    }],
                },
            }
            for mode in ("missing", "empty", "denied", "allowed"):
                with self.subTest(policy=mode):
                    current = copy.deepcopy(packet)
                    if mode == "missing":
                        current.pop("data_use")
                    elif mode == "empty":
                        current["data_use"] = {}
                    elif mode == "denied":
                        current["data_use"]["allowed_tools"] = ["claude"]
                    run = case.root / ("graph-" + mode)
                    _write_json(graph_packet_file, current)
                    before_calls = _calls(case)
                    before_reviews = _tree(case.reviews)
                    result = _program(
                        case, "task_graph.py", "run",
                        "--workflow", str(workflow_file),
                        "--packet", str(graph_packet_file),
                        "--run-dir", str(run),
                        "--jobs", "1",
                    )
                    if mode != "allowed":
                        self.assertNotEqual(
                            result.returncode, 0, _diagnostic(result)
                        )
                        message = (
                            "data_use: tool destination denied: codex"
                            if mode == "denied" else
                            "data_use: repository/history permission "
                            "and accountable owner required"
                        )
                        self.assertIn(message, result.stderr, _diagnostic(result))
                        self.assertFalse((run / "state.json").exists())
                        self.assertFalse((run / "peer-review.json").exists())
                        self.assertEqual(_tree(run / "peer-reviews"), {})
                        self.assertEqual(_tree(case.reviews), before_reviews)
                        self.assertEqual(_calls(case), before_calls)
                        continue

                    self.assertEqual(result.returncode, 0, _diagnostic(result))
                    self.assertEqual(_calls(case), before_calls + b"called\n")
                    self.assertEqual(
                        _read_json(run / "state.json")["outcome"], "complete"
                    )
                    peer_packet = _read_json(run / "peer-packet.json")
                    self.assertEqual(peer_packet["data_use"], policy)
                    self.assertFalse(
                        (peer_packet.get("tests") or {}).get("ledger_runs"),
                        "graph peer packet inherited graph ledger runs",
                    )
                    self.assertFalse(
                        peer_packet.get("coverage"),
                        "graph adapter fabricated a coverage report",
                    )
                    exclusions = peer_packet.get("exclusions", [])
                    if isinstance(exclusions, str):
                        exclusions = [exclusions]
                    self.assertTrue(
                        any(
                            "graph" in line.lower()
                            and "no" in line.lower()
                            and "design" in line.lower()
                            for line in exclusions
                        ),
                        f"Missing graph design-scoring exclusion: {exclusions!r}",
                    )
                    marker = _read_json(run / "peer-review.json")
                    state = _read_json(
                        run / "peer-reviews" / marker["review_id"] / "state.json"
                    )
                    self.assertFalse(state["coverage_checked"])
                    self.assertEqual(state["outcome"], "no_blocking_findings")


if __name__ == "__main__":
    unittest.main()
