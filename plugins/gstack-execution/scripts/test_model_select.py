#!/usr/bin/env python3
"""MR-001.9: model_select.mjs is executed as a subprocess against a stub gateway, never only its
rule table in isolation, and the dispatcher's two hooks (open refuses a packet without the field,
record-release appends the outcome) run on real review directories.
"""
import argparse
import contextlib
import http.server
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "model_select.mjs"
PLUGIN = HERE.parent
sys.path.insert(0, str(HERE))
import peer_review as pr  # noqa: E402

DESIGN = """# Fixture

### FX-001 — A fixture item

**Status:** planned.

**Links introduced:** one field on the packet.

1. `scripts/a.py` returns x + 1.
2. `test_a.py` passes.
"""


class Stub(http.server.BaseHTTPRequestHandler):
    """The gateway's evaluation-model endpoint. Answers come from `Stub.answers`, keyed by question."""
    answers = {}
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.seen.append(body)
        # an int or bool answer is 0.9 / 0.1; a float is the probability verbatim (MR-002 boundary cases)
        out = {"answers": {k: {"type": "boolean", "probability": Stub.answers[k] if isinstance(Stub.answers.get(k), float)
                               else (0.9 if Stub.answers.get(k) else 0.1)}
                           for k in body["questions"]},
               "usage": {"inputTokens": 12, "outputTokens": 1}}
        raw = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def repo():
    d = Path(tempfile.mkdtemp(prefix="mr001-")).resolve()   # macOS: /var is /private/var, and record-release resolves --repo
    sh = lambda *c: subprocess.run(["git", "-C", str(d), *c], check=True, capture_output=True, text=True).stdout.strip()
    sh("init", "-q"); sh("config", "user.email", "t@t"); sh("config", "user.name", "t")
    sh("remote", "add", "origin", "https://github.com/fixture-org/fixture-repo.git")
    (d / "a.py").write_text("def f(x):\n    return x\n"); sh("add", "."); sh("commit", "-qm", "base"); base = sh("rev-parse", "HEAD")
    (d / "a.py").write_text("def f(x):\n    return x + 1\n"); sh("commit", "-qam", "head"); head = sh("rev-parse", "HEAD")
    return d, base, head


def packet(d, base, head, **extra):
    pk = {"items": ["FX-001"], "outcome": "f adds one", "acceptance_criteria": ["`scripts/a.py` returns x + 1.", "`test_a.py` passes."],
          "repos": [{"path": str(d), "base": base, "head": head}], "changed_behavior": "f returns x+1", "exclusions": [],
          "tests": {"commands": [], "results": "", "environment": "test"}, "release_owner": "fixture-human",
          "data_use": {"owner": "fixture-human", "classification": "test", "allow_repository": True, "allow_history": True,
                       "allowed_tools": ["codex", "claude"]}}
    pk.update(extra)
    return pk


class Selector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("node"):
            raise AssertionError("node is not installed; the selector cannot be tested, and that is a failure, not a skip")
        if not (PLUGIN / "node_modules" / "ai").is_dir():
            raise AssertionError(f"`ai` is not installed; run `npm ci` in {PLUGIN}. A skipped selector test is not a pass.")
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.d, self.base, self.head = repo()
        self.root = Path(tempfile.mkdtemp(prefix="mr001-root-"))
        self.pfile = self.root / "packet.json"
        self.design = self.root / "DESIGN.md"; self.design.write_text(DESIGN)
        self.pfile.write_text(json.dumps(packet(self.d, self.base, self.head)))
        Stub.answers = {}; Stub.seen = []

    def run_select(self, *args, answers=None, **env):
        Stub.answers = answers or {}
        e = {k: v for k, v in os.environ.items() if k not in {"AI_GATEWAY_API_KEY", "GSTACK_AIGATEWAY_ENV", "JEV_ENDPOINT", "GSTACK_MODEL_ROUTING"}}
        e.update(AI_GATEWAY_API_KEY="k-env", JEV_ENDPOINT=self.endpoint, GSTACK_PEER_REVIEW_DIR=str(self.root / "reviews"), **env)
        r = subprocess.run(["node", str(SCRIPT), *args], capture_output=True, text=True, env=e, cwd=str(HERE))
        return r, json.loads(self.pfile.read_text()).get("model_selection")

    def ledger(self):
        f = self.root / "reviews" / "model-selection" / "fixture-org-fixture-repo.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        return f

    # ---- MR-001.1 and .2: questions reach the model with the inputs; the rule table decides ----

    def test_each_rule_row_from_fixed_answers(self):
        cases = [({"trust_boundary": 1}, "floor", "trust_boundary"),
                 ({"cross_file": 1, "docs_only": 1}, "floor", "cross_file"),
                 ({"docs_only": 1}, "light", "docs_only"),
                 ({"docs_only": 1, "has_tests": 1}, "standard", "default"),
                 ({}, "standard", "default"),
                 ({"has_tests": 1}, "standard", "default")]
        for answers, tier, rule in cases:
            r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers=answers)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((ms["status"], ms["mode"], ms["tier"], ms["rule"], ms["routing"]), ("checked", "shadow", tier, rule, "advice"), ms)
            self.assertEqual(set(ms["answers"]), {"trust_boundary", "cross_file", "docs_only", "has_tests", "risky"})
        body = Stub.seen[-1]
        self.assertEqual(set(body["questions"]), {"trust_boundary", "cross_file", "docs_only", "has_tests", "risky"})
        self.assertEqual(body["state"]["criteria_count"], 2)
        self.assertIn("scripts/a.py", body["state"]["paths_named"])
        self.assertEqual(body["state"]["paths_named"], ["scripts/a.py", "test_a.py"])
        # F1 (review 20261013-175825): the named files are read, not only named; a.py exists at the head, scripts/a.py does not
        self.assertEqual(body["state"]["files_read"], 0)
        self.assertEqual([f["exists"] for f in body["state"]["files"]], [False, False])
        # F2 (review 20261013-182804): the design file is required
        r = subprocess.run(["node", str(SCRIPT), "recommend", str(self.pfile)], capture_output=True, text=True, cwd=str(HERE))
        self.assertEqual(r.returncode, 2); self.assertIn("Links introduced", r.stderr)
        # round 2: the line is read from the item's own section only, and a missing item or line is refused
        self.design.write_text(DESIGN.replace("**Links introduced:** one field on the packet.\n\n", ""))   # FX-001 loses its line; FX-002 has none
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={})
        self.assertEqual(r.returncode, 2, r.stderr); self.assertIn("no \"Links introduced\" line in its own section", r.stderr)
        # FX-001 without a line, FX-002 with one: FX-002's line is not FX-001's
        self.design.write_text(DESIGN.replace("**Links introduced:** one field on the packet.\n\n", "") + "\n### FX-002 — Another item\n\n**Links introduced:** the next item's line.\n")
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={})
        self.assertEqual(r.returncode, 2, r.stderr); self.assertIn("FX-001", r.stderr)
        pk = packet(self.d, self.base, self.head, items=["FX-009"]); self.pfile.write_text(json.dumps(pk))
        self.design.write_text(DESIGN)
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={})
        self.assertEqual(r.returncode, 2, r.stderr); self.assertIn("declares no item FX-009", r.stderr)
        self.assertEqual(body["state"]["links_introduced"], [{"item": "FX-001", "links_introduced": "one field on the packet."}])

    def test_a_goal_plan_item_is_read_by_position(self):
        # F1 (review 20261013-193610): goals/<id>/PLAN.md numbers its items and declares no links
        plan = self.root / "goals" / "g1" / "PLAN.md"; plan.parent.mkdir(parents=True)
        plan.write_text("# Plan\n\n1. First thing\n   - a passes\n2. Second thing\n   - b passes\n")
        pk = packet(self.d, self.base, self.head, items=["g1/2"]); self.pfile.write_text(json.dumps(pk))
        r, ms = self.run_select("recommend", str(self.pfile), str(plan), answers={})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(ms["inputs"]["links_introduced"], [{"item": "g1/2", "links_introduced": "(plan item, no links declared) Second thing"}])
        pk["items"] = ["g1/3"]; self.pfile.write_text(json.dumps(pk))
        r, ms = self.run_select("recommend", str(self.pfile), str(plan), answers={})
        self.assertEqual(r.returncode, 2, r.stderr); self.assertIn("declares no item g1/3 (2 items)", r.stderr)

    # ---- MR-002: the risk axis and the asymmetric bars, at their boundaries ----

    def test_risky_forces_the_floor_first_and_the_bars_are_asymmetric(self):
        cases = [({"risky": 0.70, "docs_only": 0.95}, "floor", "risky"),
                 ({"risky": 0.69, "docs_only": 0.95}, "light", "docs_only"),
                 ({"trust_boundary": 0.30}, "floor", "trust_boundary"),
                 ({"trust_boundary": 0.29}, "standard", "default"),
                 ({"cross_file": 0.30}, "floor", "cross_file"),
                 ({"docs_only": 0.60, "has_tests": 0.10}, "light", "docs_only"),
                 ({"docs_only": 0.59, "has_tests": 0.10}, "standard", "default"),
                 ({"docs_only": 0.95, "has_tests": 0.50}, "standard", "default"),
                 ({"docs_only": 0.95, "has_tests": 0.49}, "light", "docs_only")]
        for answers, tier, rule in cases:
            r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers=answers)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((ms["tier"], ms["rule"]), (tier, rule), (answers, ms))
            self.assertEqual(ms["thresholds"], {"risky": 0.70, "upgrade": 0.30, "downgrade": 0.60, "has_tests": 0.50})
        self.assertIn("bars: risky 0.7, upgrade 0.3, downgrade 0.6, has_tests 0.5", r.stdout)
        self.assertEqual(Stub.seen[-1]["questions"]["risky"]["instructions"][:46], "Does this item change code that touches produc")

    def test_a_trust_boundary_item_is_never_below_floor(self):
        for extra in ({"docs_only": 1}, {"docs_only": 1, "has_tests": 1}, {"cross_file": 1}):
            r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={"trust_boundary": 1, **extra})
            self.assertEqual((ms["tier"], ms["rule"]), ("floor", "trust_boundary"), ms)

    # ---- MR-001.3: shadow writes the field; open refuses a packet without it ----

    def test_shadow_writes_the_packet_field_and_open_refuses_a_packet_without_it(self):
        saved = pr.REVIEW_DIR, pr.choose_reviewer
        pr.REVIEW_DIR = self.root / "reviews"
        pr.choose_reviewer = lambda builder, forced=None, require_installed=True: ("codex", False)
        try:
            with self.assertRaises(pr.ReviewError) as cm, contextlib.redirect_stdout(io.StringIO()):
                pr.cmd_open(argparse.Namespace(builder="claude", packet=str(self.pfile), max_rounds=3, timeout=30))
            self.assertEqual(cm.exception.outcome, "model_selection_missing")
            self.assertFalse(list((self.root / "reviews").glob("2*")), "a refused open leaves no review directory")
            r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={})
            self.assertEqual(ms["mode"], "shadow")
            with contextlib.redirect_stdout(io.StringIO()):
                st = pr.cmd_open(argparse.Namespace(builder="claude", packet=str(self.pfile), max_rounds=3, timeout=30))
            self.assertEqual(st["model_selection"], {"status": "checked", "mode": "shadow", "tier": "standard", "rule": "default", "override": None})
            # a packet claiming no item (a selftest, a goal test) is not an item review and opens as before
            pk = packet(self.d, self.base, self.head); del pk["items"]; self.pfile.write_text(json.dumps(pk))
            with contextlib.redirect_stdout(io.StringIO()):
                st2 = pr.cmd_open(argparse.Namespace(builder="claude", packet=str(self.pfile), max_rounds=3, timeout=30))
            self.assertIsNone(st2["model_selection"])
        finally:
            pr.REVIEW_DIR, pr.choose_reviewer = saved

    # ---- MR-001.4: record-release appends the outcome from state.json ----

    def test_record_release_appends_a_ledger_line_with_the_outcome(self):
        saved = pr.REVIEW_DIR, pr.github_get
        pr.REVIEW_DIR = self.root / "reviews"
        try:
            d = pr.REVIEW_DIR / "20260101-000000-abcdef0-fixture"; d.mkdir(parents=True)
            pk = packet(self.d, self.base, self.head, model_selection={"status": "checked", "mode": "shadow", "tier": "light", "rule": "docs_only",
                                                                       "answers": {"docs_only": {"probability": 0.9}}, "declared_tier": None})
            pr.save(d, "packet.json", pk, "gate_output")
            state = {"review_id": d.name, "outcome": "fixes_verified", "rounds_used": 2, "release_owner": "fixture-human",
                     "model_selection": {"status": "checked", "mode": "shadow", "tier": "light", "rule": "docs_only", "override": None}}
            pr.save(d, "state.json", state, "gate_output")
            pr.save(d, "round-1.json", {"findings": [{"id": "F1", "severity": "blocking"}, {"id": "F2", "severity": "follow_up"}],
                                        "unknowns_raised": ["u1"]}, "gate_output")
            pr.save(d, "round-2.json", {"findings": [], "unknowns_raised": []}, "gate_output")
            pr.save(d, "release.json", {"repos": pk["repos"], "release_owner": "fixture-human", "target": "main",
                                        "requested_at": "2026-01-01T00:00:00Z"}, "gate_output")
            pr.github_get = lambda name, path: ({"merged": True, "merged_at": "2026-01-01T01:00:00Z", "merge_commit_sha": "m" * 40,
                                                 "html_url": "https://github.com/fixture-org/fixture-repo/pull/7",
                                                 "head": {"sha": self.head}, "base": {"ref": "main", "repo": {"full_name": "fixture-org/fixture-repo"}},
                                                 "merged_by": {"login": "fixture-human", "type": "User"}}
                                                if path.startswith("pulls/") else [])
            saved_pr = pr.passing_review
            pr.passing_review = lambda dd: (state, pk)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    pr.cmd_record_release(argparse.Namespace(review_id=d.name, repo=str(self.d), pr=7))
            finally:
                pr.passing_review = saved_pr
            lines = [json.loads(l) for l in self.ledger().read_text().splitlines()]
            self.assertEqual(len(lines), 1)
            line = lines[0]
            self.assertEqual(line["review_id"], d.name)
            self.assertEqual(line["recommendation"], {"tier": "light", "rule": "docs_only", "mode": "shadow"})
            self.assertEqual(line["declared_tier"], "floor")      # shadow: the build ran on the floor
            self.assertEqual(line["outcome"], {"rounds_used": 2, "blocking_findings": 1, "unknowns_raised": 1,
                                               "release_outcome": "human_merge_recorded"})
            self.assertIsNone(line["override"])
            self.assertEqual(line["routing"], "advice")     # MR-001.6 as amended: nothing launched this build
        finally:
            pr.REVIEW_DIR, pr.github_get = saved

    # ---- MR-001.5 and .6: score prints zeros; route is refused until the history is there ----

    def test_score_prints_zeros_on_an_empty_ledger(self):
        r, _ = self.run_select("score", "--repo", str(self.d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 lines, 0 scored (shadow), 0 overridden, 0 routed, 0 open or abandoned reviews skipped", r.stdout)
        for t in ("floor", "standard", "light"):
            self.assertIn(f"{t:<8} 0 items, 0 cleared", r.stdout)
        self.assertIn("agreement 0 over 0 standard/light recommendations", r.stdout)
        self.assertIn("by rule  risky 0 fired 0 cleared, trust_boundary 0 fired 0 cleared, cross_file 0 fired 0 cleared, docs_only 0 fired 0 cleared, default 0 fired 0 cleared", r.stdout)

    def _lines(self, n, ok):
        """n scored lines recommending `standard`, `ok` of them cleared."""
        out = []
        for i in range(n):
            cleared = i < ok
            out.append({"review_id": f"r{i}", "recommendation": {"tier": "standard", "rule": "default", "mode": "shadow"},
                        "declared_tier": "floor", "override": None,
                        "outcome": {"rounds_used": 1 if cleared else 3, "blocking_findings": 0 if cleared else 2,
                                    "unknowns_raised": 0, "release_outcome": "agent_merge_autonomous"}})
        return "\n".join(json.dumps(l) for l in out) + "\n"

    def test_a_named_file_that_exists_is_read_at_its_head(self):
        pk = packet(self.d, self.base, self.head, acceptance_criteria=["`a.py recommend <packet>` returns x + 1.", "`test_a.py` passes.", "`x + 1` is not a path."])
        self.pfile.write_text(json.dumps(pk))
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={})
        self.assertEqual(r.returncode, 0, r.stderr)
        files = {f["path"]: f for f in ms["inputs"]["files"]}
        self.assertEqual(ms["inputs"]["files_read"], 1)
        self.assertEqual((files["a.py"]["exists"], files["a.py"]["lines"], files["a.py"]["at"]), (True, 3, self.head))
        self.assertIn("return x + 1", files["a.py"]["head"])
        self.assertEqual(files["test_a.py"], {"path": "test_a.py", "exists": False})
        # F1 (review 20261013-182804): read at the packet's head, not the working tree; never outside the repository
        (self.d / "a.py").write_text("WORKING TREE EDIT\n")
        secret = self.root / "secret.env"; secret.write_text("TOKEN=x\n")
        rel_out = os.path.relpath(secret, self.d)
        pk["acceptance_criteria"] = ["`a.py` returns x + 1.", f"`{rel_out}` is read.", "`/etc/hosts` is read."]
        pk["repos"][0]["head"] = self.base
        self.pfile.write_text(json.dumps(pk))
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={})
        self.assertEqual(r.returncode, 0, r.stderr)
        files = {f["path"]: f for f in ms["inputs"]["files"]}
        self.assertEqual(files["a.py"]["at"], self.base)
        self.assertIn("return x\n", files["a.py"]["head"] + "\n"); self.assertNotIn("WORKING TREE", files["a.py"]["head"])
        self.assertEqual(files[rel_out]["exists"], False)
        self.assertNotIn("/etc/hosts", files)
        self.assertNotIn("TOKEN=x", json.dumps(ms))

    def test_a_selector_that_did_not_run_does_not_open(self):
        # F2 (review 20261013-175825): the gate is a checked recommendation, not the field's presence
        pk = packet(self.d, self.base, self.head, model_selection={"status": "unavailable", "mode": "shadow", "why": "no key"})
        self.pfile.write_text(json.dumps(pk))
        saved = pr.REVIEW_DIR, pr.choose_reviewer
        pr.REVIEW_DIR = self.root / "reviews"
        pr.choose_reviewer = lambda builder, forced=None, require_installed=True: ("codex", False)
        try:
            with self.assertRaises(pr.ReviewError) as cm, contextlib.redirect_stdout(io.StringIO()):
                pr.cmd_open(argparse.Namespace(builder="claude", packet=str(self.pfile), max_rounds=3, timeout=30))
            self.assertEqual(cm.exception.outcome, "model_selection_missing")
            self.assertIn("unavailable", str(cm.exception))
        finally:
            pr.REVIEW_DIR, pr.choose_reviewer = saved

    def test_score_counts_open_reviews_it_skipped_and_routed_lines_apart(self):
        # a review directory with a checked packet for this repo and no ledger line is skipped, and said so
        d = self.root / "reviews" / "20260101-000000-abcdef0-open"; d.mkdir(parents=True)
        (d / "packet.json").write_text(json.dumps(packet(self.d, self.base, self.head, model_selection={"status": "checked", "mode": "shadow", "tier": "light"})))
        other = self.root / "reviews" / "20260101-000000-abcdef0-other"; other.mkdir()
        (other / "packet.json").write_text(json.dumps({"repos": [{"path": "/elsewhere"}], "model_selection": {"status": "checked"}}))
        self.ledger().write_text(self._lines(2, 2) + json.dumps({"review_id": "routed", "recommendation": {"tier": "light", "rule": "docs_only", "mode": "route"},
                                                                  "declared_tier": "light", "override": None,
                                                                  "outcome": {"rounds_used": 1, "blocking_findings": 0, "unknowns_raised": 0, "release_outcome": "x"}}) + "\n")
        r, _ = self.run_select("score", "--repo", str(self.d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("3 lines, 2 scored (shadow), 0 overridden, 1 routed, 1 open or abandoned reviews skipped", r.stdout)
        # F4 (review 20261013-182804): the routed light item is in light's row; it is not in agreement
        self.assertIn("light    1 items, 1 cleared in at most 2 rounds with no blocking finding, 0 did not, 1 of them routed", r.stdout)
        self.assertIn("standard 2 items, 2 cleared", r.stdout)
        # MR-002.4: the per-rule row counts every non-overridden line under the rule that fired for it
        self.assertIn("docs_only 1 fired 1 cleared, default 2 fired 2 cleared", r.stdout)
        self.assertIn("agreement 1 over 2 standard/light recommendations", r.stdout)

    def test_route_is_refused_with_insufficient_history_until_twenty_lines_at_point_nine(self):
        # F4 (review 20261013-175825): the gate reads shadow lines only and compares agreement unrounded
        self.ledger().write_text(self._lines(20, 18).replace('"shadow"', '"route"'))
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={}, GSTACK_MODEL_ROUTING="route")
        self.assertEqual((r.returncode, ms["mode"], ms["route_refused"]["lines"]), (5, "shadow", 0), r.stderr)
        self.ledger().write_text(self._lines(1000, 899))        # 0.899, which prints as 0.899 and must not pass 0.90
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={}, GSTACK_MODEL_ROUTING="route")
        self.assertEqual((r.returncode, ms["route_refused"]["agreement"]), (5, 0.899), r.stderr)
        for n, ok, expect in ((19, 19, False), (20, 17, False), (20, 18, True)):
            self.ledger().write_text(self._lines(n, ok))
            r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={}, GSTACK_MODEL_ROUTING="route")
            if expect:
                self.assertEqual((r.returncode, ms["mode"]), (0, "route"), (n, ok, r.stderr))
                self.assertNotIn("route_refused", ms)
            else:
                self.assertEqual((r.returncode, ms["mode"]), (5, "shadow"), (n, ok, r.stderr))
                self.assertEqual(ms["route_refused"]["reason"], "insufficient_history")
                self.assertEqual(ms["route_refused"]["lines"], n)
                self.assertIn("insufficient_history", r.stderr)
                self.assertIn(f"{n} scored lines", r.stderr)
        r, _ = self.run_select("score", "--repo", str(self.d))
        self.assertIn("standard 20 items, 18 cleared", r.stdout)
        self.assertIn("agreement 0.9 over 20", r.stdout)

    # ---- MR-001.7: an override wins, is recorded, and may not go below light ----

    def test_an_override_wins_and_is_recorded_and_a_bad_one_is_refused(self):
        pk = packet(self.d, self.base, self.head, model_selection={"override": {"tier": "floor", "reason": "touches the token path"}})
        self.pfile.write_text(json.dumps(pk))
        r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={"docs_only": 1})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((ms["tier"], ms["applied_tier"], ms["override"]["reason"]), ("light", "floor", "touches the token path"))
        for bad in ({"tier": "haiku", "reason": "cheaper"}, {"tier": "light"}, {"tier": "nano", "reason": "x"}):
            pk["model_selection"] = {"override": bad}; self.pfile.write_text(json.dumps(pk))
            r, ms = self.run_select("recommend", str(self.pfile), str(self.design), answers={})
            self.assertEqual(r.returncode, 2, (bad, r.stderr))
            self.assertIn("override", r.stderr)
        # the overridden item is counted apart from the scored ones
        self.ledger().write_text(json.dumps({"review_id": "o", "recommendation": {"tier": "light", "rule": "docs_only", "mode": "shadow"},
                                             "declared_tier": "floor", "override": {"tier": "floor", "reason": "x"},
                                             "outcome": {"rounds_used": 1, "blocking_findings": 0, "unknowns_raised": 0, "release_outcome": "x"}}) + "\n")
        r, _ = self.run_select("score", "--repo", str(self.d))
        self.assertIn("1 lines, 0 scored (shadow), 1 overridden", r.stdout)


if __name__ == "__main__":
    unittest.main()
