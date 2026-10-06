#!/usr/bin/env python3
"""XE-034: a check that failed stays failed until the same check passes. Stdlib, offline.

The ledger is written by running check_ledger.py as a subprocess, the way a builder runs it; the review
gate is exercised through peer_review.cmd_open, the entry point `open` uses.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_ledger as cl  # noqa: E402
import peer_review as pr  # noqa: E402

LEDGER = os.path.join(HERE, "check_ledger.py")
# A stand-in suite: fails while FAIL exists in the repo, unless asked for one passing case only.
SUITE = "import os,sys; sys.exit(0 if sys.argv[1:] == ['only_a'] else (1 if os.path.exists(os.environ['R'] + '/FAIL') else 0))"


def repo():
    d = Path(tempfile.mkdtemp())
    run = lambda *a: subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True)
    run("init", "-q", "-b", "build/x"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
    (d / "README.md").write_text("x\n"); (d / "sub").mkdir(); (d / "sub" / "k").write_text("k\n")
    run("add", "."); run("commit", "-qm", "base")
    base = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    (d / "README.md").write_text("y\n"); run("commit", "-qam", "change")
    head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    return d, base, head


def ledger(d, root, *argv, cwd=None):
    env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(root), R=str(d))
    return subprocess.run([sys.executable, LEDGER, "run", "--repo", str(d), "--", *argv],
                          cwd=str(cwd or d), env=env, capture_output=True, text=True).returncode


def issues(d, root):
    env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(root))
    r = subprocess.run([sys.executable, LEDGER, "open-issues", "--repo", str(d), "--branch", "build/x"],
                       env=env, capture_output=True, text=True)
    return r.returncode, r.stdout


def fixture():
    d, base, head = repo()
    return d, base, head, Path(tempfile.mkdtemp())


def test_the_command_exit_code_passes_through():
    d, _, _, root = fixture()
    assert ledger(d, root, sys.executable, "-c", "import sys; sys.exit(3)") == 3
    assert ledger(d, root, sys.executable, "-c", "pass") == 0
    runs = cl.read(cl.ledger_path(d, "build/x", root))
    assert [r["exit_code"] for r in runs] == [3, 0] and runs[0]["identity"]["cwd"] == "."


def test_the_same_check_passing_closes_the_failure():
    d, _, _, root = fixture()
    (d / "FAIL").write_text("")
    assert ledger(d, root, sys.executable, "-c", SUITE) == 1
    assert issues(d, root)[0] == 1
    (d / "FAIL").unlink()
    assert ledger(d, root, sys.executable, "-c", SUITE) == 0
    rc, out = issues(d, root)
    assert rc == 0 and out.startswith("0 open issues"), out


def test_a_passing_subset_does_not_close_the_failure():
    d, _, _, root = fixture()
    (d / "FAIL").write_text("")
    assert ledger(d, root, sys.executable, "-c", SUITE) == 1
    assert ledger(d, root, sys.executable, "-c", SUITE, "only_a") == 0
    rc, out = issues(d, root)
    assert rc == 1 and "1 open issue in" in out, out


def test_the_same_argv_in_another_directory_does_not_close_the_failure():
    d, _, _, root = fixture()
    (d / "FAIL").write_text("")
    assert ledger(d, root, sys.executable, "-c", SUITE) == 1
    (d / "FAIL").unlink()
    assert ledger(d, root, sys.executable, "-c", SUITE, cwd=d / "sub") == 0
    assert issues(d, root)[0] == 1


def test_a_piped_shell_script_needs_pipefail():
    d, _, _, root = fixture()
    assert ledger(d, root, "bash", "-c", "false | cat") == 2
    assert not cl.ledger_path(d, "build/x", root).exists()    # refused before anything ran
    assert ledger(d, root, "bash", "-c", "set -o pipefail; false | cat") == 1
    assert ledger(d, root, "bash", "-c", "true") == 0


def test_with_no_review_root_it_refuses_to_run():
    d, _, _, _ = fixture()
    env = {k: v for k, v in os.environ.items() if k != "GSTACK_PEER_REVIEW_DIR"}
    r = subprocess.run([sys.executable, LEDGER, "run", "--repo", str(d), "--", "true"],
                       cwd=str(d), env=env, capture_output=True, text=True)
    assert r.returncode != 0 and "GSTACK_PEER_REVIEW_DIR" in r.stderr


def open_review(d, base, head, root, reason=None):
    pk = {"outcome": "o", "acceptance_criteria": ["the README says y"],
          "repos": [{"path": str(d), "base": base, "head": head}], "changed_behavior": "b",
          "exclusions": [], "tests": {}, "release_owner": "dorianatmoxywolf"}
    f = Path(tempfile.mkdtemp()) / "packet.json"; f.write_text(json.dumps(pk))
    pr.REVIEW_DIR = root
    a = SimpleNamespace(packet=str(f), builder="claude", max_rounds=3, timeout=900, accept_narrow_packet=False,
                        accept_off_repo_criterion=False, accept_open_failure=reason)
    with contextlib.redirect_stdout(io.StringIO()):
        return pr.cmd_open(a)


def test_review_open_is_refused_while_a_failure_is_open():
    d, base, head, root = fixture()
    (d / "FAIL").write_text("")
    ledger(d, root, sys.executable, "-c", SUITE)
    try:
        open_review(d, base, head, root)
    except pr.ReviewError as e:
        assert e.outcome == "open_check_failure" and SUITE[:20] in e.detail, e.detail
    else:
        raise AssertionError("opened with an open failure")


def test_review_opens_with_the_override_and_records_the_reason():
    d, base, head, root = fixture()
    (d / "FAIL").write_text("")
    ledger(d, root, sys.executable, "-c", SUITE)
    st = open_review(d, base, head, root, reason="flaky upstream, Dorian 2026-10-06")
    assert st["ledger_status"] == "overridden"
    assert st["open_failures_overridden"] == "flaky upstream, Dorian 2026-10-06"
    saved = json.loads((root / st["review_id"] / "state.json").read_text())
    assert saved["open_failures_overridden"] == st["open_failures_overridden"]


def test_review_opens_clear_once_the_failure_is_closed():
    d, base, head, root = fixture()
    (d / "FAIL").write_text("")
    ledger(d, root, sys.executable, "-c", SUITE)
    (d / "FAIL").unlink()
    ledger(d, root, sys.executable, "-c", SUITE)
    st = open_review(d, base, head, root)
    assert st["ledger_status"] == "clear" and st["open_failures_overridden"] is None


def test_review_opens_with_no_ledger_and_records_none():
    d, base, head, root = fixture()
    st = open_review(d, base, head, root)
    assert st["ledger_status"] == "none"


def test_the_surface_first_line_shows_the_ledger_status():
    d, base, head, root = fixture()
    surf, _ = pr.build_surface([{"path": str(d), "base": base, "head": head}], Path(tempfile.mkdtemp()),
                               coverage="covered", ledger="none")
    assert (surf / "SURFACE.md").read_text().splitlines()[0] == \
        "# What this review can see (coverage: covered, ledger: none)"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
