#!/usr/bin/env python3
"""XE-006: run this repository's own checks, and report what was examined.

A test job that discovers nothing and exits 0 is the false pass EV-001 forbids, and it is how a gate
dies quietly when files move. So discovery is part of the result: this prints every suite it found
and ran, and fails when it finds none.

ponytail: discovery is a glob for test_*.py plus a grep for --selftest entry points. No pytest, no
config, no plugins -- the suites are stdlib-only and self-running by design. Each runs with cwd set
to its own directory, because they import sibling modules by name.

XE-048: each suite runs without GSTACK_HISTORY_DIR. A suite that isolates itself with a temporary
GSTACK_PEER_REVIEW_DIR would otherwise write its fixtures into the real history folder, because the
history folder wins (MR-006). A suite run on its own, outside this runner, isn't covered: drop the
variable at import, as the MR-006 test modules do, or run it with the variable unset.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TIMEOUT = 600


def goal_test(path, root):
    """A goal's own test (goals/<id>/tests/...). It isn't one of the repository's checks: it runs a
    candidate named by GOAL_CANDIDATE, sealed, and only the goal-tests check runs it (GO-003.5)."""
    rel = path.relative_to(root).parts
    return len(rel) > 1 and rel[0] == "goals"


def discover(root):
    """(suites, selftests) -- every runnable check in the repository."""
    suites = sorted(p for p in root.rglob("test_*.py")
                    if "__pycache__" not in p.parts and ".git" not in p.parts and not goal_test(p, root))
    selftests = sorted(p for p in root.rglob("*.py")
                       if "__pycache__" not in p.parts and ".git" not in p.parts
                       and not p.name.startswith("test_") and not goal_test(p, root)
                       and "--selftest" in p.read_text(errors="replace"))
    return suites, selftests


def run(path, args, root):
    env = {k: v for k, v in os.environ.items() if k != "GSTACK_HISTORY_DIR"}   # XE-048: never the real history
    r = subprocess.run([sys.executable, path.name] + args, cwd=str(path.parent), env=env,
                       capture_output=True, text=True, timeout=TIMEOUT)
    return r.returncode, (r.stdout + r.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--list", action="store_true", help="show what would run, run nothing")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()

    suites, selftests = discover(root)
    jobs = [(p, []) for p in suites] + [(p, ["--selftest"]) for p in selftests]

    goal_tests = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts and goal_test(p, root))
    print(f"discovered {len(suites)} test suites and {len(selftests)} selftest entry points "
          f"under {root}; left {len(goal_tests)} goal test files under goals/ to the goal-tests check")
    for p, args in jobs:
        print(f"  - {p.relative_to(root)}{' --selftest' if args else ''}")
    if a.list:
        return 0

    # XE-006.3: finding nothing is a failure, not a pass
    if not jobs:
        print("\nFAIL: discovered no checks to run. A gate that examines nothing does not pass; "
              "it is broken. Check that test files still match test_*.py under this root.")
        return 1

    print()
    failed = []
    for p, args in jobs:
        label = f"{p.relative_to(root)}{' --selftest' if args else ''}"
        try:
            rc, out = run(p, args, root)
        except subprocess.TimeoutExpired:
            rc, out = 124, f"timed out after {TIMEOUT}s"
        if rc == 0:
            print(f"PASS  {label}")
        else:
            failed.append(label)
            print(f"FAIL  {label}  (rc={rc})")
            print("\n".join(f"      {l}" for l in out.strip().splitlines()[-15:]))

    print(f"\nexamined {len(jobs)} checks: {len(jobs) - len(failed)} passed, {len(failed)} failed")
    for f in failed:
        print(f"  failed: {f}")
    return 1 if failed else 0


def _selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        empty = Path(t)
        assert discover(empty) == ([], []), "empty tree must discover nothing"
        assert main(["--root", str(empty)]) == 1, "zero discovered checks must FAIL, not pass"

        (empty / "test_ok.py").write_text("print('fine')\n")
        assert main(["--root", str(empty)]) == 0
        (empty / "test_bad.py").write_text("import sys; sys.exit(3)\n")
        assert main(["--root", str(empty)]) == 1, "a failing suite must fail the run"

        goal = empty / "goals" / "g1" / "tests"
        goal.mkdir(parents=True)
        (goal / "test_goal.py").write_text("import os, sys; sys.exit(0 if os.environ.get('GOAL_CANDIDATE') else 3)\n")
        assert goal / "test_goal.py" not in discover(empty)[0], "a goal's test is the goal-tests check's, not this runner's"
        (empty / "test_bad.py").unlink()
        assert main(["--root", str(empty)]) == 0, "a goal test that needs a candidate must not fail the repository's run"
        nested = empty / "plugins" / "goals"
        nested.mkdir(parents=True)
        (nested / "test_inner.py").write_text("print('fine')\n")
        assert nested / "test_inner.py" in discover(empty)[0], "only the top-level goals/ folder is left out"

        # XE-048: a suite never sees the real history folder, even when the runner's environment names it
        (empty / "test_history.py").write_text("import os, sys; sys.exit(3 if 'GSTACK_HISTORY_DIR' in os.environ else 0)\n")
        saved = os.environ.get("GSTACK_HISTORY_DIR")
        os.environ["GSTACK_HISTORY_DIR"] = str(empty / "real-history")
        try:
            assert main(["--root", str(empty)]) == 0, "a suite must not see GSTACK_HISTORY_DIR"
        finally:
            if saved is None:
                os.environ.pop("GSTACK_HISTORY_DIR", None)
            else:
                os.environ["GSTACK_HISTORY_DIR"] = saved
        assert not (empty / "real-history").exists()

        s, st = discover(ROOT)
        assert s and st, f"the real repository must discover checks, got {len(s)}/{len(st)}"
    print("run_all_tests selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
