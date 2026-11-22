"""Black-box holdouts for PLAN.md's viewer command contract.

Candidate code runs only as a separate program. All fixtures and observations
live outside its checkout. No candidate source, metadata, or history is read.

Draft only; not executed. Documentation, repository version changes, hook
checksums, and real agent-flow networking require separate repository/runtime
checks that this black-box interface cannot perform.
"""

import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest


SWARM = "plugins/gstack-execution/scripts/swarm.py"
STATE = b"""{
  "version": 1,
  "base": "1111111111111111111111111111111111111111",
  "integration_head": "1111111111111111111111111111111111111111",
  "budget": 5.0,
  "spent": 0.0,
  "reserved": {},
  "review_cap": 2,
  "plan": {"serial": true, "max_workers": 1, "items": [], "order": []},
  "items": {}
}
"""
EVENTS = b'{"event":"fixture","note":"preserve whitespace and newline"}\n'
SETTINGS = b'{ "permissions": { "allow": [] }, "fixture": true }\n'

FAKE_NPX = r'''
import json
import os
import signal
import socket
import sys

def record(event, **fields):
    fd = os.open(
        os.environ["HOLDOUT_NPX_LOG"],
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    try:
        os.write(fd, (json.dumps(
            dict(event=event, pid=os.getpid(), **fields)
        ) + "\n").encode())
    finally:
        os.close(fd)

def terminate(signum, frame):
    record("terminated", signal=signum)
    raise SystemExit(0)

for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(signum, terminate)
signal.alarm(180)

args = sys.argv[1:]
record("invoked", argv=args)
if len(args) != 5 or args[:4] != [
    "--yes", "agent-flow-app@0.9.6", "--no-open", "--port"
]:
    sys.exit(2)

port = int(args[4])
if not 1 <= port <= 65535:
    sys.exit(2)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind(("127.0.0.1", port))
    server.listen(8)
    record("ready", port=port)
    while True:
        connection, _ = server.accept()
        with connection:
            try:
                connection.sendall(
                    (json.dumps({"pid": os.getpid(), "port": port}) + "\n")
                    .encode()
                )
            except OSError:
                pass
'''

# Observe Python operations without replacing them or restricting networking.
OBSERVER = r'''
import json
import os
import sys

destination = os.environ["HOLDOUT_AUDIT_LOG"]
protected = {
    os.path.abspath(path)
    for path in json.loads(os.environ["HOLDOUT_STATE_PATHS"])
}
settings = os.path.join(os.environ["HOME"], ".claude", "settings.json")

def record(event, **fields):
    fd = os.open(
        destination, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
    )
    try:
        os.write(fd, (json.dumps(dict(event=event, **fields)) + "\n").encode())
    finally:
        os.close(fd)

def observe(event, args):
    if event in {"os.kill", "os.killpg"}:
        record(event, target=args[0], signal=args[1])
    elif event == "open" and isinstance(args[0], (str, bytes)):
        path = os.path.abspath(os.fsdecode(args[0]))
        flags = args[2] or 0
        writing = flags & (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        )
        if path == settings or (path in protected and writing):
            record("forbidden-open", path=path)

sys.addaudithook(observe)
record("observer-ready")
'''


class Holdout(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            sys.platform.startswith("linux"),
            "These holdouts require the specified Linux goal container.",
        )
        self.candidate = os.path.abspath(os.environ["GOAL_CANDIDATE"])

        self.libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        self.assertEqual(
            self.libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0
        )
        self.assertEqual(self.libc.prctl(36, 1, 0, 0, 0), 0)
        self.addCleanup(self.libc.prctl, 36, previous.value, 0, 0, 0)
        old_handler = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        self.addCleanup(signal.signal, signal.SIGCHLD, old_handler)

        temporary = tempfile.TemporaryDirectory(prefix="viewer-holdout-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.assertNotEqual(
            os.path.commonpath([self.candidate, str(self.root)]),
            self.candidate,
            "Fixtures must be outside GOAL_CANDIDATE.",
        )
        self.home = self.root / "home"
        self.settings = self.home / ".claude" / "settings.json"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_bytes(SETTINGS)
        self.bin = self.root / "bin"
        self.no_npx = self.root / "without-npx"
        self.observer = self.root / "observer"
        self.tmp = self.root / "tmp"
        for directory in (self.bin, self.no_npx, self.observer, self.tmp):
            directory.mkdir()
        for name in ("ps", "kill"):
            executable = shutil.which(name)
            if executable:
                for directory in (self.bin, self.no_npx):
                    (directory / name).symlink_to(executable)
        self.fake = self.bin / "npx"
        self.fake.write_text("#!" + sys.executable + "\n" + FAKE_NPX)
        self.fake.chmod(0o755)
        (self.observer / "sitecustomize.py").write_text(OBSERVER)
        self.log = self.root / "npx.jsonl"
        self.runs = []
        self.sequence = 0
        self.run = self._new_run("run with spaces")
        self.addCleanup(self._cleanup_viewers)

    def _new_run(self, name):
        run = self.root / name
        run.mkdir()
        (run / "swarm.json").write_bytes(STATE)
        (run / "swarm-events.jsonl").write_bytes(EVENTS)
        self.runs.append(run)
        return run

    def _records(self, path):
        try:
            text = path.read_text()
        except FileNotFoundError:
            return []
        return [
            json.loads(line)
            for line in text.splitlines(keepends=True)
            if line.endswith("\n")
        ]

    def _events(self, event):
        return [row for row in self._records(self.log) if row["event"] == event]

    def _wait(self, predicate, message, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.025)
        self.fail(message)

    def _environment(self, platform="Darwin", npx=True):
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("PYTHON")
        }
        env.update({
            "HOME": str(self.home),
            "CLAUDE_CONFIG_DIR": str(self.settings.parent),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "TMPDIR": str(self.tmp),
            "PATH": str(self.bin if npx else self.no_npx),
            "PYTHONDONTWRITEBYTECODE": "1",
            "SWARM_VIEWER_PLATFORM": platform,
            "HOLDOUT_NPX_LOG": str(self.log),
            "LC_ALL": "C",
        })
        return env

    def _cli(self, *arguments, platform="Darwin", npx=True):
        audit = self.root / ("audit-%d.jsonl" % self.sequence)
        self.sequence += 1
        env = self._environment(platform, npx)
        env.update({
            "PYTHONPATH": str(self.observer),
            "HOLDOUT_AUDIT_LOG": str(audit),
            "HOLDOUT_STATE_PATHS": json.dumps([
                str(run / name)
                for run in self.runs
                for name in ("swarm.json", "swarm-events.jsonl")
            ]),
        })
        result = subprocess.run(
            [sys.executable, "-B", SWARM, *map(str, arguments)],
            cwd=self.candidate,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        records = self._records(audit)
        self.assertTrue(
            any(row["event"] == "observer-ready" for row in records),
            "Audit observation must initialize in the candidate process.",
        )
        self.assertEqual(
            [row for row in records if row["event"] == "forbidden-open"], []
        )
        for run in self.runs:
            self.assertEqual((run / "swarm.json").read_bytes(), STATE)
            self.assertEqual((run / "swarm-events.jsonl").read_bytes(), EVENTS)
        self.assertEqual(self.settings.read_bytes(), SETTINGS)
        return result, records

    def _success(self, result, output):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, output)
        self.assertEqual(result.stderr, "")

    def _no_signals(self, records):
        self.assertEqual([
            row for row in records
            if row["event"] in {"os.kill", "os.killpg"} and row["signal"] != 0
        ], [], "No process may receive a nonzero signal on this path.")

    def _exit_info(self, pid):
        return os.waitid(
            os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT
        )

    def _probe(self, viewer):
        with socket.create_connection(
            ("127.0.0.1", viewer["port"]), timeout=1
        ) as connection:
            connection.settimeout(1)
            data = b""
            while b"\n" not in data and len(data) < 4096:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                data += chunk
        self.assertEqual(
            json.loads(data),
            {"pid": viewer["pid"], "port": viewer["port"]},
        )

    def _start(self, run):
        before = len(self._events("invoked"))
        ready_before = len(self._events("ready"))
        result, _ = self._cli("viewer-start", run)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        match = re.fullmatch(
            r"viewer: http://127\.0\.0\.1:([0-9]+)\n", result.stdout
        )
        self.assertIsNotNone(match, result.stdout)
        port = int(match.group(1))
        self.assertTrue(1 <= port <= 65535)
        self._wait(
            lambda: len(self._events("ready")) > ready_before,
            "An address was printed without a running viewer.",
        )
        self.assertEqual(len(self._events("invoked")), before + 1)
        self.assertEqual(len(self._events("ready")), ready_before + 1)
        invocation = self._events("invoked")[-1]
        viewer = self._events("ready")[-1]
        self.assertEqual(invocation["argv"], [
            "--yes", "agent-flow-app@0.9.6", "--no-open", "--port", str(port)
        ])
        self.assertEqual(viewer["pid"], invocation["pid"])
        self.assertEqual(viewer["port"], port)
        self.assertIsNone(self._exit_info(viewer["pid"]))
        self.assertTrue((run / "viewer.pid").read_bytes())
        self._probe(viewer)
        return viewer

    def _stop(self, run, expected="stopped", platform="Darwin", npx=True):
        result, records = self._cli(
            "viewer-stop", run, platform=platform, npx=npx
        )
        self._success(result, "viewer: %s\n" % expected)
        if expected == "not running":
            self._no_signals(records)

    def _crash(self, viewer, reap):
        os.kill(viewer["pid"], signal.SIGKILL)
        ended = self._wait(
            lambda: self._exit_info(viewer["pid"]),
            "The fake viewer did not exit.",
        )
        self.assertEqual(ended.si_code, os.CLD_KILLED)
        self.assertEqual(ended.si_status, signal.SIGKILL)
        if reap:
            os.waitpid(viewer["pid"], 0)

    def _cleanup_viewers(self):
        for pid in {row["pid"] for row in self._events("invoked")}:
            try:
                ended = self._exit_info(pid)
            except ChildProcessError:
                continue
            if ended is None:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self._wait(
                lambda pid=pid: self._exit_info(pid),
                "Fake viewer did not terminate during cleanup.",
            )
            os.waitpid(pid, 0)

    @staticmethod
    def _cleanup_child(child):
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)

    def test_argument_validation_precedes_every_other_check(self):
        viewer = self._start(self.run)
        metadata = (self.run / "viewer.pid").read_bytes()
        for platform, npx in (
            ("Darwin", True), ("Linux", True), ("Darwin", False)
        ):
            for command in ("viewer-start", "viewer-stop"):
                cases = [
                    (command,),
                    (command, self.run, "extra"),
                    (command, self.run, "--port", "49152"),
                ]
                for option in (
                    "--port=49152", "--budget=1", "--json",
                    "--unknown", "--help", "-h", "--",
                ):
                    cases.extend([
                        (command, option),
                        (option, command, self.run),
                        (command, option, self.run),
                        (command, self.run, option),
                    ])
                for arguments in cases:
                    with self.subTest(
                        platform=platform, npx=npx, arguments=arguments
                    ):
                        result, records = self._cli(
                            *arguments, platform=platform, npx=npx
                        )
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertRegex(result.stderr.lower(), r"(?m)^usage:")
                        self.assertNotIn("viewer: unavailable", result.stderr)
                        self._no_signals(records)
                        self.assertEqual(len(self._events("invoked")), 1)
                        self.assertEqual(
                            (self.run / "viewer.pid").read_bytes(), metadata
                        )
                        self.assertIsNone(self._exit_info(viewer["pid"]))
        self._probe(viewer)

    def test_unavailable_start_wins_but_stop_remains_available(self):
        viewer = self._start(self.run)
        for platform, npx in (
            ("Linux", True), ("Windows", True), ("", True),
            ("darwin", True), ("Darwin", False), ("Linux", False),
        ):
            with self.subTest(platform=platform, npx=npx):
                result, records = self._cli(
                    "viewer-start", self.run, platform=platform, npx=npx
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(len(result.stderr.splitlines()), 1)
                self.assertTrue(result.stderr.startswith("viewer: unavailable"))
                self.assertRegex(
                    result.stderr.lower(), r"\bswarm\b.*\bunaffected\b"
                )
                self._no_signals(records)
                self.assertEqual(len(self._events("invoked")), 1)
                self.assertIsNone(self._exit_info(viewer["pid"]))
                self._probe(viewer)

        result, _ = self._cli("viewer-start", self.run)
        self._success(
            result, "viewer: http://127.0.0.1:%d\n" % viewer["port"]
        )
        self.assertEqual(len(self._events("invoked")), 1)

        self._stop(self.run, platform="Linux", npx=False)
        self._wait(
            lambda: self._exit_info(viewer["pid"]),
            "viewer-stop depended on startup availability.",
        )
        self._stop(
            self.run, expected="not running", platform="Linux", npx=False
        )

    def test_stale_birth_identity_never_adopts_or_signals_another_process(self):
        for operation in ("viewer-stop", "viewer-start"):
            with self.subTest(operation=operation):
                run = self._new_run("recycled-" + operation)
                old = self._start(run)
                metadata = (run / "viewer.pid").read_bytes()
                original_args = self._events("invoked")[-1]["argv"]
                self._crash(old, reap=True)

                # Separate process birth times even with second-resolution ps.
                time.sleep(1.1)
                decoy = subprocess.Popen(
                    [str(self.fake), *original_args],
                    cwd=self.root,
                    env=self._environment(),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self.addCleanup(self._cleanup_child, decoy)
                self._wait(
                    lambda: any(
                        row["pid"] == decoy.pid for row in self._events("ready")
                    ),
                    "The replacement-identity fixture did not start.",
                )

                # Model PID reuse without assuming JSON keys or field order:
                # preserve the candidate's stored birth identity and port.
                stale, replacements = re.subn(
                    rb"(?<![0-9])" + str(old["pid"]).encode() + rb"(?![0-9])",
                    str(decoy.pid).encode(),
                    metadata,
                )
                self.assertGreater(
                    replacements, 0, "viewer.pid must contain the viewer PID."
                )
                (run / "viewer.pid").write_bytes(stale)
                calls_before = len(self._events("invoked"))

                if operation == "viewer-stop":
                    self._stop(run, expected="not running")
                    self.assertEqual(
                        len(self._events("invoked")), calls_before
                    )
                    replacement = self._start(run)
                else:
                    replacement = self._start(run)

                self.assertNotEqual(replacement["pid"], decoy.pid)
                self.assertNotEqual(replacement["port"], old["port"])
                self.assertIsNone(self._exit_info(decoy.pid))
                self.assertEqual([
                    row for row in self._events("terminated")
                    if row["pid"] == decoy.pid
                ], [])
                self._probe({"pid": decoy.pid, "port": old["port"]})
                self._stop(run)
                self._wait(
                    lambda: self._exit_info(replacement["pid"]),
                    "Stopping the replacement left it running.",
                )
                self.assertIsNone(self._exit_info(decoy.pid))

    def test_zombie_and_reaped_crashes_are_isolated_between_runs(self):
        survivor_run = self._new_run("unrelated run")
        survivor = self._start(survivor_run)
        for reap in (False, True):
            with self.subTest(reap=reap):
                run = self._new_run("crashed-%s" % reap)
                viewer = self._start(run)
                self._crash(viewer, reap=reap)
                self._stop(run, expected="not running")
                if not reap:
                    self.assertIsNotNone(self._exit_info(viewer["pid"]))

                replacement = self._start(run)
                self.assertNotEqual(replacement["pid"], viewer["pid"])
                self._crash(replacement, reap=reap)

                # Restart must recover without viewer-stop clearing metadata.
                restarted = self._start(run)
                self.assertNotEqual(restarted["pid"], replacement["pid"])
                self._stop(run)
                self._wait(
                    lambda: self._exit_info(restarted["pid"]),
                    "viewer-stop reported success before ending its viewer.",
                )
                self._stop(run, expected="not running")
                self.assertIsNone(self._exit_info(survivor["pid"]))
                self._probe(survivor)

        self._stop(survivor_run)
        self._wait(
            lambda: self._exit_info(survivor["pid"]),
            "The independent viewer did not stop.",
        )


if __name__ == "__main__":
    unittest.main()
