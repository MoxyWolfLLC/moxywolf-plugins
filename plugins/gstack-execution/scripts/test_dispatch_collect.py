#!/usr/bin/env python3
"""XE-004: a review is dispatched and collected, never blocked on. Stdlib only."""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "peer_review.py"
sys.path.insert(0, str(HERE))
import peer_review as pr  # noqa: E402  XE-022: the reviewer table has one home


def run(args, env, timeout=60):
    r = subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=True, text=True,
                       env=env, timeout=timeout, cwd=str(HERE))
    try:
        return r.returncode, json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return r.returncode, {"_stdout": r.stdout, "_stderr": r.stderr}


def fake_codex(tmp, body, sleep=0):
    """A real executable named `codex` on PATH. Exercises the genuine invocation path -- the
    GSTACK_PEER_REVIEW_FAKE_CMD hook only applies under --selftest, so a test that relied on it
    silently fell through to the real reviewer and 'passed' on review_unavailable."""
    bin_dir = tmp / "bin"; bin_dir.mkdir(parents=True, exist_ok=True)
    f = bin_dir / "codex"
    # XE-015: the loop refuses a round that opened none of the files it was offered, so a stub
    # reviewer that reads nothing is no longer a stand-in for one that reviewed. `read` is a shell
    # builtin, so this needs nothing on PATH, and it genuinely READS: an input redirect alone opens
    # the file without moving atime on APFS, which is what the record measures.
    f.write_text("#!/bin/sh\n"
                 f"{'sleep %d' % sleep if sleep else ':'}\n"
                 "read -r _ < CHANGE.diff || true\n"
                 "echo 'model: gpt-6-astra' >&2\n"
                 f"cat <<'JSONEOF'\n{body}\nJSONEOF\n")
    f.chmod(0o755)
    return bin_dir


def without_reviewers(env):
    """XE-022: a test that means to have no reviewer must not find the caller's. Prepending an empty
    directory to PATH kept the rest, so on a machine with codex installed the real one answered.
    ponytail: drops every PATH entry holding a reviewer CLI, siblings included; if that ever takes
    git with it, the run fails loudly rather than reviewing, and a per-binary shadow dir is the upgrade."""
    clis = [t for t, c in pr.REVIEWERS.items() if c["transport"] == "cli"]
    # Review F1: the round runs from another directory, so a relative entry (or an empty one, which
    # means cwd) is judged here and resolved there. Pin every entry to what it means here first.
    dirs = [os.path.abspath(d or os.curdir) for d in env["PATH"].split(os.pathsep)]
    env["PATH"] = os.pathsep.join(d for d in dirs
                                  if not any(os.access(os.path.join(d, t), os.X_OK) for t in clis))
    env.pop("GSTACK_OPENROUTER_ENV", None)


def assert_no_reviewer(env):
    """XE-022.2: the absence is checked, not assumed, so a test that cannot stage it fails as setup."""
    assert all(os.path.isabs(d) for d in env["PATH"].split(os.pathsep)), f"setup: relative PATH entry in {env['PATH']}"
    for tool in pr.REVIEWER_ORDER:
        if pr.REVIEWERS[tool]["transport"] == "cli":
            assert shutil.which(tool, path=env["PATH"]) is None, f"setup: {tool} still resolves"
        else:
            assert "GSTACK_OPENROUTER_ENV" not in env, f"setup: {tool} can reach its credential"


def fixture(tmp, body=None, sleep=0, bin_dir=None):
    env = {**os.environ, "GSTACK_PEER_REVIEW_DIR": str(tmp)}
    env.pop("GSTACK_PEER_REVIEW_SESSION", None)
    env.pop("GSTACK_REVIEWER", None)
    if bin_dir is not None:
        without_reviewers(env)
    bd = bin_dir if bin_dir is not None else fake_codex(tmp, body, sleep)
    env["PATH"] = f"{bd}:{env['PATH']}"
    repo = tmp / "repo"; repo.mkdir(parents=True)
    for c in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"]):
        subprocess.run(c, cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("one\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True, capture_output=True)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    (repo / "a.txt").write_text("two\n")
    subprocess.run(["git", "commit", "-qam", "head"], cwd=repo, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    pkt = {"outcome": "o", "acceptance_criteria": ["c"], "changed_behavior": "b", "exclusions": [],
           "tests": {"commands": [], "results": "r", "environment": "e"}, "release_owner": "dorianatmoxywolf",
           "prior_findings": [], "repos": [{"path": str(repo), "base": base, "head": head}],
           "data_use": {"owner": "dorianatmoxywolf", "classification": "internal", "allow_repository": True,
                        "allow_history": True, "allowed_tools": ["claude", "codex", "gemini"],
                        "allowed_commands": [], "output_roots": [str(tmp)]}}
    pf = tmp / "packet.json"; pf.write_text(json.dumps(pkt))
    rc, out = run(["open", "--builder", "claude", "--packet", str(pf)], env)
    assert rc == 0, out
    return env, out["review_id"]


CLEAN = json.dumps({"verdict": "no_blocking_findings",
                    "acceptance": [{"criterion": "c", "met": True, "evidence": "e"}],
                    "findings": [], "blocker_resolutions": []})


def test_collect_before_dispatch_says_so():
    with tempfile.TemporaryDirectory() as t:
        env, rid = fixture(Path(t), CLEAN)
        rc, out = run(["collect", rid], env)
        assert out["status"] == "not_dispatched" and rc == 1, out


def test_dispatch_returns_immediately_then_collect_completes():
    """The point of the item: the dispatching call does not block on the reviewer."""
    with tempfile.TemporaryDirectory() as t:
        env, rid = fixture(Path(t), CLEAN, sleep=3)
        t0 = time.time()
        rc, out = run(["dispatch", rid], env)
        elapsed = time.time() - t0
        assert rc == 0 and out["status"] == "dispatched", out
        assert elapsed < 3, f"dispatch blocked for {elapsed:.1f}s; it must return before the reviewer finishes"
        rc, out = run(["collect", rid], env)
        assert out["status"] == "pending", out          # still running, and saying so once
        for _ in range(40):
            rc, out = run(["collect", rid], env)
            if out["status"] != "pending":
                break
            time.sleep(1)
        assert out["status"] == "complete" and out["outcome"] == "no_blocking_findings", out
        assert rc == 0, rc


def test_a_dispatch_whose_process_is_killed_reports_failed_not_pending_forever():
    """Without this, a dispatch killed by OOM or a sleeping machine is indistinguishable from a
    slow one, which is the condition that produced 51 messages of 'not back yet'."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        env, rid = fixture(tmp, CLEAN, sleep=120)
        assert run(["dispatch", rid], env)[0] == 0
        rc, out = run(["collect", rid], env)
        assert out["status"] == "pending", out
        pid = json.loads((tmp / rid / "dispatch.json").read_text())["pid"]
        os.kill(pid, 9)
        for _ in range(20):
            rc, out = run(["collect", rid], env)
            if out["status"] != "pending":
                break
            time.sleep(0.5)
        assert out["status"] == "failed", out
        assert rc == 1 and "log_tail" in out, out


def test_a_reviewer_that_exits_nonzero_completes_the_round_as_unavailable():
    """Distinct from the case above: the process lived and recorded an outcome. Collect reports it
    as complete with a non-pass outcome and a nonzero exit, never as a pass."""
    with tempfile.TemporaryDirectory() as t:
        empty = Path(t) / "emptybin"; empty.mkdir()
        env, rid = fixture(Path(t), bin_dir=empty)
        assert_no_reviewer(env)
        assert run(["dispatch", rid], env)[0] == 0
        for _ in range(30):
            rc, out = run(["collect", rid], env)
            if out["status"] != "pending":
                break
            time.sleep(1)
        assert out["status"] == "complete" and out["outcome"] == "review_unavailable", out
        assert rc == 1, "a non-pass outcome must exit nonzero"


def test_the_unavailable_fixture_hides_an_installed_reviewer():
    """XE-022: CI has no reviewer installed, so the case above cannot show there that the fixture
    hides one. Plant a runnable `codex` behind the caller's PATH, as an install would sit, and
    prove it resolves before the fixture runs and does not after, while git still does."""
    with tempfile.TemporaryDirectory() as t:
        installed = Path(t) / "installed"; installed.mkdir()
        f = installed / "codex"; f.write_text("#!/bin/sh\nexit 0\n"); f.chmod(0o755)
        env = {"PATH": os.environ["PATH"] + os.pathsep + str(installed), "GSTACK_OPENROUTER_ENV": "/x"}
        assert shutil.which("codex", path=env["PATH"]), "setup: the planted reviewer must resolve first"
        without_reviewers(env)
        assert_no_reviewer(env)
        assert str(installed) not in env["PATH"].split(os.pathsep), env["PATH"]
        assert shutil.which("git", path=env["PATH"]), "git must still resolve"


def test_a_relative_path_entry_cannot_carry_a_reviewer_past_the_fixture():
    """Review F1: a relative entry is checked from the test's cwd but resolved from the round's. Plant
    codex under a directory named relatively and as an empty entry, and prove neither survives."""
    with tempfile.TemporaryDirectory() as t:
        installed = Path(t) / "rel"; installed.mkdir()
        f = installed / "codex"; f.write_text("#!/bin/sh\nexit 0\n"); f.chmod(0o755)
        here = os.getcwd()
        try:
            os.chdir(t)
            env = {"PATH": os.pathsep.join(["rel", "", os.environ["PATH"]])}
            without_reviewers(env)
            assert_no_reviewer(env)
            assert str(installed) not in env["PATH"].split(os.pathsep), env["PATH"]
            os.chdir(installed)  # the round's cwd: an empty entry would now mean this directory
            assert shutil.which("codex", path=env["PATH"]) is None, env["PATH"]
        finally:
            os.chdir(here)


def test_dispatch_refuses_a_second_review_in_flight():
    with tempfile.TemporaryDirectory() as t:
        env, rid = fixture(Path(t), CLEAN, sleep=5)
        assert run(["dispatch", rid], env)[0] == 0
        rc, out = run(["dispatch", rid], env)
        assert rc != 0, f"a second dispatch must be refused while one is in flight: {out}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
