#!/usr/bin/env python3
"""XE-034: a check that failed stays failed until the same check passes. Stdlib, offline.

The ledger is written by running check_ledger.py as a subprocess, the way a builder runs it; the review
gate is exercised through peer_review.cmd_open, the entry point `open` uses.
"""
import contextlib
import hashlib
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


def repo(parent=None):
    d = Path(tempfile.mkdtemp(dir=parent))
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
    # F1, review 20261006-162216: the command string after a combined cluster is checked too.
    for argv in (["bash", "-ec", "false | cat"], ["bash", "-lc", "false | cat"], ["bash", "-o", "posix", "-c", "false | cat"]):
        assert ledger(d, root, *argv) == 2, argv
    # F1, review 20261006-163016: `-o pipefail` on the command line can be undone by `+o pipefail`,
    # so only the script's own prefix counts.
    for argv in (["bash", "-o", "pipefail", "-c", "false | cat"],
                 ["bash", "-o", "pipefail", "+o", "pipefail", "-c", "false | cat"]):
        assert ledger(d, root, *argv) == 2, argv
    assert ledger(d, root, "bash", "-ec", "set -o pipefail; false | cat") == 1


def test_with_no_review_root_it_refuses_to_run():
    d, _, _, _ = fixture()
    env = {k: v for k, v in os.environ.items() if k != "GSTACK_PEER_REVIEW_DIR"}
    r = subprocess.run([sys.executable, LEDGER, "run", "--repo", str(d), "--", "true"],
                       cwd=str(d), env=env, capture_output=True, text=True)
    assert r.returncode != 0 and "GSTACK_PEER_REVIEW_DIR" in r.stderr


def test_a_pass_in_a_repository_with_a_colliding_name_does_not_close_the_failure():
    """F2, review 20261006-163016: acme-tools/api and acme/tools-api file under one directory name."""
    root = Path(tempfile.mkdtemp())
    a, _, _ = repo(); b, _, _ = repo()
    subprocess.run(["git", "-C", str(a), "remote", "add", "origin", "git@github.com:acme-tools/api.git"], check=True)
    subprocess.run(["git", "-C", str(b), "remote", "add", "origin", "git@github.com:acme/tools-api.git"], check=True)
    assert cl.ledger_path(a, "build/x", root) == cl.ledger_path(b, "build/x", root)   # the collision is real
    (a / "FAIL").write_text("")
    assert ledger(a, root, sys.executable, "-c", SUITE) == 1
    assert ledger(b, root, sys.executable, "-c", SUITE) == 0
    assert issues(a, root)[0] == 1 and issues(b, root)[0] == 0
    assert len(cl.issues_for(str(a), root)) == 1 and cl.issues_for(str(b), root) == []


def test_relative_origins_resolve_to_the_repository_they_name():
    """F2, review 20261006-163016 round 2: two checkouts with origin ../upstream name different repos."""
    root = Path(tempfile.mkdtemp())
    a, _, _ = repo(tempfile.mkdtemp()); b, _, _ = repo(tempfile.mkdtemp())   # different parents, so
    for d in (a, b):                                                        # ../upstream differs
        subprocess.run(["git", "-C", str(d), "remote", "add", "origin", "../upstream"], check=True)
    assert cl.repo_id(a) != cl.repo_id(b) and cl.repo_id(a).startswith("local:/")
    (a / "FAIL").write_text("")
    assert ledger(a, root, sys.executable, "-c", SUITE) == 1
    assert ledger(b, root, sys.executable, "-c", SUITE) == 0
    assert issues(a, root)[0] == 1


LEDGER_PY = LEDGER


def run(d, root, code):
    """One ledger run of `python -c code`; returns (exit code, stdout, the run's ledger line)."""
    env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(root))
    r = subprocess.run([sys.executable, LEDGER_PY, "run", "--repo", str(d), "--", sys.executable, "-c", code],
                       cwd=str(d), env=env, capture_output=True, text=True)
    return r.returncode, r.stdout, cl.read(cl.ledger_path(d, "build/x", root))[-1]


def receipt_of(d, root, line):
    return cl.receipts_dir(cl.ledger_path(d, "build/x", root)) / f"{line['id']}.log"


def test_a_run_keeps_a_receipt_whose_hash_is_on_its_line():
    d, _, _, root = fixture()
    rc, out, line = run(d, root, "import sys; print('nice: 2309 elements'); print('warn', file=sys.stderr)")
    assert rc == 0 and out == "nice: 2309 elements\n", out   # still passed through to the console
    data = receipt_of(d, root, line).read_bytes()
    assert b"nice: 2309 elements" in data and b"warn" in data
    assert line["receipt"] == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "truncated": False}



def test_a_long_run_is_truncated_and_says_so():
    d, _, _, root = fixture()
    _, _, line = run(d, root, "print('a' * 50000); print('z' * 50000)")
    data = receipt_of(d, root, line).read_bytes()
    assert line["receipt"]["truncated"] is True and len(data) == line["receipt"]["bytes"] < 70000
    assert data.startswith(b"a" * 1000) and data.rstrip().endswith(b"z" * 1000) and b"bytes omitted" in data
    assert hashlib.sha256(data).hexdigest() == line["receipt"]["sha256"]



def test_a_failing_run_keeps_its_exit_code_and_its_receipt():
    d, _, _, root = fixture()
    rc, _, line = run(d, root, "import sys; print('boom'); sys.exit(4)")
    assert rc == 4 and line["exit_code"] == 4 and b"boom" in receipt_of(d, root, line).read_bytes()



def test_the_receipt_keeps_stdout_and_stderr_in_arrival_order():
    d, _, _, root = fixture()
    code = ("import sys, time\n"
            "for i in range(6):\n"
            "    s = sys.stdout if i % 2 == 0 else sys.stderr\n"
            "    s.write(f'line{i}\\n'); s.flush(); time.sleep(0.05)")
    _, _, line = run(d, root, code)
    got = [l for l in receipt_of(d, root, line).read_text().splitlines() if l.startswith("line")]
    assert got == [f"line{i}" for i in range(6)], got


def test_an_old_line_without_a_receipt_still_reads():
    d, _, _, root = fixture()
    _, _, line = run(d, root, "print('x')")
    p = cl.ledger_path(d, "build/x", root)
    p.write_text(json.dumps({k: v for k, v in line.items() if k != "receipt"}) + "\n")
    assert cl.read(p)[0]["id"] == line["id"] and "receipt" not in cl.read(p)[0]
    assert issues(d, root)[0] == 0


def open_review(d, base, head, root, reason=None, ledger_runs=None):
    pk = {"outcome": "o", "acceptance_criteria": ["the README says y"],
          "repos": [{"path": str(d), "base": base, "head": head}], "changed_behavior": "b",
          "exclusions": [], "tests": {"ledger_runs": ledger_runs} if ledger_runs else {},
          "release_owner": "dorianatmoxywolf"}
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
