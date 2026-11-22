# drafted-by: gpt/gpt-6-astra
"""Black-box viewer tests for the networkless Linux goal container.

Candidate code runs only as a separate program. Fixtures and observations live
outside GOAL_CANDIDATE. No test reads candidate source, metadata, or history.

Coverage limits:
* The fake npx checks launch arguments and process lifecycle, not the real npm
  package's networking or installation behavior.
* Runtime hooks mutation attempts are observed through Python audit events.
  The checkout's hooks.json checksum cannot be verified without reading that
  file. The required SHA-256
  542f7e30d883d326d10441ed8f3a7c409e4d4720a9fac0c72f776f9d152b0092
  therefore still requires a separate repository gate.
* This draft has not been executed.
"""

import ctypes
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest


SWARM = "plugins/gstack-execution/scripts/swarm.py"
PINNED_PACKAGE = "agent-flow-app@0.9.6"

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
        os.environ["VIEWER_TEST_NPX_LOG"],
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    try:
        os.write(
            fd,
            (json.dumps(dict(event=event, pid=os.getpid(), **fields)) + "\n")
            .encode(),
        )
    finally:
        os.close(fd)

def terminate(signum, frame):
    record("terminated", signal=signum)
    raise SystemExit(0)

signal.signal(signal.SIGTERM, terminate)
signal.signal(signal.SIGINT, terminate)
signal.signal(signal.SIGALRM, terminate)
signal.alarm(60)

args = sys.argv[1:]
record("invoked", argv=args)
if len(args) != 5 or args[:4] != [
    "--yes", "agent-flow-app@0.9.6", "--no-open", "--port"
]:
    sys.exit(2)

try:
    port = int(args[4])
except ValueError:
    sys.exit(2)
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

# Observation only: no replacement of candidate functions, process operations,
# or networking, and no reads of protected files.
AUDIT_OBSERVER = r'''
import json
import os
import sys

destination = os.environ["VIEWER_TEST_AUDIT_LOG"]

def record(event, **fields):
    fd = os.open(
        destination, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
    )
    try:
        os.write(
            fd,
            (json.dumps(
                dict(event=event, pid=os.getpid(), **fields), default=str
            ) + "\n").encode(),
        )
    finally:
        os.close(fd)

def protected(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return None
    path = os.path.abspath(os.fsdecode(path))
    if path.endswith("/plugins/gstack-execution/hooks/hooks.json"):
        return "plugin-hooks"
    if path == os.path.join(os.environ["HOME"], ".claude", "settings.json"):
        return "personal-settings"
    if os.path.basename(path) in {"swarm.json", "swarm-events.jsonl"}:
        return "run-state"
    return None

def observe(event, args):
    if event in {"os.kill", "os.killpg"}:
        record(event, target=args[0], signal=args[1])
    elif event == "subprocess.Popen":
        record(event, executable=args[0], argv=args[1])
    elif event == "open":
        kind = protected(args[0])
        flags = args[2] or 0
        writing = flags & (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        )
        if kind and (writing or kind == "personal-settings"):
            record("protected-access", kind=kind, operation=event)
    elif event in {
        "os.remove", "os.rename", "os.rmdir", "os.link", "os.symlink",
        "os.chmod", "os.chown", "os.truncate",
    }:
        paths = args[:2] if event in {
            "os.rename", "os.link", "os.symlink"
        } else args[:1]
        for path in paths:
            kind = protected(path)
            if kind:
                record("protected-access", kind=kind, operation=event)

sys.addaudithook(observe)
record("observer-ready")
'''


class SwarmAgentView(unittest.TestCase):
    def setUp(self):
        self.assertIn("GOAL_CANDIDATE", os.environ)
        self.candidate = os.path.abspath(os.environ["GOAL_CANDIDATE"])
        self.assertTrue(
            sys.platform.startswith("linux"),
            "Zombie tests require the specified Linux goal container.",
        )

        # Adopt orphaned viewers so the test controls when they are reaped.
        self.libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        self.assertEqual(
            self.libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0,
            "PR_GET_CHILD_SUBREAPER failed",
        )
        self.assertEqual(
            self.libc.prctl(36, 1, 0, 0, 0), 0,
            "PR_SET_CHILD_SUBREAPER failed",
        )
        self.addCleanup(self.libc.prctl, 36, previous.value, 0, 0, 0)
        old_handler = signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        self.addCleanup(signal.signal, signal.SIGCHLD, old_handler)

        temporary = tempfile.TemporaryDirectory(prefix="swarm-viewer-goal-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.assertNotEqual(
            os.path.commonpath([self.candidate, str(self.root)]),
            self.candidate,
            "Fixtures must be outside the candidate checkout.",
        )

        self.home = self.root / "home"
        self.settings = self.home / ".claude" / "settings.json"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_bytes(SETTINGS)
        self.tmp = self.root / "tmp"
        self.tmp.mkdir()
        self.bin = self.root / "bin"
        self.without_npx = self.root / "without-npx"
        self.bin.mkdir()
        self.without_npx.mkdir()

        # Preserve ordinary process inspection while excluding real npx.
        for name in ("ps", "kill"):
            executable = shutil.which(name)
            if executable:
                for directory in (self.bin, self.without_npx):
                    (directory / name).symlink_to(executable)

        fake = self.bin / "npx"
        fake.write_text("#!" + sys.executable + "\n" + FAKE_NPX)
        fake.chmod(0o755)
        observer = self.root / "observer"
        observer.mkdir()
        (observer / "sitecustomize.py").write_text(AUDIT_OBSERVER)
        self.observer = observer
        self.npx_log = self.root / "npx.jsonl"
        self.audit_paths = []
        self.run = self._new_run("run")
        self.addCleanup(self._cleanup_viewers)

    def _new_run(self, name):
        run = self.root / name
        run.mkdir()
        (run / "swarm.json").write_bytes(STATE)
        (run / "swarm-events.jsonl").write_bytes(EVENTS)
        return run

    def _records(self, path):
        try:
            data = path.read_text()
        except FileNotFoundError:
            return []
        return [
            json.loads(line)
            for line in data.splitlines(keepends=True)
            if line.endswith("\n")
        ]

    def _invocations(self):
        return [
            row for row in self._records(self.npx_log)
            if row["event"] == "invoked"
        ]

    def _ready(self):
        return [
            row for row in self._records(self.npx_log)
            if row["event"] == "ready"
        ]

    def _audit(self):
        return [
            row for path in self.audit_paths for row in self._records(path)
        ]

    def _wait(self, predicate, message, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.025)
        self.fail(message)

    def _cli(self, *arguments, platform="Darwin", npx=True):
        audit = self.root / ("audit-%d.jsonl" % len(self.audit_paths))
        self.audit_paths.append(audit)
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("PYTHON")
        }
        env.update({
            "HOME": str(self.home),
            "CLAUDE_CONFIG_DIR": str(self.settings.parent),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "TMPDIR": str(self.tmp),
            "PATH": str(self.bin if npx else self.without_npx),
            "PYTHONPATH": str(self.observer),
            "PYTHONDONTWRITEBYTECODE": "1",
            "SWARM_VIEWER_PLATFORM": platform,
            "VIEWER_TEST_NPX_LOG": str(self.npx_log),
            "VIEWER_TEST_AUDIT_LOG": str(audit),
            "LC_ALL": "C",
        })
        try:
            result = subprocess.run(
                [sys.executable, "-B", SWARM, *map(str, arguments)],
                cwd=self.candidate,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired as error:
            self.fail(
                "Viewer command did not return promptly: "
                "stdout=%r stderr=%r" % (error.stdout, error.stderr)
            )
        self.assertTrue(
            any(
                row["event"] == "observer-ready"
                for row in self._records(audit)
            ),
            "The subprocess audit observer did not initialize.",
        )
        return result, audit

    def _exit_info(self, pid):
        return os.waitid(
            os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT
        )

    def _cleanup_viewers(self):
        # Never signal a PID after it has been reaped and could be reused.
        for pid in {row["pid"] for row in self._invocations()}:
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
                "Fake npx did not terminate during cleanup.",
            )
            os.waitpid(pid, 0)

    def _probe(self, port):
        try:
            with socket.create_connection(
                ("127.0.0.1", port), timeout=1
            ) as client:
                client.settimeout(1)
                data = b""
                while b"\n" not in data and len(data) < 4096:
                    part = client.recv(4096)
                    if not part:
                        break
                    data += part
            return json.loads(data)
        except (OSError, ValueError):
            return None

    def _assert_success(self, result, stdout):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, stdout)
        self.assertEqual(result.stderr, "")

    def _assert_no_signals(self, audit):
        self.assertEqual(
            [
                row for row in self._records(audit)
                if row["event"] in {"os.kill", "os.killpg"}
                and row["signal"] != 0
            ],
            [],
            "A missing or crashed viewer must receive no signal.",
        )

    def _accept_absent(self, result, command):
        if result.returncode != 2:
            return False
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            result.stderr, "swarm: unknown command %s\n" % command
        )
        return True

    def _start(self, run=None, allow_absent=False):
        run = self.run if run is None else run
        calls_before = len(self._invocations())
        ready_before = len(self._ready())
        result, _ = self._cli("viewer-start", run)
        if allow_absent and self._accept_absent(result, "viewer-start"):
            self.assertEqual(len(self._invocations()), calls_before)
            return None

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        match = re.fullmatch(
            r"viewer: http://127\.0\.0\.1:([0-9]+)\n", result.stdout
        )
        self.assertIsNotNone(match, result.stdout)
        port = int(match.group(1))
        self.assertTrue(1 <= port <= 65535)
        self._wait(
            lambda: len(self._ready()) > ready_before,
            "viewer-start printed an address without launching a viewer.",
        )
        self.assertEqual(len(self._ready()), ready_before + 1)
        self.assertEqual(len(self._invocations()), calls_before + 1)
        invocation = self._invocations()[-1]
        viewer = self._ready()[-1]
        self.assertEqual(
            invocation["argv"],
            ["--yes", PINNED_PACKAGE, "--no-open", "--port", str(port)],
        )
        self.assertEqual(viewer["pid"], invocation["pid"])
        self.assertEqual(viewer["port"], port)
        self.assertIsNone(self._exit_info(viewer["pid"]))
        self.assertEqual(
            self._probe(port), {"pid": viewer["pid"], "port": port}
        )
        self.assertTrue((run / "viewer.pid").read_bytes())
        return viewer

    def _stop(self, run=None, expected="stopped", allow_absent=False):
        run = self.run if run is None else run
        result, audit = self._cli("viewer-stop", run)
        if allow_absent and self._accept_absent(result, "viewer-stop"):
            return
        self._assert_success(result, "viewer: %s\n" % expected)
        if expected == "not running":
            self._assert_no_signals(audit)

    def _crash(self, viewer, reap=False):
        os.kill(viewer["pid"], signal.SIGKILL)
        ended = self._wait(
            lambda: self._exit_info(viewer["pid"]),
            "Fake viewer did not crash.",
        )
        self.assertEqual(ended.si_pid, viewer["pid"])
        self.assertEqual(ended.si_code, os.CLD_KILLED)
        self.assertEqual(ended.si_status, signal.SIGKILL)
        if reap:
            os.waitpid(viewer["pid"], 0)

    def _assert_run_unchanged(self, run=None):
        run = self.run if run is None else run
        self.assertEqual((run / "swarm.json").read_bytes(), STATE)
        self.assertEqual((run / "swarm-events.jsonl").read_bytes(), EVENTS)
        self.assertEqual(
            [
                row for row in self._audit()
                if row["event"] == "protected-access"
                and row["kind"] == "run-state"
            ],
            [],
            "Viewer commands must not open run state for writing.",
        )

    def _assert_unavailable(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertTrue(result.stderr.startswith("viewer: unavailable"))
        self.assertRegex(
            result.stderr.lower(), r"\bswarm\b.*\bunaffected\b"
        )

    def test_viewer_start_runs_pinned_agent_flow_locally(self):
        """Outcome.
        Scenario: Given a Mac host with npx on the path, when `swarm.py viewer-start <run>` runs, then it starts `npx --yes agent-flow-app@0.9.6 --no-open --port <port>` in the background and prints the viewer address on standard output
        """
        viewer = self._start()
        metadata = (self.run / "viewer.pid").read_bytes()
        result, _ = self._cli("viewer-start", self.run)
        self._assert_success(
            result, "viewer: http://127.0.0.1:%d\n" % viewer["port"]
        )
        self.assertEqual(len(self._invocations()), 1)
        self.assertEqual((self.run / "viewer.pid").read_bytes(), metadata)
        self.assertIsNone(self._exit_info(viewer["pid"]))
        self.assertEqual(
            self._probe(viewer["port"]),
            {"pid": viewer["pid"], "port": viewer["port"]},
        )

    def test_viewer_start_without_a_mac_or_npx_says_unavailable_and_exits_zero(self):
        """Outcome.
        Scenario: Given a host that is not a Mac, or has no npx, when `swarm.py viewer-start <run>` runs, then it prints one line starting `viewer: unavailable` on standard error, says the swarm is unaffected, and exits 0
        """
        for platform, npx in (
            ("Linux", True), ("Darwin", False), ("Linux", False)
        ):
            with self.subTest(platform=platform, npx=npx):
                result, audit = self._cli(
                    "viewer-start", self.run, platform=platform, npx=npx
                )
                self._assert_unavailable(result)
                self._assert_no_signals(audit)
                self.assertEqual(self._invocations(), [])
                self.assertFalse((self.run / "viewer.pid").exists())

        # Invalid syntax must win over platform and dependency checks.
        for platform, npx in (
            ("Darwin", True), ("Linux", True), ("Darwin", False)
        ):
            for command in ("viewer-start", "viewer-stop"):
                invalid = [
                    (command,),
                    (command, self.run, "extra"),
                    ("--unknown-viewer-option", command, self.run),
                    (command, "--unknown-viewer-option", self.run),
                    (command, self.run, "--unknown-viewer-option"),
                    (command, self.run, "--port", "49152"),
                    (command, self.run, "--budget", "1"),
                    (command, self.run, "--help"),
                ]
                for arguments in invalid:
                    with self.subTest(
                        platform=platform, npx=npx, arguments=arguments
                    ):
                        result, audit = self._cli(
                            *arguments, platform=platform, npx=npx
                        )
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertRegex(result.stderr.lower(), r"(?m)^usage:")
                        self.assertNotIn("viewer: unavailable", result.stderr)
                        self._assert_no_signals(audit)
                        self.assertEqual(self._invocations(), [])

        # An existing viewer must not bypass the availability checks.
        viewer = self._start()
        for platform, npx in (("Linux", True), ("Darwin", False)):
            with self.subTest(existing_viewer=True, platform=platform):
                result, audit = self._cli(
                    "viewer-start", self.run, platform=platform, npx=npx
                )
                self._assert_unavailable(result)
                self._assert_no_signals(audit)
                self.assertEqual(len(self._invocations()), 1)
                self.assertIsNone(self._exit_info(viewer["pid"]))

    def test_viewer_stop_ends_the_viewer_and_is_safe_when_none_runs(self):
        """Outcome.
        Scenario: Given a viewer started by `viewer-start`, when `swarm.py viewer-stop <run>` runs, then the viewer process ends and the command exits 0, and with no viewer running it exits 0 and says so
        """
        self._stop(expected="not running")
        viewer = self._start()
        self._stop()
        self._wait(
            lambda: self._exit_info(viewer["pid"]),
            "viewer-stop reported success but left the viewer alive.",
        )
        self._stop(expected="not running")
        os.waitpid(viewer["pid"], 0)
        self._stop(expected="not running")

    def test_crashed_viewer_is_not_running_and_can_be_started_again(self):
        """Outcome.
        Scenario: Given a viewer that crashed or was left as a zombie process, when `swarm.py viewer-stop <run>` runs, then it prints `viewer: not running`, exits 0 and signals no process, and a following `swarm.py viewer-start <run>` starts a new viewer
        """
        for leave_zombie in (True, False):
            with self.subTest(leave_zombie=leave_zombie):
                run = self._new_run(
                    "crashed-zombie" if leave_zombie else "crashed-reaped"
                )
                viewer = self._start(run)
                self._crash(viewer, reap=not leave_zombie)
                self._stop(run, expected="not running")
                if leave_zombie:
                    self.assertEqual(
                        self._exit_info(viewer["pid"]).si_pid, viewer["pid"]
                    )
                replacement = self._start(run)
                self.assertNotEqual(replacement["pid"], viewer["pid"])

                # Restart must also handle stale metadata without a prior stop.
                self._crash(replacement, reap=not leave_zombie)
                restarted = self._start(run)
                self.assertNotEqual(restarted["pid"], replacement["pid"])
                self._assert_run_unchanged(run)

    def test_viewer_commands_never_change_run_state_files(self):
        """Invariant.
        Scenario: Given any swarm run, when the viewer starts, stops or crashes, then swarm.json and swarm-events.jsonl are byte for byte unchanged by it
        """
        self._stop(expected="not running", allow_absent=True)
        self._assert_run_unchanged()

        for crash in (False, True):
            with self.subTest(crash=crash):
                viewer = self._start(allow_absent=True)
                self._assert_run_unchanged()
                if viewer is not None and crash:
                    self._crash(viewer)
                    self._assert_run_unchanged()
                self._stop(
                    expected="not running" if crash else "stopped",
                    allow_absent=True,
                )
                if viewer is not None:
                    self._wait(
                        lambda: self._exit_info(viewer["pid"]),
                        "Viewer remained alive after stop.",
                    )
                self._assert_run_unchanged()

        for platform, npx in (("Linux", True), ("Darwin", False)):
            result, _ = self._cli(
                "viewer-start", self.run, platform=platform, npx=npx
            )
            if not self._accept_absent(result, "viewer-start"):
                self._assert_unavailable(result)
            self._assert_run_unchanged()

    def test_hooks_json_is_unchanged_and_no_unpinned_agent_flow_is_started(self):
        """Invariant; checkout checksum coverage is limited as documented above.
        Scenario: Changing plugins/gstack-execution/hooks/hooks.json (sha256 542f7e30d883d326d10441ed8f3a7c409e4d4720a9fac0c72f776f9d152b0092) must never happen
        Scenario: The viewer being started from any version of agent-flow-app other than 0.9.6 must never happen
        """
        viewer = self._start(allow_absent=True)
        if viewer is not None:
            result, _ = self._cli("viewer-start", self.run)
            self._assert_success(
                result, "viewer: http://127.0.0.1:%d\n" % viewer["port"]
            )
            self.assertEqual(len(self._invocations()), 1)
        self._stop(allow_absent=True)
        if viewer is not None:
            self._wait(
                lambda: self._exit_info(viewer["pid"]),
                "Viewer remained alive after stop.",
            )

        for invocation in self._invocations():
            self.assertEqual(
                invocation["argv"][:4],
                ["--yes", PINNED_PACKAGE, "--no-open", "--port"],
            )
            self.assertEqual(len(invocation["argv"]), 5)

        for row in self._audit():
            if row["event"] != "subprocess.Popen":
                continue
            argv = row["argv"]
            tokens = shlex.split(argv) if isinstance(argv, str) else argv
            for token in tokens:
                if "agent-flow-app" in str(token):
                    self.assertEqual(
                        token, PINNED_PACKAGE,
                        "An unpinned or indirect agent-flow launch was attempted.",
                    )

        self.assertEqual(
            [
                row for row in self._audit()
                if row["event"] == "protected-access"
                and row["kind"] in {"plugin-hooks", "personal-settings"}
            ],
            [],
            "Viewer commands must not mutate plugin hooks or open settings.",
        )
        self.assertEqual(self.settings.read_bytes(), SETTINGS)


if __name__ == "__main__":
    unittest.main()
