# drafted-by: gpt/gpt-6-astra
"""Black-box swarm viewer tests using an executable fake npx.

Only subprocess output, exit codes, and files outside GOAL_CANDIDATE are
examined. A FIFO held open by fake npx makes process termination observable
without confusing an exited, unreaped process with a running viewer.

Coverage limitation: hooks.json's required SHA-256,
542f7e30d883d326d10441ed8f3a7c409e4d4720a9fac0c72f776f9d152b0092,
cannot be verified under the prohibition on reading checkout files. The
specified final test name is retained, but its assertions cover launch
arguments and the temporary personal settings only. Repository policy must
separately enforce the hooks checksum.

These tests verify the launcher contract, not the real npm package's bind
address, network behavior, or usability. The draft suite was not executed
in the read-only drafting environment.
"""

import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SWARM = "plugins/gstack-execution/scripts/swarm.py"

FAKE_NPX = r"""
import json
import os
from pathlib import Path
import sys
import time

root = Path(os.environ["VIEWER_TEST_ROOT"])
if (root / "cleanup").exists():
    sys.exit(0)

# Keep this descriptor open until the process actually exits.
lifetime = os.open(root / "lifetime.fifo", os.O_WRONLY | os.O_NONBLOCK)
os.write(lifetime, b"started\n")

record = {"pid": os.getpid(), "argv": sys.argv[1:]}
temporary = root / ("invocation-%s.tmp" % os.getpid())
temporary.write_text(json.dumps(record), encoding="utf-8")
temporary.replace(root / ("invocation-%s.json" % os.getpid()))

deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    if (root / "cleanup").exists():
        sys.exit(0)
    if (root / "crash").exists():
        os._exit(37)
    time.sleep(0.02)
sys.exit(0)
"""


class SwarmAgentView(unittest.TestCase):
    def setUp(self):
        self.candidate = os.environ["GOAL_CANDIDATE"]
        temporary = tempfile.TemporaryDirectory(prefix="swarm-viewer-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "run"
        self.bin = self.root / "bin"
        self.empty_bin = self.root / "empty-bin"
        self.home = self.root / "home"
        self.tmp = self.root / "tmp"
        for directory in (self.bin, self.empty_bin, self.home, self.tmp):
            directory.mkdir()

        claude = self.home / ".claude"
        claude.mkdir()
        self.settings = claude / "settings.json"
        self.original_settings = b'{\n  "hooks": {}, "test_sentinel": "keep"\n}\n'
        self.settings.write_bytes(self.original_settings)

        fifo = self.root / "lifetime.fifo"
        os.mkfifo(fifo)
        self.lifetime = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
        self.addCleanup(os.close, self.lifetime)
        self.addCleanup(self._cleanup_viewers)

        fake = self.root / "fake_npx.py"
        fake.write_text(FAKE_NPX, encoding="utf-8")
        executable = self.bin / "npx"
        executable.write_text(
            "#!/bin/sh\nexec "
            + shlex.quote(sys.executable)
            + " -B "
            + shlex.quote(str(fake))
            + ' "$@"\n',
            encoding="utf-8",
        )
        executable.chmod(0o755)

        self.env = {
            "PATH": str(self.bin),
            "HOME": str(self.home),
            "TMPDIR": str(self.tmp),
            "CLAUDE_CONFIG_DIR": str(claude),
            "PYTHONDONTWRITEBYTECODE": "1",
            "SWARM_VIEWER_PLATFORM": "Darwin",
            "VIEWER_TEST_ROOT": str(self.root),
            "LC_ALL": "C",
        }

        goal = self.root / "goal"
        goal.mkdir()
        (goal / "PLAN.md").write_text(
            "# Viewer test fixture\n\n1. Exercise the optional viewer.\n",
            encoding="utf-8",
        )
        result = self._command(
            "init",
            "--goal", str(goal),
            "--base", "a" * 40,
            "--budget", "5",
            "--review-cap", "2",
        )
        self.assertEqual(result.returncode, 0, self._diagnostic(result))
        self.original_state = self._state_bytes()

    def _command(self, command, *arguments, platform="Darwin", npx=True):
        environment = dict(self.env)
        environment["SWARM_VIEWER_PLATFORM"] = platform
        environment["PATH"] = str(self.bin if npx else self.empty_bin)
        result = subprocess.run(
            [sys.executable, "-B", SWARM, command, str(self.run), *arguments],
            cwd=self.candidate,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(self.settings.read_bytes(), self.original_settings)
        return result

    @staticmethod
    def _diagnostic(result):
        return (
            f"exit={result.returncode}\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )

    def _records(self):
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("invocation-*.json"))
        ]

    def _alive(self):
        try:
            return bool(os.read(self.lifetime, 4096))
        except BlockingIOError:
            return True

    def _wait(self, predicate, message, timeout=4):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        self.fail(message)

    def _cleanup_viewers(self):
        (self.root / "cleanup").touch()
        deadline = time.monotonic() + 0.5
        while self._alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        if self._alive():
            for record in self._records():
                try:
                    os.kill(record["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + 1
            while self._alive() and time.monotonic() < deadline:
                time.sleep(0.02)

    def _state_bytes(self):
        return {
            name: (self.run / name).read_bytes()
            for name in ("swarm.json", "swarm-events.jsonl")
        }

    def _assert_state_unchanged(self):
        self.assertEqual(self._state_bytes(), self.original_state)

    def _accept_present_or_originally_absent(self, result, command):
        if (
            result.returncode == 2
            and result.stdout == ""
            and result.stderr == f"swarm: unknown command {command}\n"
        ):
            return False
        self.assertEqual(result.returncode, 0, self._diagnostic(result))
        return True

    def _assert_pinned(self, record, port=None):
        arguments = record["argv"]
        self.assertEqual(
            arguments[:-1],
            ["--yes", "agent-flow-app@0.9.6", "--no-open", "--port"],
        )
        self.assertRegex(arguments[-1], r"^[0-9]+$")
        self.assertTrue(1 <= int(arguments[-1]) <= 65535)
        if port is not None:
            self.assertEqual(int(arguments[-1]), port)

    def _start(self, allow_absent=False):
        before = {record["pid"] for record in self._records()}
        result = self._command("viewer-start")
        if allow_absent:
            if not self._accept_present_or_originally_absent(
                result, "viewer-start"
            ):
                return None
        else:
            self.assertEqual(result.returncode, 0, self._diagnostic(result))

        address = re.fullmatch(
            r"viewer: http://127\.0\.0\.1:([0-9]+)\n?", result.stdout
        )
        self.assertIsNotNone(address, self._diagnostic(result))
        port = int(address.group(1))
        self.assertTrue(1 <= port <= 65535)

        self._wait(
            lambda: any(
                record["pid"] not in before for record in self._records()
            ),
            "viewer-start did not execute fake npx",
        )
        new_records = [
            record for record in self._records() if record["pid"] not in before
        ]
        self.assertEqual(len(new_records), 1)
        record = new_records[0]
        self._assert_pinned(record, port)
        self.assertTrue(self._alive(), "viewer exited instead of staying running")

        pid_file = self.run / "viewer.pid"
        self.assertTrue(pid_file.is_file(), "viewer.pid was not created")
        self.assertRegex(
            pid_file.read_text(encoding="utf-8"),
            rf"(?<!\d){record['pid']}(?!\d)",
        )
        return record

    def test_viewer_start_runs_pinned_agent_flow_locally(self):
        """Outcome.
        Scenario: Given a Mac host with npx on the path, when `swarm.py viewer-start <run>` runs, then it starts `npx --yes agent-flow-app@0.9.6 --no-open --port <port>` in the background and prints the viewer address on standard output
        """
        self._start()
        before = self._records()
        for command in ("viewer-start", "viewer-stop"):
            with self.subTest(unknown_option=command):
                result = self._command(
                    command, "--definitely-unknown-viewer-option"
                )
                self.assertEqual(result.returncode, 2, self._diagnostic(result))
                self.assertEqual(result.stdout, "")
                self.assertRegex(result.stderr.lower(), r"(?m)^usage:")
                self.assertEqual(self._records(), before)
                self.assertTrue(self._alive())

    def test_viewer_start_without_a_mac_or_npx_says_unavailable_and_exits_zero(self):
        """Outcome.
        Scenario: Given a host that is not a Mac, or has no npx, when `swarm.py viewer-start <run>` runs, then it prints one line starting `viewer: unavailable` on standard error, says the swarm is unaffected, and exits 0
        """
        for platform, npx in (("Linux", True), ("Darwin", False)):
            with self.subTest(platform=platform, npx=npx):
                result = self._command(
                    "viewer-start", platform=platform, npx=npx
                )
                self.assertEqual(result.returncode, 0, self._diagnostic(result))
                self.assertEqual(result.stdout, "")
                lines = result.stderr.splitlines()
                self.assertEqual(len(lines), 1, self._diagnostic(result))
                self.assertTrue(lines[0].startswith("viewer: unavailable"))
                self.assertRegex(
                    lines[0].lower(), r"\bswarm (?:is )?unaffected\b"
                )
                time.sleep(0.1)
                self.assertEqual(self._records(), [])
                self.assertFalse(self._alive())
                self._assert_state_unchanged()

    def test_viewer_stop_ends_the_viewer_and_is_safe_when_none_runs(self):
        """Outcome.
        Scenario: Given a viewer started by `viewer-start`, when `swarm.py viewer-stop <run>` runs, then the viewer process ends and the command exits 0, and with no viewer running it exits 0 and says so
        """
        result = self._command("viewer-stop")
        self.assertEqual(result.returncode, 0, self._diagnostic(result))
        self.assertEqual(result.stdout, "viewer: not running\n")

        self._start()
        result = self._command("viewer-stop")
        self.assertEqual(result.returncode, 0, self._diagnostic(result))
        self.assertEqual(result.stdout, "viewer: stopped\n")
        self._wait(lambda: not self._alive(), "viewer-stop left npx running")

        result = self._command("viewer-stop")
        self.assertEqual(result.returncode, 0, self._diagnostic(result))
        self.assertEqual(result.stdout, "viewer: not running\n")
        self.assertFalse(self._alive())

    def test_viewer_commands_never_change_run_state_files(self):
        """Invariant.
        Scenario: Given any swarm run, when the viewer starts, stops or crashes, then swarm.json and swarm-events.jsonl are byte for byte unchanged by it
        """
        for crash in (False, True):
            with self.subTest(crash=crash):
                record = self._start(allow_absent=True)
                self._assert_state_unchanged()

                if crash and record is not None:
                    (self.root / "crash").touch()
                    self._wait(
                        lambda: not self._alive(), "fake viewer did not crash"
                    )
                    self._assert_state_unchanged()

                result = self._command("viewer-stop")
                self._accept_present_or_originally_absent(result, "viewer-stop")
                if record is not None:
                    self._wait(
                        lambda: not self._alive(), "viewer remained running"
                    )
                self._assert_state_unchanged()

                if crash:
                    (self.root / "crash").unlink(missing_ok=True)

        for platform, npx in (("Linux", True), ("Darwin", False)):
            with self.subTest(platform=platform, npx=npx):
                result = self._command(
                    "viewer-start", platform=platform, npx=npx
                )
                self._accept_present_or_originally_absent(result, "viewer-start")
                self._assert_state_unchanged()

    def test_hooks_json_is_unchanged_and_no_unpinned_agent_flow_is_started(self):
        """Invariant, with the hooks-checksum coverage gap documented above.
        Scenario: The viewer being started from any version of agent-flow-app other than 0.9.6 must never happen
        """
        self._start(allow_absent=True)
        result = self._command("viewer-stop")
        self._accept_present_or_originally_absent(result, "viewer-stop")
        self._wait(lambda: not self._alive(), "viewer remained running")

        for record in self._records():
            self._assert_pinned(record)
        self.assertEqual(self.settings.read_bytes(), self.original_settings)


if __name__ == "__main__":
    unittest.main()
