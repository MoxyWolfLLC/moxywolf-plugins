#!/usr/bin/env python3
"""XE-015: a reviewer that opened none of the files it was offered examined nothing.

The predicate is cheap to test in isolation and that is not enough: the defect this item exists
for was a round that produced a well-formed verdict over nothing, so the wiring inside cmd_round
is the part that has to be exercised. The second test drives a real round end to end.
"""
import argparse, json, os, subprocess, tempfile
from pathlib import Path
import peer_review as pr


def test_predicate_fires_only_on_a_measured_reviewer_that_read_nothing():
    assert pr.examined_nothing({"read_tracking": "available", "offered_count": 11, "examined_count": 0})
    assert not pr.examined_nothing({"read_tracking": "available", "offered_count": 11, "examined_count": 3})
    # An api reviewer has no filesystem and a noatime mount cannot be measured. In both the empty
    # list is a constant, not a choice, so reading it as "examined nothing" is the EV-001 error.
    assert not pr.examined_nothing({"read_tracking": "not_applicable"})
    assert not pr.examined_nothing({"read_tracking": "unavailable"})
    # Nothing offered is nothing to have missed.
    assert not pr.examined_nothing({"read_tracking": "available", "offered_count": 0, "examined_count": 0})
    assert not pr.examined_nothing({})


def test_a_round_that_read_nothing_is_refused_on_that_and_not_on_its_verdict():
    """The reviewer here returns a CLEAN verdict that validates. Before XE-015 this round was
    recorded as no_blocking_findings, which is the whole defect: a clean cross-tool review over
    nothing. The outcome must name what actually went wrong, and the record must still carry what
    the reviewer said so the refusal can be read back.
    """
    tmp = Path(tempfile.mkdtemp(prefix="gstack-xe015-"))
    saved_dir, saved_report, saved_run = pr.REVIEW_DIR, pr.examined_report, pr.run_reviewer
    saved_choose = pr.choose_reviewer
    try:
        # Not _SELFTEST and not the FAKE_CMD hook: both exempt the round from measurement, and
        # exempting the thing under test is how a guard passes without guarding. run_reviewer is
        # replaced instead, so cmd_round takes exactly the path a live codex round takes.
        pr.REVIEW_DIR = tmp / "reviews"
        repo = tmp / "repo"; repo.mkdir()
        sh = lambda *c: subprocess.run(["git", "-C", str(repo), *c], check=True,
                                       capture_output=True, text=True).stdout.strip()
        sh("init", "-q"); sh("config", "user.email", "t@t"); sh("config", "user.name", "t")
        (repo / "a.py").write_text("def f(x):\n    return x\n")
        sh("add", "."); sh("commit", "-qm", "base"); base = sh("rev-parse", "HEAD")
        (repo / "a.py").write_text("def f(x):\n    return x + 1\n")
        sh("commit", "-qam", "head"); head = sh("rev-parse", "HEAD")
        pk = {"outcome": "f adds one", "acceptance_criteria": ["f(1) == 2"],
              "repos": [{"path": str(repo), "base": base, "head": head}],
              "changed_behavior": "f returns x+1", "exclusions": [],
              "tests": {"commands": [], "results": "", "environment": "selftest"},
              "release_owner": "fixture-human",
              "data_use": {"owner": "fixture-human", "classification": "test",
                           "allow_repository": True, "allow_history": True,
                           "allowed_tools": ["codex", "claude"]}}
        pfile = tmp / "packet.json"; pfile.write_text(json.dumps(pk))

        # A reviewer that answers well. atime has one-second resolution and this round takes
        # milliseconds, so the fake cannot be measured as having read; the measurement is forced
        # to the shape the live codex round produced on 2026-09-22 instead of faked with sleeps.
        pr.examined_report = lambda before, root: {"read_tracking": "available", "examined": [],
                                                   "examined_count": 0, "offered_count": 11,
                                                   "examined_beyond_the_diff": [],
                                                   "looked_beyond_the_diff": False}
        clean = json.dumps({"verdict": "no_blocking_findings",
                            "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
                            "findings": [], "blocker_resolutions": []})
        # cmd_round picks the reviewer before it runs one, and choose_reviewer refuses when no
        # reviewer CLI is installed. Replacing run_reviewer alone made this test pass only on a
        # machine with codex on PATH and fail as review_unavailable everywhere else, CI included,
        # where the workflow provisions checkout and Python only. Peer review 20260922-160502
        # F1 caught it; reproduced with PATH stripped of the npm global bin before fixing.
        pr.choose_reviewer = lambda builder, forced=None, require_installed=True: ("codex", False)
        pr.run_reviewer = lambda tool, prompt, root, timeout, schema=None: (clean, "gpt-6-astra")
        ns = lambda **k: argparse.Namespace(**k)
        rid = pr.cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=3, timeout=30))["review_id"]
        outcome = pr.cmd_round(ns(review_id=rid, head=[]))
        assert outcome == "examined_nothing", f"got {outcome!r}; a clean verdict over nothing is the defect"
        rec = pr.load(pr.REVIEW_DIR / rid, "round-1.json")
        assert rec["outcome"] == "examined_nothing"
        assert "0 of 11" in rec["error"], rec.get("error")
        assert rec.get("raw"), "the refusal must still record what the reviewer said"
    finally:
        pr.examined_report, pr.run_reviewer = saved_report, saved_run
        pr.choose_reviewer = saved_choose
        pr.REVIEW_DIR = saved_dir


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
