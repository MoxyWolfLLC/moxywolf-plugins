#!/usr/bin/env python3
"""EV-011: an open question is a record with a revision, not a sentence in a finding. Stdlib, offline.

The ledger is written by running unknowns.py as a subprocess, the way a builder runs it; the review
hooks are exercised through peer_review.cmd_open / cmd_round / cmd_release with run_reviewer replaced.
"""
import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_ledger as cl  # noqa: E402
import peer_review as pr  # noqa: E402
import unknowns as un  # noqa: E402

UNK = HERE / "unknowns.py"
LEDGER = HERE / "check_ledger.py"


def repo():
    d = Path(tempfile.mkdtemp(prefix="ev011-")) / "repo"; d.mkdir()
    sh = lambda *c: subprocess.run(["git", "-C", str(d), *c], check=True, capture_output=True, text=True).stdout.strip()
    sh("init", "-q", "-b", "build/x"); sh("config", "user.email", "t@t"); sh("config", "user.name", "t")
    (d / "a.py").write_text("def f(x):\n    return x\n"); sh("add", "."); sh("commit", "-qm", "base"); base = sh("rev-parse", "HEAD")
    (d / "a.py").write_text("def f(x):\n    return x + 1\n"); sh("commit", "-qam", "head"); head = sh("rev-parse", "HEAD")
    return d, base, head


def cli(root, *argv, cwd=None):
    env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(root))
    r = subprocess.run([sys.executable, str(UNK), *argv], cwd=str(cwd or HERE), env=env, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def fixture():
    d, base, head = repo()
    return d, base, head, Path(tempfile.mkdtemp())


def lines(d, root):
    return [json.loads(l) for l in un.path(d, "build/x", root).read_text().splitlines() if l.strip()]


def test_record_then_list():
    d, _, _, root = fixture()
    rc, out, err = cli(root, "record", "--repo", str(d), "--question", "does f handle None?", "--needs", "runtime", "--raised-by", "node check")
    assert rc == 0, err
    uid = out.split()[0]; assert len(uid) == 12
    rc, out, _ = cli(root, "list", "--repo", str(d), "--branch", "build/x")
    assert rc == 0 and uid in out and "1 unknown listed, 1 open" in out, out
    rc, out, _ = cli(root, "list", "--repo", str(d), "--branch", "build/x", "--state", "open")
    assert rc == 1, "an open unknown exits 1 under --state open"
    row = lines(d, root)[0]
    assert (row["revision"], row["state"], row["needs"], row["question"]) == (1, "open", "runtime", "does f handle None?")
    assert row["head"] and row["repo"] == cl.repo_id(d) and row["raised_by"] == "node check"
    rc, _, err = cli(root, "record", "--repo", str(d), "--question", "orphan", "--needs", "human")
    assert rc != 0 and "--raised-by" in err, "a question with nothing raising it was accepted"
    # the same question from the same party is not a second record
    rc, out2, _ = cli(root, "record", "--repo", str(d), "--question", "does f handle None?", "--needs", "runtime", "--raised-by", "node check")
    assert uid in out2 and "not duplicated" in out2 and len(lines(d, root)) == 1
    rc, _, err = cli(root, "record", "--repo", str(d), "--question", "x", "--needs", "guess", "--raised-by", "node check")
    assert rc != 0 and "--needs" in err


def test_an_empty_ledger_lists_zero_and_exits_zero():
    d, _, _, root = fixture()
    rc, out, _ = cli(root, "list", "--repo", str(d), "--branch", "build/x", "--state", "open")
    assert rc == 0 and "0 unknowns listed, 0 open" in out, out


def test_two_writers_at_the_same_revision_produce_exactly_one_mutation():
    """F4 (review 20261013-124809): the read, the revision check and the append are one locked
    transaction, so of two concurrent updates at revision 1 one appends revision 2 and the other
    reads 2 and is refused with the winning line."""
    d, _, _, root = fixture()
    _, out, _ = cli(root, "record", "--repo", str(d), "--question", "q", "--needs", "human", "--raised-by", "node check"); uid = out.split()[0]
    env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(root))
    procs = [subprocess.Popen([sys.executable, str(UNK), "update", "--repo", str(d), "--id", uid, "--revision", "1", "--question", f"writer {i}"],
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(2)]
    results = [(p.wait(), *p.communicate()) for p in procs]
    assert sorted(rc for rc, _, _ in results) == [0, 2], results
    loser = next(err for rc, _, err in results if rc == 2)
    assert loser.startswith("stale_revision:") and "revision 2" in loser and '"revision": 2' in loser, loser
    rows = lines(d, root)
    assert [r["revision"] for r in rows] == [1, 2] and un.current(d, "build/x", root=root)[0]["revision"] == 2


def test_update_at_the_current_revision_is_accepted_and_a_stale_one_writes_nothing():
    d, _, _, root = fixture()
    _, out, _ = cli(root, "record", "--repo", str(d), "--question", "q", "--needs", "repository", "--raised-by", "builder round 0"); uid = out.split()[0]
    rc, out, _ = cli(root, "update", "--repo", str(d), "--id", uid, "--revision", "1", "--question", "q, sharpened")
    assert rc == 0 and json.loads(out)["revision"] == 2 and json.loads(out)["question"] == "q, sharpened"
    before = lines(d, root)
    rc, out, err = cli(root, "update", "--repo", str(d), "--id", uid, "--revision", "1", "--question", "stale")
    assert rc == 2 and err.startswith("stale_revision:") and "revision 2" in err, err
    assert lines(d, root) == before, "a refused update wrote a line"
    rc, _, err = cli(root, "update", "--repo", str(d), "--id", "000000000000", "--revision", "1", "--question", "x")
    assert rc == 2 and err.startswith("stale_revision:")


def test_close_needs_evidence_that_exists_and_carries_enough_authority():
    d, _, _, root = fixture()
    saved_root, pr.REVIEW_DIR = pr.REVIEW_DIR, root
    try:
        _close_cases(d, root)
    finally:
        pr.REVIEW_DIR = saved_root


def _close_cases(d, root):
    _, out, _ = cli(root, "record", "--repo", str(d), "--question", "does the suite pass?", "--needs", "runtime", "--raised-by", "builder round 0"); uid = out.split()[0]
    # a ledger line that passed is runtime authority
    env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(root))
    subprocess.run([sys.executable, str(LEDGER), "run", "--repo", str(d), "--", sys.executable, "-c", "pass"], cwd=str(d), env=env, check=True)
    passed = cl.read(cl.ledger_path(d, "build/x", root))[-1]["id"]
    # an evidence id that does not exist is refused
    rc, _, err = cli(root, "close", "--repo", str(d), "--id", uid, "--revision", "1", "--evidence", "ledger:nope")
    assert rc == 2 and err.startswith("authority_insufficient:") and "does not exist" in err, err
    # weaker authority is refused: a reviewer finding (repository) cannot close a runtime question
    for bare in ("human:", "human:dorian", "human:no-such-review:0"):
        rc, _, err = cli(root, "close", "--repo", str(d), "--id", uid, "--revision", "1", "--evidence", bare)
        assert rc == 2 and "does not exist" in err, (bare, err)
    _, out2, _ = cli(root, "record", "--repo", str(d), "--question", "needs a person", "--needs", "human", "--raised-by", "builder round 0"); uid2 = out2.split()[0]
    rc, _, err = cli(root, "close", "--repo", str(d), "--id", uid2, "--revision", "1", "--evidence", f"ledger:{passed}")
    assert rc == 2 and "needs human" in err and "carries runtime" in err, err
    assert all(r["state"] == "open" for r in un.current(d, "build/x")), "a refused close changed state"
    # matching authority closes it, and the closed record names its evidence
    rc, out, err = cli(root, "close", "--repo", str(d), "--id", uid, "--revision", "1", "--evidence", f"ledger:{passed}")
    assert rc == 0, err
    row = json.loads(out); assert (row["state"], row["revision"], row["closed_authority"]) == ("closed", 2, "runtime")
    rc, _, err = cli(root, "close", "--repo", str(d), "--id", uid, "--revision", "2", "--evidence", f"ledger:{passed}")
    assert rc == 2 and "closed" in err, "closing twice must be refused"
    rc, out, _ = cli(root, "list", "--repo", str(d), "--branch", "build/x", "--state", "open")
    assert rc == 1 and uid2 in out and uid not in out
    rc, out, _ = cli(root, "list", "--repo", str(d), "--branch", "build/x")
    assert rc == 0 and "2 unknowns listed, 1 open" in out
    # a failed ledger line is not evidence of anything
    subprocess.run([sys.executable, str(LEDGER), "run", "--repo", str(d), "--", sys.executable, "-c", "import sys; sys.exit(1)"], cwd=str(d), env=env)
    failed = cl.read(cl.ledger_path(d, "build/x", root))[-1]["id"]
    assert un.evidence_authority(f"ledger:{failed}", d) is None and un.evidence_authority("human:dorian", d) is None
    assert un.evidence_authority("round:none:1:F1", d) is None and un.evidence_authority("ci:none:1", d) is None
    # a person's observation on a release handoff is human evidence; the automatic head check is not
    rel = root / "rev-x"; rel.mkdir()
    (rel / "release.json").write_text(json.dumps({"observations": [
        {"claim": "release head is the reviewed head", "automatic": True},
        {"claim": "I ran the suite on my Mac and read the counts", "command": "python3 run_all_tests.py", "automatic": False}]}))
    assert un.evidence_authority("human:rev-x:1", d) == "human"
    assert un.evidence_authority("human:rev-x:0", d) is None and un.evidence_authority("human:rev-x:2", d) is None
    rc, out, err = cli(root, "close", "--repo", str(d), "--id", uid2, "--revision", "1", "--evidence", "human:rev-x:1")
    assert rc == 0 and json.loads(out)["closed_authority"] == "human", err
    # all closed: list --state open exits 0 and prints zero (F7)
    rc, out, _ = cli(root, "list", "--repo", str(d), "--branch", "build/x", "--state", "open")
    assert rc == 0 and "0 unknowns listed, 0 open" in out, out


def test_the_ledger_lives_under_the_review_root_only():
    d, _, _, _ = fixture()
    env = {k: v for k, v in os.environ.items() if k != "GSTACK_PEER_REVIEW_DIR"}
    r = subprocess.run([sys.executable, str(UNK), "record", "--repo", str(d), "--question", "q", "--needs", "human", "--raised-by", "x"],
                       env=env, capture_output=True, text=True)
    assert r.returncode != 0 and "GSTACK_PEER_REVIEW_DIR" in r.stderr
    assert not list(Path.home().glob(".gstack/**/unknowns")), "no silent home default"


def _packet(d, base, head):
    return {"outcome": "f adds one", "acceptance_criteria": ["f(1) == 2", "f(None) is handled"],
            "repos": [{"path": str(d), "base": base, "head": head}], "changed_behavior": "f returns x+1",
            "exclusions": [], "tests": {"commands": [], "results": "", "environment": "test"},
            "release_owner": "fixture-human",
            "data_use": {"owner": "fixture-human", "classification": "test", "allow_repository": True,
                         "allow_history": True, "allowed_tools": ["codex", "claude"]}}


def _reply(round_no):
    if round_no == 1:
        return json.dumps({"verdict": "blocking_findings",
                           "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"},
                                          {"criterion": "f(None) is handled", "met": False, "evidence": "could not determine: no test exercises None"}],
                           "findings": [{"id": "F1", "severity": "blocking", "file": "a.py", "line": 2, "what": "None is unhandled",
                                         "evidence": "a.py:2, not verified for None", "criterion": "f(None) is handled", "fix": "guard"}],
                           "blocker_resolutions": []})
    return json.dumps({"verdict": "no_blocking_findings",
                       "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"},
                                      {"criterion": "f(None) is handled", "met": True, "evidence": "a.py:3"}],
                       "findings": [], "blocker_resolutions": [{"id": "F1", "resolved": True, "evidence": "a.py:3"}]})


def test_a_round_that_raises_an_unknown_leaves_a_ledger_line_the_next_round_can_read():
    d, base, head = repo(); tmp = Path(tempfile.mkdtemp(prefix="ev011-round-"))
    saved = pr.REVIEW_DIR, pr.examined_report, pr.run_reviewer, pr.choose_reviewer
    try:
        pr.REVIEW_DIR = tmp / "reviews"
        pfile = tmp / "packet.json"; pfile.write_text(json.dumps(_packet(d, base, head)))
        pr.examined_report = lambda before, root: {"read_tracking": "available", "examined": ["changed/0-repo/a.py"],
                                                   "examined_count": 1, "offered_count": 2, "examined_beyond_the_diff": [],
                                                   "looked_beyond_the_diff": False}
        pr.choose_reviewer = lambda builder, forced=None, require_installed=True: ("codex", False)
        rounds = {"n": 0}
        def run(tool, prompt, root, timeout, schema=None, named=()):
            rounds["n"] += 1; return _reply(rounds["n"]), "gpt-6-astra"
        pr.run_reviewer = run
        ns = argparse.Namespace
        with contextlib.redirect_stdout(io.StringIO()):
            st = pr.cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=3, timeout=30)); rid = st["review_id"]
            assert st["unknowns_open"] == 0, "a branch with no ledger is zero, printed as zero"
            assert pr.cmd_round(ns(review_id=rid, head=[])) == "blocking_findings"
        rec1 = pr.load(pr.REVIEW_DIR / rid, "round-1.json")
        assert len(rec1["unknowns_raised"]) == 2, rec1["unknowns_raised"]   # the finding and the unmet criterion
        cur = {u["id"]: u for u in un.current(d, "build/x")}
        assert set(rec1["unknowns_raised"]) == set(cur) and all(u["needs"] == "human" and u["state"] == "open" for u in cur.values())
        assert all(u["raised_by"] == f"{rid} round 1" for u in cur.values())
        st = pr.load(pr.REVIEW_DIR / rid, "state.json"); assert st["unknowns_open"] == 2
        assert un.evidence_authority(f"round:{rid}:1:F1", d) == "repository" and un.evidence_authority(f"round:{rid}:1:F9", d) is None
        # round 2: the surface's first lines carry the count, and the ids are stable
        sh = lambda *c: subprocess.run(["git", "-C", str(d), *c], check=True, capture_output=True, text=True).stdout.strip()
        (d / "a.py").write_text("def f(x):\n    return 0 if x is None else x + 1\n"); sh("commit", "-qam", "fix"); h2 = sh("rev-parse", "HEAD")
        pr.save_map(pr.REVIEW_DIR / rid, "dispositions.json", {"F1": "fixed"})
        with contextlib.redirect_stdout(io.StringIO()):
            assert pr.cmd_round(ns(review_id=rid, head=[f"{d}={h2}"])) == "fixes_verified"
        assert (pr.REVIEW_DIR / rid / "round-2-prompt.txt").exists()
        surf2, _ = pr.build_surface([{"path": str(d), "base": base, "head": h2}], Path(tempfile.mkdtemp()),
                                    unknowns_open=pr.open_unknowns([{"path": str(d)}]))
        text2 = (surf2 / "SURFACE.md").read_text()
        assert all(u in text2 for u in rec1["unknowns_raised"]) and "unknowns open: 2;" in text2.splitlines()[1]
        rec2 = pr.load(pr.REVIEW_DIR / rid, "round-2.json")
        assert rec2["unknowns_raised"] == [] and set(u["id"] for u in un.current(d, "build/x")) == set(rec1["unknowns_raised"])
        # release lists them and does not refuse on them
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                pr.cmd_release(ns(review_id=rid, target="main", coverage_exception="release it, fixture-human",
                                  observation=["None is handled, I read a.py :: git -C " + str(d) + " show HEAD:a.py"]))
            except pr.ReviewError as e:
                assert e.outcome == "awaiting_human_release", e
            else:
                raise AssertionError("release returned instead of handing off")
        rel = pr.load(pr.REVIEW_DIR / rid, "release.json")
        assert {u["id"] for u in rel["unknowns_open"]} == set(rec1["unknowns_raised"]) and rel["outcome"] == "awaiting_human_release"
        # a human closes one at the current revision; the next open count drops to one
        uid = rec1["unknowns_raised"][0]
        rc, out, err = cli(pr.REVIEW_DIR, "close", "--repo", str(d), "--id", uid, "--revision", "1", "--evidence", "human:fixture-human")
        assert rc == 2 and "does not exist" in err, "a bare login closed an unknown"
        rc, out, err = cli(pr.REVIEW_DIR, "close", "--repo", str(d), "--id", uid, "--revision", "1", "--evidence", f"human:{rid}:0")
        assert rc == 2, "the automatic head check is not a person's observation"
        rc, out, err = cli(pr.REVIEW_DIR, "close", "--repo", str(d), "--id", uid, "--revision", "1", "--evidence", f"human:{rid}:1")
        assert rc == 0, err
        assert pr.unknowns_open_count([{"path": str(d)}]) == 1
    finally:
        pr.REVIEW_DIR, pr.examined_report, pr.run_reviewer, pr.choose_reviewer = saved


def test_the_surface_first_lines_show_the_open_count():
    d, base, head = repo()
    surf, _ = pr.build_surface([{"path": str(d), "base": base, "head": head}], Path(tempfile.mkdtemp()),
                               coverage="covered", ledger="none", unknowns_open=[{"id": f"u{i}", "revision": 1, "needs": "human", "question": "q"} for i in range(3)])
    first = (surf / "SURFACE.md").read_text().splitlines()
    assert first[0] == "# What this review can see (coverage: covered, ledger: none)"
    assert first[1] == "unknowns open: 3; embedded instructions reported in the prior round: 0"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
