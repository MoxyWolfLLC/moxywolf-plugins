#!/usr/bin/env python3
"""XE-006: run this repository's own checks, and report what was examined.

A test job that discovers nothing and exits 0 is the false pass EV-001 forbids, and it is how a gate
dies quietly when files move. So discovery is part of the result: this prints every suite it found
and ran, and fails when it finds none.

ponytail: discovery is a glob for test_*.py plus a grep for --selftest entry points. No pytest, no
config, no plugins -- the suites are stdlib-only and self-running by design. Each runs with cwd set
to its own directory, because they import sibling modules by name.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TIMEOUT = 600


def discover(root):
    """(suites, selftests) -- every runnable check in the repository."""
    suites = sorted(p for p in root.rglob("test_*.py")
                    if "__pycache__" not in p.parts and ".git" not in p.parts)
    selftests = sorted(p for p in root.rglob("*.py")
                       if "__pycache__" not in p.parts and ".git" not in p.parts
                       and not p.name.startswith("test_")
                       and "--selftest" in p.read_text(errors="replace"))
    return suites, selftests


def run(path, args, root):
    r = subprocess.run([sys.executable, path.name] + args, cwd=str(path.parent),
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

    print(f"discovered {len(suites)} test suites and {len(selftests)} selftest entry points "
          f"under {root}")
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

        s, st = discover(ROOT)
        assert s and st, f"the real repository must discover checks, got {len(s)}/{len(st)}"
    print("run_all_tests selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
