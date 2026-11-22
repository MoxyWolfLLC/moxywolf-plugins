"""Black-box holdout checks for the viewer command contract.

All candidate execution uses GOAL_CANDIDATE as its working directory.
Fixtures, process observations, and state assertions live outside that checkout.
Repository documentation, version changes, protected paths, and the real npm
package's networking require separate verification. This draft was not executed.
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
"""


class Holdout(unittest.TestCase):
    def setUp(self):
        self.candidate = os.environ["GOAL_CANDIDATE"]
        temporary = tempfile.TemporaryDirectory(prefix="viewer-holdout-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "run with spaces"
        self.bin = self.root / "bin"
        self.empty_bin = self.root / "empty-bin"
        self.home = self.root / "home"
        self.tmp = self.root / "tmp"

        for directory in (self.bin, self.empty_bin, self.home, self.tmp):
            directory.mkdir()

        claude = self.home / ".claude"
        claude.mkdir()
        self.settings = claude / "settings.json"
        self.settings.write_bytes(
            b'{\n  "hooks": {}, "holdout_sentinel": "preserve"\n}\n'
        )
        self.settings_before = self._fingerprint(self.settings)

        fifo = self.root / "lifetime.fifo"
        os.mkfifo(fifo)
        self.lifetime = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
        self.addCleanup(os.close, self.lifetime)
        self.addCleanup(self._cleanup_viewer)

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
            "# Viewer fixture\n\n1. Exercise the optional viewer.\n",
            encoding="utf-8",
        )
        self.state_before = None
        result = self._command(
            "init",
            "--goal", str(goal),
            "--base", "a" * 40,
            "--budget", "5",
            "--review-cap", "2",
        )
        self.assertEqual(result.returncode, 0, self._diagnostic(result))
        self.state_before = self._state()

    @staticmethod
    def _fingerprint(path):
        contents = path.read_bytes()
        stat = path.stat()
        return contents, stat.st_mtime_ns, stat.st_ctime_ns

    def _state(self):
        return {
            name: self._fingerprint(self.run / name)
            for name in ("swarm.json", "swarm-events.jsonl")
        }

    def _assert_preserved(self):
        self.assertEqual(
            self._fingerprint(self.settings),
            self.settings_before,
            "The personal settings file was modified",
        )
        if self.state_before is not None:
            self.assertEqual(
                self._state(),
                self.state_before,
                "Viewer activity modified or rewrote swarm state",
            )

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
            timeout=15,
        )
        self._assert_preserved()
        return result

    @staticmethod
    def _diagnostic(result):
        return (
            f"exit={result.returncode}; "
            f"stdout={result.stdout!r}; stderr={result.stderr!r}"
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

    def _cleanup_viewer(self):
        (self.root / "cleanup").touch()
        deadline = time.monotonic() + 1
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

    def _assert_reply(self, result, message):
        self.assertEqual(result.returncode, 0, self._diagnostic(result))
        self.assertEqual(result.stdout, message + "\n", self._diagnostic(result))

    def _start(self):
        before = {record["pid"] for record in self._records()}
        result = self._command("viewer-start")
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
            "viewer-start printed an address without executing npx",
        )
        records = [
            record for record in self._records() if record["pid"] not in before
        ]
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(
            record["argv"],
            [
                "--yes",
                "agent-flow-app@0.9.6",
                "--no-open",
                "--port",
                str(port),
            ],
            "Launch must use the pinned package and pass no host/bind option",
        )
        self.assertTrue(self._alive(), "The background viewer already exited")

        pid_file = self.run / "viewer.pid"
        self.assertTrue(pid_file.is_file(), "Missing viewer.pid in the run folder")
        self.assertRegex(
            pid_file.read_text(encoding="utf-8"),
            rf"(?<!\d){record['pid']}(?!\d)",
        )
        self._assert_preserved()
        return record

    def test_unavailable_is_one_stderr_line_and_never_launches(self):
        for platform, npx in (
            ("Linux", True),
            ("FreeBSD", True),
            ("Windows", True),
            ("Darwin", False),
            ("Linux", False),
        ):
            with self.subTest(platform=platform, npx=npx):
                result = self._command(
                    "viewer-start", platform=platform, npx=npx
                )
                self.assertEqual(result.returncode, 0, self._diagnostic(result))
                self.assertEqual(result.stdout, "", self._diagnostic(result))
                lines = result.stderr.splitlines()
                self.assertEqual(len(lines), 1, self._diagnostic(result))
                self.assertTrue(lines[0].startswith("viewer: unavailable"))
                self.assertRegex(
                    lines[0].lower(), r"\bswarm (?:is )?unaffected\b"
                )
                time.sleep(0.1)
                self.assertEqual(self._records(), [])
                self.assertFalse(self._alive())
                self._assert_preserved()

    def test_unknown_options_are_usage_errors_before_any_side_effect(self):
        for running in (False, True):
            if running:
                self._start()
            records_before = self._records()
            pid_file = self.run / "viewer.pid"
            pid_before = pid_file.read_bytes() if pid_file.exists() else None

            for command in ("viewer-start", "viewer-stop"):
                for platform, npx in (
                    ("Darwin", True),
                    ("Linux", True),
                    ("Darwin", False),
                ):
                    with self.subTest(
                        running=running,
                        command=command,
                        platform=platform,
                        npx=npx,
                    ):
                        result = self._command(
                            command,
                            "--holdout-unknown-option",
                            platform=platform,
                            npx=npx,
                        )
                        self.assertEqual(
                            result.returncode, 2, self._diagnostic(result)
                        )
                        self.assertEqual(result.stdout, "")
                        self.assertRegex(result.stderr.lower(), r"(?m)^usage:")
                        time.sleep(0.1)
                        self.assertEqual(self._records(), records_before)
                        self.assertEqual(self._alive(), running)
                        self.assertEqual(
                            pid_file.read_bytes() if pid_file.exists() else None,
                            pid_before,
                            "Invalid arguments changed viewer ownership",
                        )
                        self._assert_preserved()

    def test_stop_works_after_platform_or_npx_availability_changes(self):
        for platform, npx in (("Linux", True), ("Darwin", False)):
            with self.subTest(platform=platform, npx=npx):
                result = self._command(
                    "viewer-stop", platform=platform, npx=npx
                )
                self._assert_reply(result, "viewer: not running")

                self._start()
                records_before = self._records()
                result = self._command(
                    "viewer-stop", platform=platform, npx=npx
                )
                self._assert_reply(result, "viewer: stopped")
                self._wait(
                    lambda: not self._alive(),
                    "viewer-stop reported success but left the viewer running",
                )

                result = self._command(
                    "viewer-stop", platform=platform, npx=npx
                )
                self._assert_reply(result, "viewer: not running")
                self.assertEqual(self._records(), records_before)
                self.assertFalse(self._alive())
                self._assert_preserved()

    def test_crashed_viewer_is_not_running_and_can_be_started_again(self):
        self._start()
        (self.root / "crash").touch()
        self._wait(lambda: not self._alive(), "Fake viewer failed to exit")
        self._assert_preserved()

        records_before = self._records()
        result = self._command("viewer-stop")
        self._assert_reply(result, "viewer: not running")
        self.assertEqual(self._records(), records_before)
        self.assertFalse(self._alive())

        (self.root / "crash").unlink()
        self._start()
        self.assertEqual(len(self._records()), len(records_before) + 1)
        result = self._command("viewer-stop")
        self._assert_reply(result, "viewer: stopped")
        self._wait(lambda: not self._alive(), "Restarted viewer did not stop")
        self._assert_preserved()


if __name__ == "__main__":
    unittest.main()
