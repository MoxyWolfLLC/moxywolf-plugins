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
CRITERION = "`widget.py` returns the expected value; `evidence.txt` explains it."
WIDGET = "# Dependency: settings.json\n\ndef make():\n    return 2\n"
CALLER = "import widget\nassert widget.make() == 2\n"
SETTINGS = '{"expected": 2}\n'
EVIDENCE = "The expected result is 2.\n"

OBSERVER = r"""
import base64
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
surface = Path(args[args.index("-C") + 1])
files = {
    path.relative_to(surface).as_posix():
        base64.b64encode(path.read_bytes()).decode("ascii")
    for path in surface.rglob("*")
    if path.is_file()
}
with open(os.environ["HOLDOUT_CALLS"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps({"files": files}) + "\n")
print("holdout observer finished", file=sys.stderr)
sys.exit(23)
"""


def run(argv, cwd, env):
    return subprocess.run(
        [str(arg) for arg in argv],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def diagnostic(result):
    return (
        f"exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def git(case, fixture, *args):
    result = run(
        ["git", "-C", fixture.repo, *args], fixture.root, fixture.env
    )
    case.assertEqual(result.returncode, 0, diagnostic(result))
    return result.stdout.strip()


def commit(case, fixture, message):
    git(case, fixture, "add", "-A")
    git(case, fixture, "commit", "-qm", message)
    sha = git(case, fixture, "rev-parse", "HEAD")
    case.assertRegex(sha, r"^[0-9a-f]{40}$")
    return sha


def fixture(case, directory):
    root = Path(directory)
    candidate = Path(os.path.abspath(os.environ["GOAL_CANDIDATE"]))
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GSTACK_", "GOAL_", "GIT_"))
        and key not in {"PYTHONPATH", "PYTHONHOME"}
    }
    binaries = root / "bin"
    scratch = root / "scratch"
    binaries.mkdir()
    scratch.mkdir()
    observer = binaries / "codex"
    observer.write_text("#!" + sys.executable + "\n" + OBSERVER, encoding="utf-8")
    observer.chmod(0o755)

    f = SimpleNamespace(
        root=root,
        candidate=candidate,
        repo=root / "repo",
        reviews=root / "reviews",
        calls=root / "calls.jsonl",
        env=env,
    )
    env.update({
        "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
        "GSTACK_PEER_REVIEW_DIR": str(f.reviews),
        "GSTACK_REVIEWER": "codex",
        "GSTACK_CODEX_MODEL": "gpt-6-astra",
        "HOLDOUT_CALLS": str(f.calls),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "TMPDIR": str(scratch),
    })
    f.repo.mkdir()
    git(case, f, "init", "-q", "-b", "build/holdout")
    for key, value in (
        ("user.name", "Holdout"),
        ("user.email", "holdout@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", str(root / "no-hooks")),
        ("maintenance.auto", "false"),
        ("gc.auto", "0"),
    ):
        git(case, f, "config", key, value)

    for name, body in {
        "widget.py": WIDGET.replace("return 2", "return 1"),
        "caller.py": CALLER,
        "settings.json": SETTINGS,
        "evidence.txt": EVIDENCE,
        "obsolete.txt": "OLD DELETED FILE CONTENT\n",
    }.items():
        (f.repo / name).write_text(body, encoding="utf-8")
    f.base = commit(case, f, "base")
    (f.repo / "widget.py").write_text(WIDGET, encoding="utf-8")
    f.head = commit(case, f, "packet head")
    return f


def record_run(case, f):
    # Ledger recording always happens on a named branch.
    branch = git(case, f, "symbolic-ref", "--short", "HEAD")
    case.assertTrue(branch)
    result = run(
        [
            sys.executable,
            f.candidate / SCRIPTS / "check_ledger.py",
            "run", "--repo", f.repo, "--",
            sys.executable, "-c", "print('holdout check passed')",
        ],
        f.repo,
        f.env,
    )
    case.assertEqual(result.returncode, 0, diagnostic(result))
    ledger = f.reviews / "ledger" / "repo" / (branch + ".jsonl")
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    case.assertEqual(row["head"], git(case, f, "rev-parse", "HEAD"))
    case.assertEqual(row["exit_code"], 0)
    return row["id"], ledger


def packet(f, run_id):
    return {
        "outcome": "The widget returns the expected value.",
        "acceptance_criteria": [CRITERION],
        "repos": [{
            "path": str(f.repo),
            "base": f.base,
            "head": f.head,
        }],
        "changed_behavior": "The widget now returns 2.",
        "exclusions": [],
        "tests": {
            "commands": ["holdout check"],
            "results": "The recorded check passed.",
            "environment": "Disposable offline repository.",
            "ledger_runs": [{"repo": str(f.repo), "run_id": run_id}],
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
                "item": "holdout-fixture",
                "criterion_no": 1,
                "declared": CRITERION,
                "probability": 1.0,
            }],
        },
    }


def peer(f, *args, extra_env=None):
    env = dict(f.env)
    env.update(extra_env or {})
    return run(
        [sys.executable, f.candidate / SCRIPTS / "peer_review.py", *args],
        f.candidate,
        env,
    )


def open_packet(f, value, *flags, extra_env=None):
    source = f.root / "packet.json"
    source.write_text(json.dumps(value), encoding="utf-8")
    return peer(
        f, "open", "--builder", "claude",
        "--packet", source, "--timeout", "20", *flags,
        extra_env=extra_env,
    )


def opened(case, f, value, *flags):
    result = open_packet(f, value, *flags)
    case.assertEqual(result.returncode, 0, diagnostic(result))
    state = json.loads(result.stdout)
    case.assertEqual(state["outcome"], "opened", diagnostic(result))
    case.assertEqual(state["rounds_used"], 0)
    case.assertEqual(state["heads"], [[value["repos"][0]["head"]]])
    return state


def tree(root):
    if not root.exists():
        return None
    return {
        path.relative_to(root).as_posix():
            None if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


def call_bytes(f):
    return f.calls.read_bytes() if f.calls.exists() else None


def refusal(case, f, result, before, calls_before, message):
    case.assertEqual(result.returncode, 2, diagnostic(result))
    case.assertEqual(result.stdout, "", diagnostic(result))
    case.assertEqual(result.stderr.splitlines(), [message], diagnostic(result))
    case.assertEqual(tree(f.reviews), before, "Refusal changed review storage.")
    case.assertEqual(call_bytes(f), calls_before, "Refusal dispatched a reviewer.")


def stale_message(run_id, recorded, head):
    return (
        f"refused: tests.ledger_runs: run {run_id} is at "
        f"{recorded}, head is {head}"
    )


class Holdout(unittest.TestCase):
    def test_open_preflight_order_and_exact_streams_survive_old_guards(self):
        with tempfile.TemporaryDirectory(prefix="holdout-order-") as directory:
            f = fixture(self, directory)
            old_run, _ = record_run(self, f)
            old_head = f.head
            (f.repo / "widget.py").write_text(WIDGET + "# later\n", encoding="utf-8")
            f.head = commit(self, f, "advance")
            complete = packet(f, old_run)

            for session in (False, True):
                for stage in ("missing", "empty", "denied", "coverage", "ledger"):
                    with self.subTest(session=session, stage=stage):
                        value = copy.deepcopy(complete)
                        # These older failures must not obscure the new checks.
                        value.pop("release_owner")
                        value["owner"] = "holdout-owner"
                        value.pop("coverage")
                        expected = "refused: coverage: not attached"
                        if stage == "missing":
                            value.pop("data_use")
                            expected = "refused: data_use: missing"
                        elif stage == "empty":
                            value["data_use"] = {}
                            expected = "refused: data_use: missing"
                        elif stage == "denied":
                            value["data_use"]["allowed_tools"] = ["claude"]
                            expected = (
                                "refused: data_use: denied: "
                                "data_use: tool destination denied: codex"
                            )
                        elif stage == "ledger":
                            value["coverage"] = complete["coverage"]
                            expected = stale_message(old_run, old_head, f.head)
                        before = tree(f.reviews)
                        calls_before = call_bytes(f)
                        result = open_packet(
                            f, value, "--max-rounds", "0",
                            extra_env={
                                "GSTACK_PEER_REVIEW_SESSION": "1"
                            } if session else {},
                        )
                        refusal(
                            self, f, result, before, calls_before, expected
                        )

            current_run, _ = record_run(self, f)
            complete = packet(f, current_run)
            for field, replacement in (
                ("owner", "different-owner"),
                ("allow_repository", False),
                ("allow_history", False),
                ("classification", ""),
            ):
                with self.subTest(policy_field=field):
                    value = copy.deepcopy(complete)
                    value["data_use"][field] = replacement
                    before = tree(f.reviews)
                    result = open_packet(f, value)
                    refusal(
                        self, f, result, before, call_bytes(f),
                        "refused: data_use: denied: data_use: "
                        "repository/history permission and accountable owner required",
                    )

            for empty in (None, {}, [], ""):
                with self.subTest(empty_coverage=empty):
                    value = copy.deepcopy(complete)
                    value["coverage"] = empty
                    before = tree(f.reviews)
                    result = open_packet(f, value)
                    refusal(
                        self, f, result, before, call_bytes(f),
                        "refused: coverage: not attached",
                    )
                    value["exclusions"] = ["This review scores no design items."]
                    opened(self, f, value, "--accept-narrow-packet")

    def test_ledger_order_and_full_commit_identity(self):
        with tempfile.TemporaryDirectory(prefix="holdout-identities-") as directory:
            f = fixture(self, directory)
            old_head = f.head
            first, _ = record_run(self, f)
            second, _ = record_run(self, f)
            (f.repo / "widget.py").write_text(WIDGET + "# next\n", encoding="utf-8")
            f.head = commit(self, f, "next")
            fresh, ledger = record_run(self, f)
            value = packet(f, fresh)

            for order in ((fresh, second, first), (fresh, first, second)):
                with self.subTest(order=order):
                    value["tests"]["ledger_runs"] = [
                        {"repo": str(f.repo), "run_id": run_id}
                        for run_id in order
                    ]
                    before = tree(f.reviews)
                    result = open_packet(f, value)
                    refusal(
                        self, f, result, before, call_bytes(f),
                        stale_message(order[1], old_head, f.head),
                    )

            original = ledger.read_text(encoding="utf-8")
            value = packet(f, fresh)
            for representation in ("short", "absent", "null"):
                with self.subTest(commit_representation=representation):
                    rows = [json.loads(line) for line in original.splitlines()]
                    row = next(row for row in rows if row["id"] == fresh)
                    if representation == "short":
                        row["head"] = f.head[:12]
                        expected_sha = f.head[:12]
                    elif representation == "absent":
                        row.pop("head")
                        expected_sha = "none"
                    else:
                        row["head"] = None
                        expected_sha = "none"
                    ledger.write_text(
                        "".join(json.dumps(row) + "\n" for row in rows),
                        encoding="utf-8",
                    )
                    before = tree(f.reviews)
                    result = open_packet(f, value)
                    refusal(
                        self, f, result, before, call_bytes(f),
                        stale_message(fresh, expected_sha, f.head),
                    )
            ledger.write_text(original, encoding="utf-8")
            git(self, f, "checkout", "-q", "--detach", f.base)
            opened(self, f, value)

    def test_round_ledger_preflight_precedes_session_and_terminal_guards(self):
        with tempfile.TemporaryDirectory(prefix="holdout-round-") as directory:
            f = fixture(self, directory)
            old_head = f.head
            old_run, _ = record_run(self, f)
            value = packet(f, old_run)
            state = opened(self, f, value)
            review_id = state["review_id"]

            (f.repo / "widget.py").write_text(WIDGET + "# newer\n", encoding="utf-8")
            new_head = commit(self, f, "new head")
            new_run, _ = record_run(self, f)
            git(self, f, "checkout", "-q", "--detach", f.base)

            # The first round must apply --head before comparing the named run.
            cases = (
                (old_run, new_head, old_head),
                (new_run, old_head, new_head),
            )
            for run_id, sent_head, recorded_head in cases:
                for session in (False, True):
                    with self.subTest(run=run_id, head=sent_head, session=session):
                        before = tree(f.reviews)
                        result = peer(
                            f, "round", review_id,
                            "--head", f"{f.repo}={sent_head}",
                            "--ledger-run", f"{f.repo}={run_id}",
                            extra_env={
                                "GSTACK_PEER_REVIEW_SESSION": "1"
                            } if session else {},
                        )
                        refusal(
                            self, f, result, before, call_bytes(f),
                            stale_message(run_id, recorded_head, sent_head),
                        )

            # These are retained files outside the candidate checkout.
            state_file = f.reviews / review_id / "state.json"
            original = json.loads(state_file.read_text(encoding="utf-8"))
            prior_file = f.reviews / review_id / "round-1.json"
            for guard in ("closed", "exhausted", "undisposed"):
                with self.subTest(existing_guard=guard):
                    altered = copy.deepcopy(original)
                    if guard == "closed":
                        altered["outcome"] = "no_blocking_findings"
                    elif guard == "exhausted":
                        altered["rounds_used"] = altered["max_rounds"]
                    else:
                        altered.update(
                            outcome="blocking_findings",
                            rounds_used=1,
                            adjudicated_round=1,
                        )
                        prior_file.write_text(json.dumps({
                            "outcome": "blocking_findings",
                            "findings": [{"id": "F1", "severity": "blocking"}],
                        }), encoding="utf-8")
                    state_file.write_text(json.dumps(altered), encoding="utf-8")
                    before = tree(f.reviews)
                    result = peer(
                        f, "round", review_id,
                        "--head", f"{f.repo}={new_head}",
                        "--ledger-run", f"{f.repo}={old_run}",
                    )
                    refusal(
                        self, f, result, before, call_bytes(f),
                        stale_message(old_run, old_head, new_head),
                    )
                    if prior_file.exists():
                        prior_file.unlink()

    def test_first_round_head_controls_all_surface_bytes_and_only_named_runs_gate(self):
        with tempfile.TemporaryDirectory(prefix="holdout-surface-") as directory:
            f = fixture(self, directory)
            old_run, _ = record_run(self, f)
            value = packet(f, old_run)

            new_widget = WIDGET.replace("return 2", "return 3")
            new_caller = CALLER.replace("== 2", "== 3")
            new_settings = '{"expected": 3}\n'
            new_evidence = "The expected result is 3.\n"
            unusual = {
                "space name.txt": b"SPACE HEAD BYTES\n",
                "tab\tname.txt": b"TAB HEAD BYTES\n",
                "line\nname.txt": b"NEWLINE HEAD BYTES\n",
            }
            for name, body in {
                "widget.py": new_widget,
                "caller.py": new_caller,
                "settings.json": new_settings,
                "evidence.txt": new_evidence,
            }.items():
                (f.repo / name).write_text(body, encoding="utf-8")
            for name, body in unusual.items():
                (f.repo / name).write_bytes(body)
            (f.repo / "obsolete.txt").unlink()
            new_head = commit(self, f, "replacement head")
            new_run, _ = record_run(self, f)

            git(self, f, "checkout", "-q", "--detach", f.base)
            (f.repo / "widget.py").write_text("WORKTREE ONLY\n", encoding="utf-8")
            (f.repo / "caller.py").write_text("NO IMPORT HERE\n", encoding="utf-8")
            (f.repo / "settings.json").write_text("WORKTREE SETTINGS\n", encoding="utf-8")
            (f.repo / "evidence.txt").unlink()

            for name_run in (True, False):
                with self.subTest(explicit_ledger_run=name_run):
                    state = opened(self, f, value)
                    previous = (
                        len(f.calls.read_text(encoding="utf-8").splitlines())
                        if f.calls.exists() else 0
                    )
                    args = [
                        "round", state["review_id"],
                        "--head", f"{f.repo}={new_head}",
                    ]
                    if name_run:
                        args += ["--ledger-run", f"{f.repo}={new_run}"]
                    result = peer(f, *args)
                    self.assertTrue(f.calls.exists(), diagnostic(result))
                    calls = [
                        json.loads(line)
                        for line in f.calls.read_text(encoding="utf-8").splitlines()
                    ]
                    self.assertEqual(len(calls), previous + 1, diagnostic(result))
                    files = {
                        name: base64.b64decode(body)
                        for name, body in calls[-1]["files"].items()
                    }

                    # All four files changed between the original packet and
                    # the first round's replacement head.
                    expected = {
                        "widget.py": new_widget.encode(),
                        "caller.py": new_caller.encode(),
                        "settings.json": new_settings.encode(),
                        "evidence.txt": new_evidence.encode(),
                        **unusual,
                    }
                    for name, body in expected.items():
                        with self.subTest(surface_file=name):
                            key = "changed/0-repo/" + name
                            self.assertIn(key, files, diagnostic(result))
                            self.assertEqual(files[key], body)
                    self.assertIn(b"deleted file mode", files["CHANGE.diff"])
                    for name, body in files.items():
                        if name.startswith(("changed/", "callers/", "dependencies/")):
                            self.assertNotIn(b"OLD DELETED FILE CONTENT", body)
                            self.assertNotIn(b"WORKTREE ONLY", body)
                            self.assertNotIn(b"WORKTREE SETTINGS", body)
                    record = json.loads(result.stdout)
                    self.assertEqual(record["repos"][0]["head"], new_head)

    def test_escaping_symlink_is_checked_at_head_with_whitespace_names(self):
        for name in ("escape name.txt", "escape\tname.txt", "escape\nname.txt"):
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory(prefix="holdout-link-") as directory:
                    f = fixture(self, directory)
                    outside = f.root / "outside.txt"
                    outside.write_text("OUTSIDE SENTINEL CONTENT\n", encoding="utf-8")
                    (f.repo / name).symlink_to(outside)
                    f.head = commit(self, f, "escaping link")
                    run_id, _ = record_run(self, f)
                    value = packet(f, run_id)

                    # The working tree contains an ordinary, harmless file at
                    # precisely the name whose committed object is a symlink.
                    git(self, f, "checkout", "-q", "--detach", f.base)
                    (f.repo / name).write_text("harmless checkout file\n", encoding="utf-8")
                    result = open_packet(f, value)
                    if result.returncode:
                        self.assertEqual(result.stdout, "", diagnostic(result))
                        self.assertIn("data_use_denied", result.stderr)
                    else:
                        state = json.loads(result.stdout)
                        self.assertEqual(state["outcome"], "opened", diagnostic(result))
                        result = peer(f, "round", state["review_id"])
                        self.assertNotEqual(result.returncode, 0, diagnostic(result))
                        record = json.loads(result.stdout)
                        self.assertEqual(record["outcome"], "data_use_denied")
                        self.assertIn("symlink", record["error"])
                    self.assertFalse(f.calls.exists(), "Escaping link reached a reviewer.")
                    self.assertNotIn(
                        "OUTSIDE SENTINEL CONTENT", result.stdout + result.stderr
                    )


if __name__ == "__main__":
    unittest.main()
