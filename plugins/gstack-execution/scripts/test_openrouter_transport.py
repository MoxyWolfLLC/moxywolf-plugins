#!/usr/bin/env python3
"""XE-013: the openrouter transport, and what a reviewer that opens nothing is allowed to claim.

Everything here runs against a stub HTTP server on localhost. No provider is called and no credit
is spent: the live round is criterion 10's separate evidence, run once by hand and recorded, because
a suite that spends money on every CI run is a suite somebody turns off.

ponytail: one stub server, a dict of canned responses, no mocking framework.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import peer_review as pr

NEXT = {"status": 200, "body": {}}
SEEN = {}


class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        SEEN.clear()
        SEEN.update(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        SEEN["_auth"] = self.headers.get("Authorization")
        self.send_response(NEXT["status"])
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(NEXT["body"]).encode())

    def log_message(self, *a):
        pass


def ok(content, model="deepseek/deepseek-v4.1-flash", finish="stop", usage=None):
    return {"model": model, "usage": usage or {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
            "choices": [{"finish_reason": finish, "message": {"content": content}}]}


class OpenRouterTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tmp = Path(tempfile.mkdtemp())
        (cls.tmp / "key.env").write_text('OPENROUTER_API_KEY="sk-test-not-a-real-key"\n')
        os.environ["GSTACK_OPENROUTER_URL"] = f"http://127.0.0.1:{cls.srv.server_port}/v1/chat/completions"
        os.environ["GSTACK_OPENROUTER_ENV"] = str(cls.tmp / "key.env")
        pr.OPENROUTER_URL = os.environ["GSTACK_OPENROUTER_URL"]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def surface(self):
        d = Path(tempfile.mkdtemp(dir=self.tmp))
        (d / "CHANGE.diff").write_text("--- a/x\n+++ b/x\n+one line\n")
        (d / "changed").mkdir(); (d / "changed" / "x.py").write_text("print('changed')\n")
        (d / "callers").mkdir(); (d / "callers" / "y.py").write_text("import x\n")
        (d / "NOTES.md").write_text("not in sends\n")     # must not be sent
        return d

    # --- criterion 2 -------------------------------------------------------------------
    def test_an_entry_named_for_its_transport_is_refused_at_import(self):
        """Not at run time. A table that accepts it has already lost the distinction."""
        doctored = self.tmp / "doctored.py"
        src = Path(pr.__file__).read_text().replace(
            '    "openrouter-gpt": {"family": "gpt", "transport": "openrouter"',
            '    "openrouter": {"family": "gpt", "transport": "openrouter"', 1)
        doctored.write_text(src)
        r = subprocess.run([sys.executable, "-c", f"import importlib.util as u;"
                            f"s=u.spec_from_file_location('d',r'{doctored}');m=u.module_from_spec(s);s.loader.exec_module(m)"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0, "an entry named for a transport must refuse to load")
        self.assertIn("named for a transport", r.stderr)

    def test_every_entry_declares_a_known_transport_and_a_family(self):
        self.assertGreaterEqual(len(pr.REVIEWERS), 4, "table looks empty; this check examined almost nothing")
        for name, cfg in pr.REVIEWERS.items():
            with self.subTest(entry=name):
                self.assertIn(cfg["transport"], pr.TRANSPORTS)
                self.assertNotIn(name, pr.TRANSPORTS)
                self.assertTrue(cfg["family"])

    # --- criterion 3 -------------------------------------------------------------------
    def test_headroom_is_enforced_on_the_api_and_declared_only_on_the_clis(self):
        for t in ("codex", "claude", "gemini"):
            self.assertFalse(pr.headroom_enforced(t), f"{t} exposes no flag, so its headroom is declared only")
        for t in ("openrouter-gpt", "openrouter-deepseek"):
            self.assertTrue(pr.headroom_enforced(t))

    def test_max_tokens_is_actually_on_the_request(self):
        NEXT.update(status=200, body=ok('{"ok":true}'))
        pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(SEEN["max_tokens"], pr.REVIEWERS["openrouter-deepseek"]["max_output"])

    # --- criterion 4 -------------------------------------------------------------------
    def test_usage_arrives_in_one_shape_from_the_provider(self):
        NEXT.update(status=200, body=ok('{"ok":true}', usage={"prompt_tokens": 100, "completion_tokens": 20,
                                                              "total_tokens": 120,
                                                              "prompt_tokens_details": {"cached_tokens": 7}}))
        pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(pr.LAST_REVIEWER_USAGE,
                         {"input": 100, "output": 20, "cache_read": 7, "total": 120, "source": "openrouter usage"})

    # --- criterion 5 -------------------------------------------------------------------
    def test_the_surface_is_sent_and_every_file_is_accounted_for(self):
        NEXT.update(status=200, body=ok('{"ok":true}'))
        pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        content = SEEN["messages"][0]["content"]
        for rel in ("CHANGE.diff", "changed/x.py", "callers/y.py"):
            self.assertIn(f"=== {rel} ===", content, f"{rel} is in sends and must be sent")
        self.assertNotIn("NOTES.md", content, "a file outside sends must not be sent")
        paths = {f["path"] for f in pr.LAST_SENT_SURFACE}
        self.assertEqual(paths, {"CHANGE.diff", "changed/x.py", "callers/y.py"})
        self.assertTrue(all(f["sent"] for f in pr.LAST_SENT_SURFACE))

    def test_a_surface_over_the_cap_declares_the_tail_unsent_rather_than_dropping_it(self):
        d = self.surface()
        (d / "changed" / "big.py").write_text("x" * (pr.API_SURFACE_CAP + 10))
        NEXT.update(status=200, body=ok('{"ok":true}'))
        pr.run_openrouter("openrouter-deepseek", "p", d, 30, {"type": "object"})
        unsent = [f for f in pr.LAST_SENT_SURFACE if not f["sent"]]
        self.assertTrue(unsent, "the oversized file must be recorded as unsent, not silently omitted")
        self.assertIn("cap", unsent[0]["why"])

    # --- criterion 9, and XE-005.5 -----------------------------------------------------
    def test_a_ceiling_hit_and_a_broken_reviewer_are_different_outcomes(self):
        NEXT.update(status=200, body=ok("partial", finish="length"))
        with self.assertRaises(pr.ReviewError) as e:
            pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(e.exception.outcome, "output_truncated")

        NEXT.update(status=200, body=ok("   ", finish="stop"))
        with self.assertRaises(pr.ReviewError) as e:
            pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(e.exception.outcome, "malformed_output")

    def test_a_served_model_below_the_floor_is_refused_after_the_call(self):
        NEXT.update(status=200, body=ok('{"ok":true}', model="deepseek/deepseek-v2-lite"))
        with self.assertRaises(pr.ReviewError) as e:
            pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(e.exception.outcome, "model_below_floor")

    def test_a_provider_prefix_does_not_defeat_the_floor(self):
        self.assertTrue(pr.model_ok("openrouter-gpt", "openai/gpt-6-astra"))
        self.assertFalse(pr.model_ok("openrouter-gpt", "openai/gpt-4o"))
        self.assertTrue(pr.model_ok("codex", "gpt-6-astra"), "the cli entries keep working unchanged")

    # --- criterion 8 -------------------------------------------------------------------
    def test_a_missing_credential_names_the_file_it_looked_for(self):
        missing = str(self.tmp / "nope.env")
        old = os.environ["GSTACK_OPENROUTER_ENV"]
        try:
            os.environ["GSTACK_OPENROUTER_ENV"] = missing
            with self.assertRaises(pr.ReviewError) as e:
                pr.openrouter_key()
            self.assertEqual(e.exception.outcome, "review_unavailable")
            self.assertIn(missing, e.exception.detail)

            del os.environ["GSTACK_OPENROUTER_ENV"]
            with self.assertRaises(pr.ReviewError) as e:
                pr.openrouter_key()
            self.assertIn("GSTACK_OPENROUTER_ENV", e.exception.detail)
        finally:
            os.environ["GSTACK_OPENROUTER_ENV"] = old

    def test_the_key_is_sent_and_never_comes_from_an_argument(self):
        NEXT.update(status=200, body=ok('{"ok":true}'))
        pr.run_openrouter("openrouter-deepseek", "p", self.surface(), 30, {"type": "object"})
        self.assertEqual(SEEN["_auth"], "Bearer sk-test-not-a-real-key")

    # --- criteria 1 and 7 --------------------------------------------------------------
    def test_a_forced_reviewer_of_the_builders_family_is_refused(self):
        with self.assertRaises(pr.ReviewError) as e:
            pr.choose_reviewer("claude", forced="openrouter-claude")
        self.assertEqual(e.exception.outcome, "reviewer_not_independent")

    def test_the_api_entry_is_the_fallback_when_no_cli_is_installed(self):
        """The 21 September failure: codex absent, and the checkpoint had nowhere independent to go."""
        real = pr.shutil.which
        pr.shutil.which = lambda _n: None
        try:
            tool, is_fallback = pr.choose_reviewer("claude")
            self.assertEqual(pr.REVIEWERS[tool]["transport"], "openrouter")
            self.assertNotEqual(pr.family(tool), pr.family("claude"), "a fallback still has to be independent")
            self.assertTrue(is_fallback, "an unrecorded fallback is a silent downgrade")
        finally:
            pr.shutil.which = real

    def test_a_cli_reviewer_is_still_preferred_when_one_is_installed(self):
        real = pr.shutil.which
        pr.shutil.which = lambda n: "/usr/bin/" + n if n == "codex" else None
        try:
            tool, is_fallback = pr.choose_reviewer("claude")
            self.assertEqual(tool, "codex")
            self.assertFalse(is_fallback)
        finally:
            pr.shutil.which = real

class DataUseBindsTheToolThatRuns(unittest.TestCase):
    """XE-013 defect found by using it: the data_use gate ran against the reviewer recorded at
    `open`, while `round` resolved a different one afterwards and sent the surface to that.

    Two failures, one cause. A grant naming the entry that would actually run was refused, so the
    round the grant authorized could not be opened. And a grant for an absent `codex` PASSED, after
    which the fallback sent the source to whichever entry it reached, which the owner never named.
    `cmd_round` now resolves the reviewer first and gates on the tool that receives the surface.
    """

    def setUp(self):
        self._which, self._key = pr.shutil.which, pr.openrouter_key
        pr.shutil.which = lambda _n: None            # no CLI reviewer on this host
        pr.openrouter_key = lambda: "sk-test"        # the api entries can run
        self.resolved, _ = pr.choose_reviewer("claude")

    def tearDown(self):
        pr.shutil.which, pr.openrouter_key = self._which, self._key

    @staticmethod
    def grant(*tools):
        return {"release_owner": "o",
                "data_use": {"owner": "o", "classification": "internal", "allow_repository": True,
                             "allow_history": True, "allowed_tools": list(tools)}}

    def test_the_resolved_reviewer_differs_from_the_one_open_would_record(self):
        # codex heads the preference order and is absent here, which is the whole gap.
        self.assertEqual(pr.reviewer_candidates("claude")[0], "codex")
        self.assertNotEqual(self.resolved, "codex")
        self.assertEqual(pr.REVIEWERS[self.resolved]["transport"], "openrouter")

    def test_a_grant_for_the_tool_that_runs_is_honoured(self):
        pr.data_permission(self.grant(self.resolved), tool=self.resolved)

    def test_a_grant_for_an_absent_tool_does_not_authorize_the_fallback(self):
        """The direction that matters: permission for codex must not licence a send to another."""
        with self.assertRaises(ValueError):
            pr.data_permission(self.grant("codex"), tool=self.resolved)


if __name__ == "__main__":
    unittest.main(verbosity=1)
