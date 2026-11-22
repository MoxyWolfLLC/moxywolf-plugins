"""Black-box holdout tests using only external fixtures and CLI observations.

Draft, not executed here. Documentation, version changes, checkout protections,
and the real npm package's behavior require separate verification.
"""

import ctypes
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest


TOOL = "plugins/gstack-execution/scripts/swarm.py"
STATE = b"""{
  "plan": {"serial": true, "max_workers": 1, "items": [], "order": []},
  "base": "1111111111111111111111111111111111111111",
  "integration_head": "1111111111111111111111111111111111111111",
  "budget": 5.0,
  "spent": 0.0,
  "reserved": {},
  "review_cap": 2,
  "items": {}
}
"""
EVENTS = b'{"event":"init","budget":5.0,"items":[]}\n'
SETTINGS = b'{"hooks":{},"permissions":{"allow":[]}}\n'

FAKE_NPX = r'''
import json
import os
import signal
import socket
import sys
import time

def record(kind, **fields):
    data = (json.dumps(dict(kind=kind, pid=os.getpid(), **fields)) + "\n").encode()
    fd = os.open(os.environ["HOLDOUT_NPX_LOG"],
                 os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)

def terminate(number, frame):
    record("signal", number=number)
    raise SystemExit(0)

for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    signal.signal(number, terminate)

record("start", argv=sys.argv[1:])
listener = socket.socket()
try:
    port = int(sys.argv[sys.argv.index("--port") + 1])
    listener.bind(("127.0.0.1", port))
    listener.listen()
except Exception as error:
    record("bind-error", error=str(error))
    raise SystemExit(1)

record("ready", port=port)
deadline = time.monotonic() + 180
while time.monotonic() < deadline:
    time.sleep(0.05)
'''

# Observe Python file opens and signal attempts without denying operations.
# This does not inspect candidate files or alter networking.
AUDITOR = r'''
import json
import os
import platform
import sys

if "HOLDOUT_NATIVE_PLATFORM" in os.environ:
    platform.system = lambda: os.environ["HOLDOUT_NATIVE_PLATFORM"]

root = os.path.abspath(os.environ["HOLDOUT_ROOT"])
settings = os.path.join(root, "home", ".claude", "settings.json")
protected = {
    os.path.join(root, name, filename)
    for name in ("run one", "run two")
    for filename in ("swarm.json", "swarm-events.jsonl")
}
log = os.environ["HOLDOUT_AUDIT_LOG"]
write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

def audit(event, args):
    entry = None
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = os.path.abspath(os.fsdecode(args[0]))
        mode, flags = args[1], args[2]
        writing = (
            isinstance(mode, str) and any(char in mode for char in "wax+")
        ) or (isinstance(flags, int) and bool(flags & write_flags))
        if path == settings or (path in protected and writing):
            entry = {"kind": "forbidden-open", "path": path,
                     "mode": mode, "flags": flags}
    elif event in ("os.kill", "os.killpg"):
        entry = {"kind": "signal-attempt", "event": event,
                 "target": args[0], "number": args[1]}
    if entry is not None:
        data = (json.dumps(entry) + "\n").encode()
        fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)

sys.addaudithook(audit)
'''


class Holdout(unittest.TestCase):
    def setUp(self):
        self.candidate = os.path.abspath(os.environ["GOAL_CANDIDATE"])
        temporary = tempfile.TemporaryDirectory(prefix="viewer-holdout-", dir="/tmp")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.assertNotEqual(
            os.path.commonpath([self.candidate, str(self.root)]),
            self.candidate,
            "Fixtures must be outside the candidate checkout",
        )

        self.runs = [self.root / "run one", self.root / "run two"]
        for run in self.runs:
            run.mkdir()
            (run / "swarm.json").write_bytes(STATE)
            (run / "swarm-events.jsonl").write_bytes(EVENTS)

        self.home = self.root / "home"
        self.settings = self.home / ".claude" / "settings.json"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_bytes(SETTINGS)

        self.bin = self.root / "bin"
        self.empty_bin = self.root / "empty-bin"
        self.probe = self.root / "probe"
        for directory in (self.bin, self.empty_bin, self.probe):
            directory.mkdir()
        (self.probe / "sitecustomize.py").write_text(AUDITOR, encoding="utf-8")
        executable = self.bin / "npx"
        executable.write_text(
            "#!" + sys.executable + "\n" + FAKE_NPX, encoding="utf-8"
        )
        executable.chmod(0o755)
        self.log = self.root / "npx.jsonl"
        self.audit_log = self.root / "audit.jsonl"

        self.subreaper = False
        if sys.platform.startswith("linux"):
            libc = ctypes.CDLL(None, use_errno=True)
            previous = ctypes.c_int()
            self.assertEqual(libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0)
            self.assertEqual(libc.prctl(36, 1, 0, 0, 0), 0)
            self.subreaper = True

            def restore():
                self.assertEqual(libc.prctl(36, previous.value, 0, 0, 0), 0)

            self.addCleanup(restore)
        self.addCleanup(self._cleanup_processes)

    def _records(self, path):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return []
        # A concurrently appended final record may not yet be complete.
        return [json.loads(line) for line in data.split(b"\n")[:-1] if line]

    def _starts(self):
        return [entry for entry in self._records(self.log) if entry["kind"] == "start"]

    def _state(self, pid):
        if sys.platform.startswith("linux"):
            try:
                value = Path("/proc", str(pid), "stat").read_text()
            except FileNotFoundError:
                return None
            return value.rsplit(") ", 1)[1].split()[0]
        result = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "stat="],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()[:1] or None

    def _alive(self, pid):
        return self._state(pid) not in (None, "Z", "X")

    def _wait(self, predicate, message, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(0.02)
        self.fail(message)

    def _cleanup_processes(self):
        deadline = time.monotonic() + 0.5
        seen = set()
        while time.monotonic() < deadline:
            for entry in self._starts():
                pid = entry["pid"]
                if pid in seen:
                    continue
                seen.add(pid)
                try:
                    if self._alive(pid):
                        os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass
            time.sleep(0.02)

    def _call(self, arguments, platform="Darwin", npx=True, native=None):
        env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "HOLDOUT_NATIVE_PLATFORM"):
            env.pop(key, None)
        env.update(
            HOME=str(self.home),
            CLAUDE_CONFIG_DIR=str(self.home / ".claude"),
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_CACHE_HOME=str(self.home / ".cache"),
            npm_config_cache=str(self.home / ".npm"),
            TMPDIR=str(self.root),
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONPATH=str(self.probe),
            HOLDOUT_ROOT=str(self.root),
            HOLDOUT_NPX_LOG=str(self.log),
            HOLDOUT_AUDIT_LOG=str(self.audit_log),
            PATH=str(self.bin) + os.pathsep + os.defpath
            if npx else str(self.empty_bin),
        )
        if platform is None:
            env.pop("SWARM_VIEWER_PLATFORM", None)
        else:
            env["SWARM_VIEWER_PLATFORM"] = platform
        if native is not None:
            env["HOLDOUT_NATIVE_PLATFORM"] = native

        try:
            result = subprocess.run(
                [sys.executable, "-B", TOOL, *map(str, arguments)],
                cwd=self.candidate,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            self.fail("Viewer command failed to return within 15 seconds")

        forbidden = [
            entry for entry in self._records(self.audit_log)
            if entry["kind"] == "forbidden-open"
        ]
        self.assertEqual(forbidden, [], "Forbidden file access, even if bytes survived")
        for run in self.runs:
            self.assertEqual((run / "swarm.json").read_bytes(), STATE)
            self.assertEqual((run / "swarm-events.jsonl").read_bytes(), EVENTS)
        self.assertEqual(self.settings.read_bytes(), SETTINGS)
        return result

    def _stable_count(self, expected):
        deadline = time.monotonic() + 0.25
        while time.monotonic() < deadline:
            self.assertEqual(len(self._starts()), expected)
            time.sleep(0.02)

    def _address(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        match = re.fullmatch(r"viewer: http://127\.0\.0\.1:([0-9]+)\n", result.stdout)
        self.assertIsNotNone(match, repr(result.stdout))
        port = int(match.group(1))
        self.assertTrue(1 <= port <= 65535)
        return port

    def _start(self, run):
        count = len(self._starts())
        result = self._call(["viewer-start", run])
        port = self._address(result)
        self._wait(lambda: len(self._starts()) > count, "npx was never executed")
        self._stable_count(count + 1)
        entry = self._starts()[-1]
        self.assertEqual(
            entry["argv"],
            ["--yes", "agent-flow-app@0.9.6", "--no-open", "--port", str(port)],
        )
        self._wait(
            lambda: any(
                record["kind"] == "ready" and record["pid"] == entry["pid"]
                for record in self._records(self.log)
            ),
            "The selected port was not usable by the viewer",
        )
        self.assertTrue(self._alive(entry["pid"]))
        self.assertTrue((run / "viewer.pid").is_file())
        return entry["pid"], result.stdout

    def _stop(self, run, expected, **environment):
        before = len(self._records(self.audit_log))
        result = self._call(["viewer-stop", run], **environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, expected + "\n")
        if expected == "viewer: not running":
            attempts = [
                entry for entry in self._records(self.audit_log)[before:]
                if entry["kind"] == "signal-attempt" and entry["number"] != 0
            ]
            self.assertEqual(attempts, [], "An absent viewer must not be signalled")

    def _unavailable(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        lines = result.stderr.splitlines()
        self.assertEqual(len(lines), 1, result.stderr)
        self.assertTrue(lines[0].startswith("viewer: unavailable"), result.stderr)
        self.assertRegex(lines[0].lower(), r"\bswarm\b.*\bunaffected\b")

    def test_argument_errors_precede_live_viewer_and_availability_checks(self):
        run = self.runs[0]
        pid, address = self._start(run)
        for command in ("viewer-start", "viewer-stop"):
            arguments = [[command], [command, run, "extra"]]
            for option in ("--help", "-h", "--", "--port=43129", "--unknown"):
                arguments.extend([
                    [option, command, run],
                    [command, option, run],
                    [command, run, option],
                    [command, option],
                ])
            arguments.extend([
                ["--port", "43129", command, run],
                [command, "--port", "43129", run],
                [command, run, "--port", "43129"],
            ])
            for argv in arguments:
                with self.subTest(argv=argv):
                    result = self._call(argv)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertTrue(result.stderr.lower().startswith("usage:"))
                    self.assertNotIn("viewer: unavailable", result.stderr)
                    self.assertTrue(self._alive(pid), "Invalid arguments stopped the viewer")
        self._stable_count(1)
        again = self._call(["viewer-start", run])
        self._address(again)
        self.assertEqual(again.stdout, address)

    def test_unavailable_overrides_existing_viewer_including_empty_on_darwin(self):
        run = self.runs[0]
        pid, address = self._start(run)
        cases = [
            {"platform": "", "native": "Darwin"},
            {"platform": "", "native": "Darwin", "npx": False},
            {"platform": "Linux"},
            {"platform": "darwin"},
            {"platform": "Darwin", "npx": False},
        ]
        for environment in cases:
            with self.subTest(environment=environment):
                self._unavailable(self._call(["viewer-start", run], **environment))
                self._stable_count(1)
                self.assertTrue(self._alive(pid))
        again = self._call(["viewer-start", run])
        self._address(again)
        self.assertEqual(again.stdout, address)
        self._stable_count(1)

    def test_stop_works_without_npx_or_an_available_platform(self):
        run = self.runs[0]
        for platform in ("Linux", "", "Darwin"):
            with self.subTest(platform=platform):
                pid, _ = self._start(run)
                self._stop(
                    run, "viewer: stopped", platform=platform, npx=False
                )
                self._wait(lambda: not self._alive(pid), "viewer-stop left its process alive")
                self._stop(
                    run, "viewer: not running", platform=platform, npx=False
                )

    def test_independent_runs_use_free_ports_and_stop_only_their_own_viewers(self):
        first, second = self.runs
        first_pid, first_address = self._start(first)
        second_pid, second_address = self._start(second)
        self.assertNotEqual(first_pid, second_pid)
        self.assertNotEqual(first_address, second_address)

        for run, address in ((first, first_address), (second, second_address)):
            result = self._call(["viewer-start", run])
            self._address(result)
            self.assertEqual(result.stdout, address)
        self._stable_count(2)

        self._stop(first, "viewer: stopped")
        self._wait(lambda: not self._alive(first_pid), "First viewer survived stop")
        self.assertTrue(self._alive(second_pid), "Stopping one run killed another viewer")
        self._stop(first, "viewer: not running")
        self.assertTrue(self._alive(second_pid))
        self._stop(second, "viewer: stopped")
        self._wait(lambda: not self._alive(second_pid), "Second viewer survived stop")

    def test_crashed_and_zombie_viewers_are_replaced_without_forbidden_opens(self):
        if not self.subreaper:
            self.skipTest("Deterministic zombie ownership requires the Linux test container")
        run = self.runs[0]
        for reap, stop_first in ((False, True), (True, True), (False, False)):
            with self.subTest(reap=reap, stop_first=stop_first):
                crashed_pid, _ = self._start(run)
                os.kill(crashed_pid, signal.SIGKILL)
                self._wait(
                    lambda: self._state(crashed_pid) == "Z",
                    "Killed viewer did not become a zombie",
                )
                self._wait(
                    lambda: os.waitid(
                        os.P_PID,
                        crashed_pid,
                        os.WEXITED | os.WNOHANG | os.WNOWAIT,
                    ),
                    "The test runner did not adopt the crashed viewer",
                )
                if reap:
                    self.assertEqual(os.waitpid(crashed_pid, 0)[0], crashed_pid)

                self._unavailable(
                    self._call(["viewer-start", run], platform="", native="Darwin")
                )
                if stop_first:
                    self._stop(run, "viewer: not running")

                replacement_pid, _ = self._start(run)
                self.assertTrue(self._alive(replacement_pid))
                if not reap:
                    self.assertNotEqual(replacement_pid, crashed_pid)
                    self.assertEqual(self._state(crashed_pid), "Z")
                    self.assertEqual(os.waitpid(crashed_pid, 0)[0], crashed_pid)

                self._stop(run, "viewer: stopped")
                self._wait(
                    lambda: not self._alive(replacement_pid),
                    "Replacement viewer survived stop",
                )
                self._stop(run, "viewer: not running")


if __name__ == "__main__":
    unittest.main()
