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
        bound = f"pr=42;base_ref={base_ref};base={'b' * 40}"      # goal checks name the PR, its target and base
        return {"prs": {cid: {"number": 42, "merged": merged, "merge_commit_sha": head if merged else None,
                              "head": {"sha": pr_head or head}, "base": {"ref": base_ref, "sha": "b" * 40, "repo": {"full_name": "o/r"}},
                              "mergeable_state": state}},
                "checks": {cid: {c: ("success", bound) for c in gd.MERGE_CHECKS} if checks else {"tests": ("failure", "")}},
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
        prs = {cid: {"number": doc["changes"][cid]["pr"], "merged": True, "head": {"sha": doc["changes"][cid]["head"]},
                     "merge_commit_sha": doc["changes"][cid]["head"], "base": {"ref": "main", "repo": {"full_name": "o/r"}}}
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



class Repairs(unittest.TestCase):
    """Goal gstack-delivery-completion: regression cases for the review findings on b321160
    (20261027-101630-b321160-f16vgusw F1, F2) and the fresh-checkout repair. Written before the fix."""
    observed = NextAction.observed

    def test_r1_a_merged_pull_request_of_another_target_repository_or_number_is_never_progress(self):
        doc = document(); h = doc["changes"]["implementation"]["head"]
        for bad in ({"base_ref": "release"},):
            obs = self.observed(h, merged=True, **bad)
            self.assertIn("blocked", gd.next_action(doc, obs), "a wrong-target merge is not record_merge")
        obs = self.observed(h, merged=True); obs["prs"]["implementation"]["base"]["repo"]["full_name"] = "someone/fork"
        self.assertIn("blocked", gd.next_action(doc, obs))
        obs = self.observed(h, merged=True); obs["prs"]["implementation"]["number"] = 99
        self.assertIn("blocked", gd.next_action(doc, obs))
        doc["changes"]["implementation"]["merge"] = {"verified": True, "head": h, "sha": h}   # a stale verified flag
        self.assertIn("blocked", gd.next_action(doc, self.observed(h, merged=True, base_ref="release")))
        self.assertEqual(gd.next_action(doc, self.observed(h, merged=True))["action"], "record_release")

    def test_r2_checks_reached_for_another_pull_request_or_an_old_base_cannot_merge(self):
        doc = document(); h = doc["changes"]["implementation"]["head"]
        self.assertEqual(gd.next_action(doc, self.observed(h))["action"], "merge")
        for binding in ("pr=43;base_ref=main;base=" + "b" * 40, "pr=42;base_ref=main;base=" + "0" * 40,
                        "pr=42;base_ref=release;base=" + "b" * 40, "", None):
            obs = self.observed(h)
            for c in ("goal-envelope", "goal-tests"):
                obs["checks"]["implementation"][c] = ("success", binding)
            self.assertIn("pending", gd.next_action(doc, obs), f"binding {binding!r} is not this PR at this base")

    def test_r5_a_saved_synced_flag_is_not_an_observation_of_the_checkout(self):
        sc = SyncCheckout(); sc.addCleanup = self.addCleanup
        src, bare, co, spec = sc.fixture()
        tip = sc.git(co, "rev-parse", "HEAD")
        self.assertEqual(gd.sync_checkout(spec, tip)["status"], "synced")
        spec["sync"] = {"status": "synced", "sha": tip}                  # what an earlier run saved
        (co / "a").write_text("edited after the sync\n")
        seen = gd.observe_checkout(spec, tip)
        self.assertEqual(seen["status"], "sync_pending"); self.assertIn("dirty", seen["reason"])
        doc = document(checkouts=[spec])
        for cid in doc["changes"]:
            doc["changes"][cid]["merge"] = {"verified": True}; doc["changes"][cid]["release_record"] = {"verified": True}
        self.assertNotEqual(gd.delivery_status(doc)["delivery_status"], "complete", "the saved flag alone is not synced")
        self.assertEqual(gd.delivery_status(doc, {"checkouts": {spec["name"]: seen}})["delivery_status"], "sync_pending")
        sc.git(co, "checkout", "--", "a")
        self.assertEqual(gd.observe_checkout(spec, tip)["status"], "synced")
        sc.git(co, "switch", "-qc", "elsewhere")
        self.assertIn("branch", gd.observe_checkout(spec, tip)["reason"])



class RepairsRound2(unittest.TestCase):
    """Review 20261027-124210-98b5ed8-o897p6eo F1: a checkout counts as synced only at the live
    remote tip, not merely containing the merge. Written before the fix."""

    def test_f1_a_clean_checkout_ahead_of_or_behind_the_remote_tip_is_not_synced(self):
        sc = SyncCheckout(); sc.addCleanup = self.addCleanup
        src, bare, co, spec = sc.fixture()
        tip = sc.git(co, "rev-parse", "HEAD")
        self.assertEqual(gd.observe_checkout(spec, tip)["status"], "synced")
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            sc.git(co, "config", k, v)
        (co / "local").write_text("unpushed\n"); sc.git(co, "add", "local"); sc.git(co, "commit", "-qm", "unpushed")
        seen = gd.observe_checkout(spec, tip)                              # clean, contains the merge, ahead of origin
        self.assertEqual(seen["status"], "sync_pending"); self.assertIn("remote", seen["reason"])
        sc.git(co, "reset", "-q", "--hard", tip)
        (src / "a").write_text("2\n"); sc.git(src, "commit", "-qam", "main advanced"); sc.git(src, "push", "-q", str(bare), "main")
        seen = gd.observe_checkout(spec, tip)                              # clean, contains the merge, behind origin
        self.assertEqual(seen["status"], "sync_pending"); self.assertIn("remote", seen["reason"])
        self.assertEqual(gd.sync_checkout(spec, tip)["status"], "synced")
        self.assertEqual(gd.observe_checkout(spec, tip)["status"], "synced")
        spec2 = dict(spec, remote=str(bare) + ".missing")
        sc.git(co, "remote", "set-url", "origin", spec2["remote"])
        self.assertEqual(gd.observe_checkout(spec2, tip)["status"], "sync_pending")   # an unreadable remote is not synced


class RepairsRound3(unittest.TestCase):
    """Review 20261027-144404-675bb13-9l70pwgt F1-F3 (goal gstack-delivery-completion-3 repairs 6-8).
    Written before the fix."""
    observed = NextAction.observed

    def goal_change(self, tested="t" * 40, finalized="f" * 40):
        doc = document(head=finalized)
        doc["changes"]["implementation"]["final"] = True
        obs = self.observed(finalized, review_head=tested)
        obs["reviews"]["implementation"]["finalized"] = {"pinned": True, "finalized_head": finalized}
        return doc, obs

    def test_g6_the_goal_change_merges_at_its_finalized_head_on_a_review_pinned_to_the_tested_head(self):
        doc, obs = self.goal_change()
        self.assertEqual(gd.next_action(doc, obs)["action"], "merge")
        doc, obs = self.goal_change(); obs["reviews"]["implementation"]["finalized"]["pinned"] = False
        self.assertIn("GO-011.2", gd.next_action(doc, obs)["pending"])
        doc, obs = self.goal_change(); obs["reviews"]["implementation"]["finalized"]["finalized_head"] = "9" * 40
        self.assertIn("finalized head", json.dumps(gd.next_action(doc, obs)))
        doc, obs = self.goal_change(); obs["reviews"]["implementation"].pop("finalized")
        self.assertIn("pending", gd.next_action(doc, obs), "no finalized evidence is not a pass")
        doc, obs = self.goal_change(); doc["changes"]["implementation"].pop("final")   # an ordinary change keeps the exact-head rule
        self.assertIn("not the candidate head", gd.next_action(doc, obs)["pending"])

    def test_g7_a_failed_git_inspection_is_never_read_as_clean_and_writes_nothing(self):
        sc = SyncCheckout(); sc.addCleanup = self.addCleanup
        real = gd._git
        self.addCleanup(setattr, gd, "_git", real)
        for verb in ("status", "rev-parse", "merge-base", "ls-remote", "remote", "symbolic-ref", "fetch"):
            with self.subTest(verb):
                src, bare, co, spec = sc.fixture()
                tip = sc.git(co, "rev-parse", "HEAD")          # clean, at the remote tip: synced if every read succeeds
                self.assertEqual(gd.observe_checkout(spec, tip)["status"], "synced")
                before = sc.snapshot(co)
                def fake(path, *args, _verb=verb, **kw):
                    if args and args[0] == _verb:
                        return subprocess.CompletedProcess(["git", *args], 128, "", f"fatal: {_verb} could not be read")
                    return real(path, *args, **kw)
                gd._git = fake
                try:
                    seen, synced = gd.observe_checkout(spec, tip), gd.sync_checkout(spec, tip)
                finally:
                    gd._git = real
                if verb != "fetch":                              # observation never fetches
                    self.assertEqual(seen["status"], "sync_pending", f"observe with a failing {verb}")
                    self.assertIn("could not be read", seen["reason"], f"observe names the failed {verb}")
                self.assertEqual(synced["status"], "sync_pending", f"sync with a failing {verb}")
                self.assertIn("could not be read", synced["reason"], f"sync names the failed {verb}")
                self.assertEqual(sc.snapshot(co), before, f"a failing {verb} wrote nothing")
                self.assertEqual(sc.git(co, "rev-parse", "HEAD"), tip)

    def test_g8_each_checkout_is_bound_to_its_repository_and_every_required_merge_is_checked(self):
        doc = document()
        c = doc["changes"]
        c["implementation"]["merge"] = {"verified": True, "sha": "a" * 40}
        c["other"] = dict(c["implementation"], repo="o/other", pr=50, merge={"verified": True, "sha": "b" * 40})
        c["later"] = dict(c["implementation"], pr=51, merge={"verified": True, "sha": "c" * 40})
        c["unmerged"] = dict(c["implementation"], pr=52, merge=None)
        c["goal-branch"] = dict(c["implementation"], pr=53, target="goal/g", merge={"verified": True, "sha": "d" * 40})
        for spec in ({"name": "mac", "repo": "o/r", "branch": "main"},
                     {"name": "mac", "remote": "https://github.com/O/R.git", "branch": "main"},
                     {"name": "mac", "remote": "git@github.com:o/r.git"}):
            self.assertEqual(sorted(gd.required_merges(doc, spec)), ["a" * 40, "c" * 40], spec)
        with self.assertRaises(gd.Blocked):
            gd.required_merges(doc, {"name": "mac", "remote": "/some/local/path.git"})   # no repository identity
        sc = SyncCheckout(); sc.addCleanup = self.addCleanup
        src, bare, co, spec = sc.fixture()
        first = sc.git(co, "rev-parse", "HEAD")
        sc.git(src, "switch", "-qc", "side", first)
        (src / "side").write_text("x\n"); sc.git(src, "add", "side"); sc.git(src, "commit", "-qm", "required but never on main")
        orphan = sc.git(src, "rev-parse", "HEAD"); sc.git(co, "fetch", "-q", str(src), orphan)
        self.assertEqual(gd.observe_checkout(spec, [first])["status"], "synced")
        seen = gd.observe_checkout(spec, [orphan, first])                 # the newest is there, an earlier one isn't
        self.assertEqual(seen["status"], "sync_pending"); self.assertIn(orphan[:12], seen["reason"])
        before = sc.snapshot(co)
        out = gd.sync_checkout(spec, [first, orphan])
        self.assertEqual(out["status"], "sync_pending"); self.assertIn(orphan[:12], out["reason"])
        self.assertEqual(sc.snapshot(co), before)
        spec_file = Path(co).parent / "spec.json"; spec_file.write_text(json.dumps(spec))
        r = subprocess.run([sys.executable, str(HERE / "goal_delivery.py"), "sync-checkout", "--checkout", str(spec_file),
                            "--merge", f"{first},{orphan}"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3, r.stderr); self.assertIn(orphan[:12], json.loads(r.stdout)["reason"])
        self.assertEqual(sc.snapshot(co), before)


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
