#!/usr/bin/env python3
"""XE-034: a check that failed stays failed until the same check passes.

  check_ledger.py run --repo <path> -- <argv...>
      run argv with no shell from the current directory, pass its output through, append one line to
      the branch's ledger and exit with the command's own exit code. A shell `-c` script containing `|`
      is refused (exit 2) unless it starts with `set -o pipefail`: without it the pipeline reports its
      last stage, and the ledger would record a pass the check never earned.
  check_ledger.py open-issues --repo <path> --branch <name>
      every open issue, then a count. Exit 0 with none, 1 otherwise.

A check's identity is its working directory relative to the repository root plus its argument list
exactly as given. A failure opens an issue for that identity; only a later run with the same identity
exiting 0 closes it. A subset of the suite, or the same command elsewhere, never does.

The ledger is `<review_root()>/ledger/<owner>-<repo>/<branch>.jsonl`, under the same declared directory
as the reviews (EV-009), and nowhere else.

The idea is from WXK-AI/jev-opus at 6b6b0f8 (MIT), which tracks failures by fingerprint and clears one
only when the same check passes. No code is copied, and its output-text classifier isn't taken: this
wrapper runs the command itself, so it reads the real exit code.

ponytail: stdlib, one JSONL file per branch, a linear scan. Fine until a branch runs thousands of checks.
"""
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import peer_review as pr  # noqa: E402  one review_root(), not a second convention

SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}


def _git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def repo_key(repo):
    """<owner>-<repo> from origin, or the directory's name when there is no origin."""
    url = _git(repo, "remote", "get-url", "origin")
    if url:
        parts = [p for p in re.split(r"[/:]", re.sub(r"\.git$", "", url.rstrip("/"))) if p]
        if len(parts) >= 2:
            return f"{parts[-2]}-{parts[-1]}"
    return Path(_git(repo, "rev-parse", "--show-toplevel") or repo).name


def branch_of(repo):
    """The checked-out branch, or None on a detached head."""
    b = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return None if b in (None, "HEAD") else b


def ledger_path(repo, branch, root):
    return Path(root) / "ledger" / repo_key(repo) / f"{branch}.jsonl"


def read(path):
    """Every run, in order. A line that isn't JSON stops the read: a ledger we can't read is not clear."""
    runs = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            try:
                runs.append(json.loads(line))
            except ValueError:
                raise SystemExit(f"refused: {path} line {n} is not JSON; the ledger can't be read as clear")
    return runs


def key(identity):
    return json.dumps([identity["cwd"], identity["argv"]])


def open_issues(runs):
    """Failures not yet followed by a pass of the same identity. The first failure stays the opener."""
    opened = {}
    for i, r in enumerate(runs):
        k = key(r["identity"])
        if r["exit_code"] != 0:
            opened.setdefault(k, (i, r))
        else:
            opened.pop(k, None)
    return [dict(identity=r["identity"], id=r["id"], head=r["head"], runs_ago=len(runs) - 1 - i)
            for i, r in sorted(opened.values(), key=lambda t: t[0])]


def issues_for(repo, root):
    """For peer_review open: the open issues of the branch checked out at repo, or None with no ledger."""
    b = branch_of(repo)
    p = ledger_path(repo, b, root) if b else None
    return open_issues(read(p)) if p and p.exists() else None


def unsafe_pipe(argv):
    if Path(argv[0]).name not in SHELLS or "-c" not in argv[1:]:
        return False
    i = argv.index("-c", 1)
    script = argv[i + 1] if i + 1 < len(argv) else ""
    return "|" in script and not script.lstrip().startswith("set -o pipefail")


def cmd_run(repo, argv):
    if not argv:
        return print("refused: nothing to run after --", file=sys.stderr) or 2
    if unsafe_pipe(argv):
        print("refused: a shell -c script with a pipe must start with `set -o pipefail`, or its exit code "
              "is the last stage's", file=sys.stderr)
        return 2
    top = _git(repo, "rev-parse", "--show-toplevel")
    b = branch_of(repo)
    if not top or not b:
        print(f"refused: {repo} is not a git checkout on a branch", file=sys.stderr)
        return 2
    cwd = os.path.relpath(os.path.realpath(os.getcwd()), os.path.realpath(top))
    if cwd == ".." or cwd.startswith(".." + os.sep):
        print(f"refused: the current directory is outside {top}", file=sys.stderr)
        return 2
    path = ledger_path(repo, b, pr.review_root())
    started = time.time()
    try:
        rc = subprocess.run(argv).returncode
    except OSError as e:
        print(f"{argv[0]}: {e}", file=sys.stderr)
        rc = 127
    rc = 128 - rc if rc < 0 else rc   # killed by signal N reads as 128+N, as a shell reports it
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps({"id": uuid.uuid4().hex[:12], "identity": {"cwd": cwd, "argv": argv},
                            "head": _git(repo, "rev-parse", "HEAD"), "exit_code": rc,
                            "started": started, "ended": time.time()}) + "\n")
    return rc


def cmd_open_issues(repo, branch):
    p = ledger_path(repo, branch, pr.review_root())
    issues = open_issues(read(p)) if p.exists() else []
    for i in issues:
        print(f"open  {i['identity']['cwd']}: {' '.join(i['identity']['argv'])}  "
              f"(run {i['id']} at {str(i['head'])[:7]}, {i['runs_ago']} runs ago)")
    print(f"{len(issues)} open issue{'s' if len(issues) != 1 else ''} in {p}")
    return 1 if issues else 0


def main(argv):
    if len(argv) >= 3 and argv[0] == "run" and argv[1] == "--repo":
        rest = argv[3:]
        if rest[:1] != ["--"]:
            return print("usage: check_ledger.py run --repo <path> -- <argv...>", file=sys.stderr) or 2
        return cmd_run(argv[2], rest[1:])
    if len(argv) == 5 and argv[0] == "open-issues" and argv[1] == "--repo" and argv[3] == "--branch":
        return cmd_open_issues(argv[2], argv[4])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
