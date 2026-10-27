#!/usr/bin/env python3
"""Goal gstack-delivery-through-merge, item 2: the delivery record, the cumulative review limit
and the one allowed next action. Stdlib, offline."""
import json, os, subprocess, sys, tempfile, threading, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goal_delivery as gd

HERE = Path(__file__).resolve().parent


def document(head="h" * 40, base="b" * 40, companion=False, checkouts=()):
    change = lambda pr, h, b: {"repo": "o/r", "path": "/x", "base": b, "head": h, "target": "main", "pr": pr,
                               "review_id": f"rev-{pr}", "review_attempts": [], "original_findings": [], "merge": None, "release_record": None}
    doc = {"schema_version": 1, "goal": "g", "approval": {"repo": "o/r", "pr": 7, "review_id": 700, "head": base, "owner": "d"},
           "max_review_rounds": 3, "active_seconds": 17, "source_bindings": [],
           "changes": {"implementation": change(42, head, base)}, "release_companion": None, "required_checkouts": list(checkouts)}
    if companion:
        doc["changes"]["marketplace"] = change(43, "c" * 40, head); doc["release_companion"] = "marketplace"
    return doc


class ReserveReview(unittest.TestCase):
    def test_three_attempts_then_refused_and_a_replacement_id_does_not_reset(self):
        doc = document()
        for n in (1, 2, 3):
            self.assertEqual(gd.reserve_review(doc, "implementation", f"r{n}"), n)
        for rid in ("replacement", "another"):
            with self.assertRaises(gd.Blocked) as c:
                gd.reserve_review(doc, "implementation", rid)
            self.assertIn("exhausted", str(c.exception))
        self.assertEqual([a["review_id"] for a in doc["changes"]["implementation"]["review_attempts"]], ["r1", "r2", "r3"])

    def test_a_reserved_id_is_not_reserved_twice_and_an_unreadable_limit_blocks(self):
        doc = document(); gd.reserve_review(doc, "implementation", "r1")
        with self.assertRaises(gd.Blocked): gd.reserve_review(doc, "implementation", "r1")
        doc["max_review_rounds"] = "three"
        with self.assertRaises(gd.Blocked) as c: gd.reserve_review(doc, "implementation", "r2")
        self.assertIn("unreadable", str(c.exception))
        with self.assertRaises(gd.Blocked): gd.reserve_review(document(), "nope", "r1")

    def test_cli_persists_attempts_keeps_elapsed_time_and_exhaustion_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "delivery.json"); path.write_text(json.dumps(document()))
            for n in (1, 2, 3):
                r = subprocess.run([sys.executable, str(HERE / "goal_delivery.py"), "reserve-review", "--delivery", str(path),
                                    "--change-id", "implementation", "--review-id", f"r{n}"], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr); self.assertEqual(json.loads(r.stdout)["attempts_used"], n)
            before = path.read_bytes()
            r = subprocess.run([sys.executable, str(HERE / "goal_delivery.py"), "reserve-review", "--delivery", str(path),
                                "--change-id", "implementation", "--review-id", "r4"], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn("exhausted", r.stderr)
            self.assertEqual(path.read_bytes(), before, "a refused reservation wrote nothing")
            self.assertGreaterEqual(json.loads(path.read_text())["active_seconds"], 17)

    def test_concurrent_reservations_have_one_winner(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td, "delivery.json"); path.write_text(json.dumps(document()))
            results = []
            def go(rid):
                r = subprocess.run([sys.executable, str(HERE / "goal_delivery.py"), "reserve-review", "--delivery", str(path),
                                    "--change-id", "implementation", "--review-id", rid], capture_output=True, text=True)
                results.append((rid, r.returncode))
            threads = [threading.Thread(target=go, args=(f"same-{i}",)) for i in range(4)]
            for t in threads: t.start()
            for t in threads: t.join()
            attempts = json.loads(path.read_text())["changes"]["implementation"]["review_attempts"]
            self.assertEqual(len(attempts), min(3, len(threads)), attempts)
            self.assertEqual(sorted(a["attempt"] for a in attempts), list(range(1, len(attempts) + 1)), "attempts are numbered once each")


class NextAction(unittest.TestCase):
    def observed(self, head, merged=False, checks=True, review="no_blocking_findings", pr_head=None, state="clean",
                 review_head=None, base_ref="main", cid="implementation"):
        return {"prs": {cid: {"number": 42, "merged": merged, "merge_commit_sha": head if merged else None,
                              "head": {"sha": pr_head or head}, "base": {"ref": base_ref}, "mergeable_state": state}},
                "checks": {cid: {c: "success" for c in gd.MERGE_CHECKS} if checks else {"tests": "failure"}},
                "reviews": {cid: {"outcome": review, "head": review_head or head, "repo": "/x", "base": "b" * 40}}, "checkouts": {}}

    def test_incomplete_review_evidence_or_another_reviewed_base_is_pending(self):   # round 2 F2
        doc = document(); h = doc["changes"]["implementation"]["head"]
        obs = self.observed(h); obs["reviews"]["implementation"]["base"] = "z" * 40
        self.assertIn("not the candidate range", gd.next_action(doc, obs)["pending"])
        obs = self.observed(h); obs["reviews"]["implementation"] = {"outcome": "no_blocking_findings", "incomplete": "no packet"}
        self.assertIn("incomplete", gd.next_action(doc, obs)["pending"])
        obs = self.observed(h); obs["reviews"]["implementation"].pop("repo")
        self.assertIn("incomplete", gd.next_action(doc, obs)["pending"])

    def test_a_review_counts_only_at_the_candidate_head_in_this_repository_and_the_target_must_match(self):   # review F2
        doc = document(); h = doc["changes"]["implementation"]["head"]
        self.assertIn("pending", gd.next_action(doc, self.observed(h, review_head="o" * 40)))
        obs = self.observed(h); obs["reviews"]["implementation"]["repo"] = "/elsewhere"
        self.assertIn("blocked", gd.next_action(doc, obs))
        self.assertIn("blocked", gd.next_action(doc, self.observed(h, base_ref="release")))
        self.assertEqual(gd.next_action(doc, self.observed(h))["action"], "merge")

    def test_a_verified_merge_github_contradicts_is_blocked_and_an_unobserved_one_is_pending(self):   # review F3
        doc = document(); h = doc["changes"]["implementation"]["head"]
        doc["changes"]["implementation"]["merge"] = {"verified": True, "head": h, "sha": h}
        self.assertIn("persisted merge is invalid", gd.next_action(doc, self.observed(h, merged=False))["blocked"])
        self.assertIn("pending", gd.next_action(doc, {"prs": {}}))
        self.assertEqual(gd.next_action(doc, self.observed(h, merged=True))["action"], "record_release")

    def test_observations_are_keyed_by_change_not_by_pull_request_number(self):   # review F5
        doc = document(); h = doc["changes"]["implementation"]["head"]
        obs = self.observed(h, merged=True, cid="someone-else")          # another change's merged #42 at the same commit
        self.assertIn("pending", gd.next_action(doc, obs))

    def test_merge_only_with_a_clean_review_green_checks_and_the_candidate_head(self):
        doc = document(); h = doc["changes"]["implementation"]["head"]
        self.assertEqual(gd.next_action(doc, self.observed(h))["action"], "merge")
        self.assertIn("pending", gd.next_action(doc, self.observed(h, checks=False)))
        self.assertIn("pending", gd.next_action(doc, self.observed(h, review="blocking_findings")))
        self.assertIn("blocked", gd.next_action(doc, self.observed(h, pr_head="m" * 40)))
        self.assertIn("pending", gd.next_action(doc, {"prs": {}}))

    def test_an_observed_merge_is_recorded_before_anything_else_and_a_declared_one_counts_for_nothing(self):
        doc = document(); h = doc["changes"]["implementation"]["head"]
        self.assertEqual(gd.next_action(doc, self.observed(h, merged=True))["action"], "record_merge")
        doc["changes"]["implementation"]["merge"] = {"head": h, "sha": h}          # no verified: a declaration
        self.assertEqual(gd.next_action(doc, self.observed(h, merged=True))["action"], "record_merge")
        doc["changes"]["implementation"]["merge"]["verified"] = True
        self.assertEqual(gd.next_action(doc, self.observed(h, merged=True))["action"], "record_release")
        doc["changes"]["implementation"]["release_record"] = {"verified": True, "path": "/p"}
        self.assertEqual(gd.next_action(doc, self.observed(h, merged=True))["action"], "complete")
        self.assertIn("pending", gd.next_action(doc, {"prs": {}}), "complete needs the merge re-observed, not remembered")

    def test_companion_checkouts_and_blocked_states(self):
        doc = document(companion=True, checkouts=[{"name": "mac", "path": "/m", "required": True}])
        h = doc["changes"]["implementation"]["head"]
        for cid in ("implementation", "marketplace"):
            doc["changes"][cid]["merge"] = {"verified": True}; doc["changes"][cid]["release_record"] = {"verified": True}
        self.assertIn("pending", gd.next_action(doc, {"checkouts": {}}), "a recorded merge not re-observed is pending, not progress")
        prs = {cid: {"merged": True, "head": {"sha": doc["changes"][cid]["head"]}, "merge_commit_sha": doc["changes"][cid]["head"]}
               for cid in ("implementation", "marketplace")}
        self.assertEqual(gd.next_action(doc, {"prs": prs, "checkouts": {}}), {"action": "sync_checkout", "checkout": "mac"})
        self.assertEqual(gd.next_action(doc, {"prs": prs, "checkouts": {"mac": {"status": "synced"}}}), {"action": "complete"})
        doc["source_bindings"] = [{"id": "bank", "stale": True}]
        self.assertIn("stale", gd.next_action(doc, {})["blocked"])
        doc = document(); doc["approval"]["head"] = ""
        self.assertIn("authority", gd.next_action(doc, {})["blocked"])
        doc = document(); doc["max_review_rounds"] = None
        self.assertIn("budget", gd.next_action(doc, {})["blocked"])

    def test_delivery_status_needs_every_merge_record_companion_and_checkout(self):
        doc = document(companion=True, checkouts=[{"name": "mac", "path": "/m", "required": True}])
        self.assertEqual(gd.delivery_status(doc)["delivery_status"], "in_progress")
        for cid in ("implementation", "marketplace"):
            doc["changes"][cid]["merge"] = {"verified": True}
        self.assertIn("marketplace: merged, release not recorded", gd.delivery_status(doc)["missing"])
        for cid in ("implementation", "marketplace"):
            doc["changes"][cid]["release_record"] = {"verified": True}
        s = gd.delivery_status(doc); self.assertEqual(s["delivery_status"], "sync_pending"); self.assertIn("mac", json.dumps(s))
        self.assertEqual(gd.delivery_status(doc, {"checkouts": {"mac": {"status": "synced"}}})["delivery_status"], "complete")
        doc["release_companion"] = "ghost"
        self.assertEqual(gd.delivery_status(doc)["delivery_status"], "blocked")



class SyncCheckout(unittest.TestCase):
    """Item 3: a merge not yet on the remote leaves the checkout exactly as it was; a checkout
    already at the tip is reported synced without being written. (The five refusals and the
    advanced-main fast-forward are the goal test's.)"""

    def git(self, cwd, *a):
        return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True).stdout.strip()

    def fixture(self):
        root = Path(tempfile.mkdtemp(prefix="sync-")); self.addCleanup(subprocess.run, ["rm", "-rf", str(root)])
        src, bare, co = root / "src", root / "origin.git", root / "co"
        self.git(root, "init", "-q", "-b", "main", str(src))
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            self.git(src, "config", k, v)
        (src / "a").write_text("1\n"); self.git(src, "add", "a"); self.git(src, "commit", "-qm", "base")
        self.git(root, "init", "--bare", "-q", "-b", "main", str(bare)); self.git(src, "push", "-q", str(bare), "main")
        self.git(root, "clone", "-q", str(bare), str(co))
        spec = {"name": "mac", "path": str(co), "host": gd.socket.gethostname(), "remote": str(bare), "branch": "main"}
        return src, bare, co, spec

    def snapshot(self, co):
        return sorted((str(p.relative_to(co)), p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else b"")
                      for p in Path(co).rglob("*"))

    def test_a_merge_not_on_the_remote_yet_is_pending_and_nothing_is_written(self):
        src, bare, co, spec = self.fixture()
        (src / "a").write_text("2\n"); self.git(src, "commit", "-qam", "unpushed merge")
        merge = self.git(src, "rev-parse", "HEAD")
        self.git(co, "fetch", "-q", str(src), merge)   # the object exists locally; the remote branch lacks it
        before = self.snapshot(co)
        out = gd.sync_checkout(spec, merge)
        self.assertEqual(out["status"], "sync_pending"); self.assertIn("not on", out["reason"])
        self.assertEqual(self.snapshot(co), before)

    def test_a_checkout_already_at_the_tip_is_synced_without_writing(self):
        src, bare, co, spec = self.fixture()
        tip = self.git(co, "rev-parse", "HEAD")
        before = self.snapshot(co)
        out = gd.sync_checkout(spec, tip)
        self.assertEqual((out["status"], out["sha"]), ("synced", tip))
        self.assertEqual(self.snapshot(co), before)


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
