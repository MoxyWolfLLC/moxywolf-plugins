#!/usr/bin/env python3
"""XE-026: jev_route's selftest examines something on every machine.

The default selftest must run with no key and no network, so its result can't
depend on the caller's machine. The live check must never pass over nothing.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jev_route  # noqa: E402


class OfflineSelftest(unittest.TestCase):
    def test_passes_with_a_bogus_key_a_dead_endpoint_and_no_curl(self):
        empty = tempfile.mkdtemp()
        env = dict(os.environ, AI_GATEWAY_API_KEY="vck_bogus",
                   JEV_ENDPOINT="http://127.0.0.1:9", PATH=empty, HOME=empty)
        # Precondition: the staged environment really has no curl, so any live
        # call would fail. A test that can't stage that is a setup error.
        self.assertIsNone(shutil.which("curl", path=env["PATH"]),
                          "setup: curl still resolves on the staged PATH")
        r = subprocess.run([sys.executable, str(HERE / "jev_route.py"), "--selftest"],
                           env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"\n([1-9]\d*)/\1 offline cases")

    def test_never_loads_a_key_or_reaches_the_real_ask(self):
        # The subprocess test above catches transport use, but a bogus key
        # resolves like a real one, so it can't see a key load (review F1).
        # Here both the key loader and the real _ask raise if touched.
        def touched(*_, **__):
            raise AssertionError("offline selftest touched the key or the gateway")
        saved = jev_route.load_gateway_key, jev_route._ask
        jev_route.load_gateway_key, jev_route._ask = touched, touched
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                rc = jev_route.selftest_offline()
        finally:
            jev_route.load_gateway_key, jev_route._ask = saved
        self.assertEqual(rc, 0, out.getvalue())


class LiveSelftest(unittest.TestCase):
    def _run(self, **patches):
        saved = {k: getattr(jev_route, k) for k in patches}
        for k, v in patches.items():
            setattr(jev_route, k, v)
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                return jev_route.selftest_live(), out.getvalue()
        finally:
            for k, v in saved.items():
                setattr(jev_route, k, v)

    def test_no_key_is_skipped_not_passed(self):
        def no_key(**_):
            raise jev_route.JevUnavailable("no key")
        rc, out = self._run(load_gateway_key=no_key)
        self.assertEqual(rc, 3, out)
        self.assertIn("SKIPPED", out)

    def test_gateway_failure_exits_2(self):
        def down(*_):
            raise jev_route.JevUnavailable("503")
        rc, out = self._run(load_gateway_key=lambda **_: ("k", "test"), _ask=down)
        self.assertEqual(rc, 2, out)
        self.assertIn("gateway failed", out)


if __name__ == "__main__":
    unittest.main()
