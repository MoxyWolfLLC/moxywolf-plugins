#!/usr/bin/env python3
"""XE-016: counting what a review cost never costs the review.

DS-001's round 2 died in reviewer_usage() after codex had answered: a comma-only match reached
int(). The parse is tested on its own, and then through a real cmd_round whose usage parse raises,
because the defect was never the regex alone; it was that bookkeeping could abort the round.
"""
import argparse, json, os, subprocess, tempfile
from pathlib import Path
import peer_review as pr


def test_comma_only_usage_is_not_reported():
    assert pr.reviewer_usage("codex", "", "tokens used: ,") == "not_reported"
    assert pr.reviewer_usage("codex", "tokens used\n,\n", "") == "not_reported"
    assert pr.reviewer_usage("codex", "", "tokens used\n1,234")["total"] == 1234


def test_a_round_survives_a_usage_parse_that_raises():
    tmp = Path(tempfile.mkdtemp(prefix="gstack-xe016-"))
    saved = (pr.REVIEW_DIR, pr.reviewer_usage, pr.choose_reviewer, pr.examined_report, pr._SELFTEST)
    saved_env = os.environ.get("GSTACK_PEER_REVIEW_FAKE_CMD")
    try:
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
        clean = json.dumps({"verdict": "no_blocking_findings",
                            "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
                            "findings": [], "blocker_resolutions": []})
        # The real run_reviewer runs, through the selftest command hook, so the subprocess and the
        # usage call inside it are the production path; only the parser is made to fail.
        pr._SELFTEST = True
        os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = f"echo '{clean}'"
        pr.choose_reviewer = lambda builder, forced=None, require_installed=True: ("codex", False)

        def boom(*a, **k):
            raise ValueError("invalid literal for int() with base 10: ','")
        pr.reviewer_usage = boom
        ns = lambda **k: argparse.Namespace(**k)
        rid = pr.cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=3, timeout=30))["review_id"]
        outcome = pr.cmd_round(ns(review_id=rid, head=[]))
        assert outcome == "no_blocking_findings", f"got {outcome!r}; the usage parse aborted the round"
        rec = pr.load(pr.REVIEW_DIR / rid, "round-1.json")
        assert rec["reviewer_usage"] == "not_reported", rec.get("reviewer_usage")
        assert rec["verdict"] == "no_blocking_findings"
    finally:
        pr.REVIEW_DIR, pr.reviewer_usage, pr.choose_reviewer, pr.examined_report, pr._SELFTEST = saved
        if saved_env is None:
            os.environ.pop("GSTACK_PEER_REVIEW_FAKE_CMD", None)
        else:
            os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = saved_env


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
