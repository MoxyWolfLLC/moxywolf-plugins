# drafted-by: gpt/gpt-6-astra
"""Black-box goal tests; the candidate is executed, never imported or inspected.

Only temporary files outside GOAL_CANDIDATE and operating-system process
information are read by these tests. Linux child-subreaper support keeps crashed
viewers unreaped so the zombie regression is exercised deterministically.

Verification limits:
* The current CLI was exercised and rejects both viewer commands with exit 2.
  This complete suite was not run during the read-only drafting session.
* Checking the checkout's hooks.json checksum requires repository-file access,
  which the test contract forbids. That protection needs the external
  allowed-path/checksum gate; the final test does not pretend to verify it.
* The fake npx verifies process launches and arguments, not the real npm
  package's network behavior. Signals delivered to an already-dead process
  cannot be observed through its output.
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
ADDRESS = re.compile(r"viewer: http://127\.0\.0\.1:([0-9]+)\n?")

STATE = b"""{
  "plan": {
    "serial": true,
    "max_workers": 1,
    "items": [],
    "order": []
  },
  "base": "1111111111111111111111111111111111111111",
  "integration_head": "1111111111111111111111111111111111111111",
  "budget": 5.0,
  "spent": 0.0,
  "reserved": {},
  "review_cap": 2,
  "items": {}
}
"""
EVENTS = (
    b'{"ts":"2026-11-22T00:00:00Z","event":"init",'
    b'"base":"1111111111111111111111111111111111111111",'
    b'"budget":5.0,"serial":true,"items":[]}\n'
)
SETTINGS = b'{"hooks":{},"permissions":{"allow":[]}}\n'

FAKE_NPX = r'''
import json
import os
import signal
import sys
import time

def record(kind, **fields):
    entry = {"kind": kind, "pid": os.getpid(), **fields}
    data = (json.dumps(entry) + "\n").encode()
    fd = os.open(
        os.environ["SWARM_TEST_NPX_LOG"],
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
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
# A final backstop if the test runner itself is killed.
deadline = time.monotonic() + 180
while time.monotonic() < deadline:
    time.sleep(0.05)
'''


class _Viewer:
    """Temporary external inputs, process observations, and deterministic cleanup."""

    def __init__(self, case):
        self.case = case
        candidate = os.environ.get("GOAL_CANDIDATE")
        if not candidate:
            raise RuntimeError("GOAL_CANDIDATE must name the candidate checkout")
        self.candidate = os.path.abspath(candidate)
        self.old_subreaper = None
        self.libc = None

    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="swarm-viewer-", dir="/tmp")
        self.root = Path(self.temp.name)
        try:
            if os.path.commonpath([self.candidate, str(self.root)]) == self.candidate:
                raise RuntimeError("The test's temporary directory must be outside the checkout")

            self.run = self.root / "run with spaces"
            self.run.mkdir()
            (self.run / "swarm.json").write_bytes(STATE)
            (self.run / "swarm-events.jsonl").write_bytes(EVENTS)

            self.home = self.root / "home"
            self.settings = self.home / ".claude" / "settings.json"
            self.settings.parent.mkdir(parents=True)
            self.settings.write_bytes(SETTINGS)

            self.bin = self.root / "bin"
            self.bin.mkdir()
            self.empty_bin = self.root / "empty-bin"
            self.empty_bin.mkdir()
            self.log = self.root / "npx.jsonl"
            npx = self.bin / "npx"
            npx.write_text(
                "#!" + sys.executable + "\n" + FAKE_NPX,
                encoding="utf-8",
            )
            npx.chmod(0o755)

            if sys.platform.startswith("linux"):
                self.libc = ctypes.CDLL(None, use_errno=True)
                previous = ctypes.c_int()
                if self.libc.prctl(37, ctypes.byref(previous), 0, 0, 0) != 0:
                    raise OSError(ctypes.get_errno(), "PR_GET_CHILD_SUBREAPER failed")
                if self.libc.prctl(36, 1, 0, 0, 0) != 0:
                    raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER failed")
                self.old_subreaper = previous.value
            return self
        except BaseException:
            self.temp.cleanup()
            raise

    def __exit__(self, exc_type, exc, traceback):
        try:
            # Re-scan briefly to catch a child still starting after a CLI failure.
            deadline = time.monotonic() + 0.4
            seen = set()
            while time.monotonic() < deadline:
                for entry in self.starts():
                    pid = entry["pid"]
                    if pid in seen:
                        continue
                    seen.add(pid)
                    if self.alive(pid):
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    try:
                        os.waitpid(pid, 0)
                    except ChildProcessError:
                        pass
                time.sleep(0.02)
        finally:
            try:
                if self.old_subreaper is not None:
                    if self.libc.prctl(36, self.old_subreaper, 0, 0, 0) != 0:
                        raise OSError(ctypes.get_errno(), "Restoring subreaper failed")
            finally:
                self.temp.cleanup()

    def environment(self, platform="Darwin", npx=True, extra=None):
        env = os.environ.copy()
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        env.update(
            HOME=str(self.home),
            CLAUDE_CONFIG_DIR=str(self.home / ".claude"),
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_CACHE_HOME=str(self.home / ".cache"),
            npm_config_cache=str(self.home / ".npm"),
            TMPDIR=str(self.root),
            PYTHONDONTWRITEBYTECODE="1",
            SWARM_TEST_NPX_LOG=str(self.log),
            PATH=(
                str(self.bin) + os.pathsep + os.defpath
                if npx else str(self.empty_bin)
            ),
        )
        if platform is None:
            env.pop("SWARM_VIEWER_PLATFORM", None)
        else:
            env["SWARM_VIEWER_PLATFORM"] = platform
        if extra:
            env.update(extra)
        return env

    def invoke(self, arguments, **environment):
        try:
            return subprocess.run(
                [sys.executable, "-B", TOOL, *map(str, arguments)],
                cwd=self.candidate,
                env=self.environment(**environment),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            self.case.fail("The viewer command did not return within 15 seconds")

    def command(self, command, **environment):
        return self.invoke([command, self.run], **environment)

    def records(self):
        if not self.log.exists():
            return []
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
            if line
        ]

    def starts(self):
        return [entry for entry in self.records() if entry["kind"] == "start"]

    def state(self, pid):
        if sys.platform.startswith("linux"):
            try:
                stat = Path("/proc") / str(pid) / "stat"
                return stat.read_text().rsplit(") ", 1)[1].split()[0]
            except FileNotFoundError:
                return None
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="],
            capture_output=True,
            text=True,
            timeout=5,
        )
        value = result.stdout.strip()
        return value[:1] or None

    def alive(self, pid):
        return self.state(pid) not in (None, "Z", "X")

    def wait(self, predicate, message, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(0.02)
        self.case.fail(message)

    def unchanged_start_count(self, count):
        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:
            self.case.assertEqual(len(self.starts()), count)
            time.sleep(0.02)

    def address(self, result):
        self.case.assertEqual(result.returncode, 0, result.stderr)
        self.case.assertEqual(result.stderr, "")
        match = ADDRESS.fullmatch(result.stdout)
        self.case.assertIsNotNone(match, repr(result.stdout))
        port = int(match.group(1))
        self.case.assertGreater(port, 0)
        self.case.assertLessEqual(port, 65535)
        return port

    def pinned(self, entry, port=None):
        argv = entry["argv"]
        self.case.assertEqual(len(argv), 5, argv)
        self.case.assertEqual(
            argv[:4],
            ["--yes", "agent-flow-app@0.9.6", "--no-open", "--port"],
        )
        self.case.assertRegex(argv[4], r"^[0-9]+$")
        actual_port = int(argv[4])
        self.case.assertGreater(actual_port, 0)
        self.case.assertLessEqual(actual_port, 65535)
        if port is not None:
            self.case.assertEqual(actual_port, port)

    def start(self, **environment):
        count = len(self.starts())
        result = self.command("viewer-start", **environment)
        port = self.address(result)
        self.wait(
            lambda: len(self.starts()) > count,
            "viewer-start reported success without executing npx",
        )
        self.unchanged_start_count(count + 1)
        entry = self.starts()[-1]
        self.pinned(entry, port)
        self.case.assertTrue(self.alive(entry["pid"]), "The viewer already exited")
        self.case.assertTrue((self.run / "viewer.pid").is_file())
        return entry, result.stdout

    def stop(self, expected):
        result = self.command("viewer-stop")
        self.case.assertEqual(result.returncode, 0, result.stderr)
        self.case.assertEqual(result.stdout, expected + "\n")
        self.case.assertEqual(result.stderr, "")
        return result

    def unavailable(self, result):
        self.case.assertEqual(result.returncode, 0, result.stderr)
        self.case.assertEqual(result.stdout, "")
        lines = result.stderr.splitlines()
        self.case.assertEqual(len(lines), 1, result.stderr)
        self.case.assertTrue(lines[0].startswith("viewer: unavailable"), result.stderr)
        self.case.assertRegex(lines[0].lower(), r"\bswarm\b.*\bunaffected\b")

    def crash(self, pid, reap):
        self.case.assertIsNotNone(
            self.old_subreaper,
            "The zombie fixture requires the specified Linux test container",
        )
        os.kill(pid, signal.SIGKILL)
        self.wait(lambda: self.state(pid) == "Z", "Viewer did not become a zombie")
        status = self.wait(
            lambda: os.waitid(
                os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT
            ),
            "The test runner did not adopt the crashed viewer",
        )
        self.case.assertEqual(status.si_pid, pid)
        if reap:
            self.case.assertEqual(os.waitpid(pid, 0)[0], pid)
            self.case.assertIsNone(self.state(pid))

    def observe_optional_start(self, result):
        # Invariants permit the baseline's unsupported command. A claimed launch,
        # however, must have a real externally recorded process.
        if result.returncode == 0 and result.stdout.startswith("viewer: http://"):
            self.wait(lambda: self.starts(), "Reported viewer never executed npx")
        time.sleep(0.1)

    def assert_state_unchanged(self):
        self.case.assertEqual((self.run / "swarm.json").read_bytes(), STATE)
        self.case.assertEqual((self.run / "swarm-events.jsonl").read_bytes(), EVENTS)


class SwarmAgentView(unittest.TestCase):
    def test_viewer_start_runs_pinned_agent_flow_locally(self):
        """Scenario: Given a Mac host with npx on the path, when `swarm.py viewer-start <run>` runs, then it starts `npx --yes agent-flow-app@0.9.6 --no-open --port <port>` in the background and prints the viewer address on standard output"""
        with _Viewer(self) as viewer:
            entry, address = viewer.start()
            again = viewer.command("viewer-start")
            viewer.address(again)
            self.assertEqual(again.stdout, address)
            viewer.unchanged_start_count(1)
            self.assertTrue(viewer.alive(entry["pid"]))

    def test_viewer_start_without_a_mac_or_npx_says_unavailable_and_exits_zero(self):
        """Scenario: Given a host that is not a Mac, or has no npx, when `swarm.py viewer-start <run>` runs, then it prints one line starting `viewer: unavailable` on standard error, says the swarm is unaffected, and exits 0"""
        with _Viewer(self) as viewer:
            for platform, npx in (("Linux", True), ("Darwin", False), ("Linux", False)):
                with self.subTest(platform=platform, npx=npx):
                    viewer.unavailable(
                        viewer.command("viewer-start", platform=platform, npx=npx)
                    )
                    viewer.unchanged_start_count(0)

            # Argument errors must precede unavailable-platform/npx handling.
            for command in ("viewer-start", "viewer-stop"):
                invalid = [
                    [command],
                    [command, viewer.run, "extra"],
                ]
                for option in ("--unknown", "--help", "-h", "--spend-stop"):
                    invalid.extend([
                        [option, command, viewer.run],
                        [command, option, viewer.run],
                        [command, viewer.run, option],
                    ])
                invalid.extend([
                    [command, "--port", "43210", viewer.run],
                    [command, viewer.run, "--port", "43210"],
                    ["--port", "43210", command, viewer.run],
                ])
                for arguments in invalid:
                    with self.subTest(arguments=arguments):
                        result = viewer.invoke(arguments, platform="Linux", npx=False)
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertTrue(
                            result.stderr.lower().startswith("usage:"),
                            result.stderr,
                        )
                        self.assertNotIn("viewer: unavailable", result.stderr)
            viewer.unchanged_start_count(0)

            # Availability also takes precedence over an existing viewer.
            entry, _ = viewer.start()
            for platform, npx in (("Linux", True), ("Darwin", False)):
                with self.subTest(existing_viewer=True, platform=platform, npx=npx):
                    viewer.unavailable(
                        viewer.command("viewer-start", platform=platform, npx=npx)
                    )
                    viewer.unchanged_start_count(1)
                    self.assertTrue(viewer.alive(entry["pid"]))

    def test_empty_platform_override_is_unavailable_not_the_real_platform(self):
        """Scenario: Given the environment variable `SWARM_VIEWER_PLATFORM` set to an empty value, on any host and with npx on the path, when `swarm.py viewer-start <run>` runs, then the empty value is the platform, so it prints one line starting `viewer: unavailable` on standard error, prints nothing on standard output, exits 0 and starts no process"""
        with _Viewer(self) as viewer:
            # Exercise the native container and a Darwin platform.system()
            # fallback. Without the latter, `override or platform.system()`
            # incorrectly passes this regression test on Linux.
            probe = viewer.root / "darwin-platform"
            probe.mkdir()
            (probe / "sitecustomize.py").write_text(
                'import platform\nplatform.system = lambda: "Darwin"\n',
                encoding="utf-8",
            )
            extra = {"PYTHONPATH": str(probe)}
            check = subprocess.run(
                [sys.executable, "-B", "-c", "import platform; print(platform.system())"],
                cwd=str(viewer.root),
                env=viewer.environment(platform="", extra=extra),
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertEqual(check.stdout, "Darwin\n")

            for environment in ({}, extra):
                with self.subTest(darwin_fallback=bool(environment)):
                    viewer.unavailable(
                        viewer.command("viewer-start", platform="", extra=environment)
                    )
                    viewer.unchanged_start_count(0)

    def test_viewer_stop_ends_the_viewer_and_is_safe_when_none_runs(self):
        """Scenario: Given a viewer started by `viewer-start`, when `swarm.py viewer-stop <run>` runs, then the viewer process ends and the command exits 0, and with no viewer running it exits 0 and says so"""
        with _Viewer(self) as viewer:
            viewer.stop("viewer: not running")
            entry, _ = viewer.start()
            viewer.stop("viewer: stopped")
            viewer.wait(
                lambda: not viewer.alive(entry["pid"]),
                "viewer-stop left the viewer running",
            )
            signals = [r for r in viewer.records() if r["kind"] == "signal"]
            viewer.stop("viewer: not running")
            self.assertEqual(
                [r for r in viewer.records() if r["kind"] == "signal"],
                signals,
            )
            viewer.unchanged_start_count(1)

    def test_crashed_viewer_is_not_running_and_can_be_started_again(self):
        """Scenario: Given a viewer that crashed or was left as a zombie process, when `swarm.py viewer-stop <run>` runs, then it prints `viewer: not running`, exits 0 and signals no process, and a following `swarm.py viewer-start <run>` starts a new viewer"""
        with _Viewer(self) as viewer:
            for reap in (False, True):
                with self.subTest(reaped=reap):
                    crashed, _ = viewer.start()
                    pid = crashed["pid"]
                    viewer.crash(pid, reap=reap)
                    before = viewer.records()
                    viewer.stop("viewer: not running")
                    self.assertEqual(viewer.records(), before)
                    if not reap:
                        self.assertEqual(viewer.state(pid), "Z")

                    replacement, _ = viewer.start()
                    if not reap:
                        self.assertNotEqual(replacement["pid"], pid)
                        self.assertEqual(viewer.state(pid), "Z")
                        self.assertEqual(os.waitpid(pid, 0)[0], pid)

                    viewer.stop("viewer: stopped")
                    viewer.wait(
                        lambda: not viewer.alive(replacement["pid"]),
                        "Replacement viewer survived viewer-stop",
                    )

            # Also restart directly after a crash, without an intervening stop.
            crashed, _ = viewer.start()
            viewer.crash(crashed["pid"], reap=False)
            replacement, _ = viewer.start()
            self.assertNotEqual(replacement["pid"], crashed["pid"])
            self.assertEqual(viewer.state(crashed["pid"]), "Z")
            self.assertEqual(os.waitpid(crashed["pid"], 0)[0], crashed["pid"])

    def test_viewer_commands_never_change_run_state_files(self):
        """Scenario: Given any swarm run, when the viewer starts, stops or crashes, then swarm.json and swarm-events.jsonl are byte for byte unchanged by it"""
        with _Viewer(self) as viewer:
            viewer.command("viewer-stop")
            viewer.assert_state_unchanged()

            result = viewer.command("viewer-start")
            viewer.observe_optional_start(result)
            viewer.assert_state_unchanged()

            viewer.command("viewer-start")
            viewer.assert_state_unchanged()
            viewer.command("viewer-stop")
            viewer.assert_state_unchanged()

            result = viewer.command("viewer-start")
            viewer.observe_optional_start(result)
            viewer.assert_state_unchanged()
            for entry in viewer.starts():
                if viewer.alive(entry["pid"]):
                    viewer.crash(entry["pid"], reap=False)
                    viewer.assert_state_unchanged()

            viewer.command("viewer-stop")
            viewer.assert_state_unchanged()
            result = viewer.command("viewer-start")
            viewer.observe_optional_start(result)
            viewer.assert_state_unchanged()
            viewer.command("viewer-stop")
            viewer.assert_state_unchanged()

            for platform, npx in (("Linux", True), ("Darwin", False), ("", True)):
                viewer.command("viewer-start", platform=platform, npx=npx)
                viewer.assert_state_unchanged()

    def test_hooks_json_is_unchanged_and_no_unpinned_agent_flow_is_started(self):
        """Scenario: The viewer being started from any version of agent-flow-app other than 0.9.6 must never happen
        Scenario: Changing plugins/gstack-execution/hooks/hooks.json (sha256 542f7e30d883d326d10441ed8f3a7c409e4d4720a9fac0c72f776f9d152b0092) must never happen

        The checkout checksum is unverified here: reading that file is forbidden.
        This test checks observable launches and the external personal settings;
        checkout protection must be enforced by the repository's external gate.
        """
        with _Viewer(self) as viewer:
            for command in ("viewer-start", "viewer-start", "viewer-stop", "viewer-stop"):
                result = viewer.command(command)
                viewer.observe_optional_start(result)
                self.assertEqual(viewer.settings.read_bytes(), SETTINGS)
                for entry in viewer.starts():
                    viewer.pinned(entry)

            for platform, npx in (("Linux", True), ("Darwin", False), ("", True)):
                result = viewer.command("viewer-start", platform=platform, npx=npx)
                viewer.observe_optional_start(result)
                self.assertEqual(viewer.settings.read_bytes(), SETTINGS)
                for entry in viewer.starts():
                    viewer.pinned(entry)


if __name__ == "__main__":
    unittest.main()
