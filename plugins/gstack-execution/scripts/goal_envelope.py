#!/usr/bin/env python3
"""GO-004: a goal run stays inside its envelope, and only a person can stop or undo it.

  goal_envelope.py check <id> --head <sha> [--base <ref>]   GO-004.1: every file a goal-authored
                        commit changes is inside the brief's Allowed paths and outside CODEOWNERS
  goal_envelope.py halted <id> [--base <ref>]               GO-004.3: exit 0 when goals/<id>/HALT
                        is on main (stop), 1 when it isn't
  goal_envelope.py revert <merge sha>                       GO-004.4: the commands that open the
                        revert pull request of a goal's merge commit

The brief and CODEOWNERS are read from main (default origin/main), never from the branch under
check. A goal-authored commit is one on the head that isn't on main, so commits a sync brings in
from main aren't the goal's changes. Merge commits are read as a dense combined diff, so a change
hidden in a merge resolution is still seen. The one CODEOWNERS file a goal may write is its run
record, goal-runs/<id>/RESULT.md, and only in a commit that changes nothing else (GO-003.7).
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal_brief import ROOT, bullet_lines, globs_overlap, sections  # noqa: E402
sys.path.insert(0, str(ROOT / ".github"))
from test_codeowners import owners, rules  # noqa: E402

GOAL_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def at(repo, ref, path):
    r = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def goal_commits(repo, base, head):
    """[(sha, [files])] for each commit on head that isn't on base, merges as dense combined diffs."""
    out = []
    for sha in git(repo, "rev-list", "--reverse", f"{base}..{head}").split():
        files = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--cc", sha).split("\n")
        out.append((sha, [f for f in files if f]))
    return out


def check(repo, goal_id, head, base="origin/main"):
    """(errors, examined commits). Fails closed when the goal isn't on main."""
    if not GOAL_ID.match(goal_id):
        return [f"goal id must be lowercase letters, digits and hyphens, got: {goal_id}"], 0
    brief = at(repo, base, f"goals/{goal_id}/GOAL.md")
    codeowners = at(repo, base, ".github/CODEOWNERS")
    if brief is None:
        return [f"goals/{goal_id}/GOAL.md is not on {base}; only an approved goal has an envelope"], 0
    if not codeowners or not rules(codeowners):
        return [f"CODEOWNERS on {base} has no rules; refusing to judge the envelope without them"], 0
    errors = []
    allowed = [g.strip("`") for g in bullet_lines("Allowed paths", sections(brief).get("Allowed paths", ""), errors)]
    if not allowed:
        return errors + ["the brief on main lists no Allowed paths"], 0
    rs, record = rules(codeowners), f"goal-runs/{goal_id}/RESULT.md"
    commits = goal_commits(repo, base, head)
    for sha, files in commits:
        if files == [record]:
            continue                                       # the finalize commit (GO-003.7)
        for f in files:
            if owners(rs, f):
                errors.append(f"{sha[:12]} changes {f}, a CODEOWNERS path")
            elif not any(globs_overlap(g, f) for g in allowed):
                errors.append(f"{sha[:12]} changes {f}, outside Allowed paths")
    return errors, len(commits)


def halted(repo, goal_id, base="origin/main"):
    return at(repo, base, f"goals/{goal_id}/HALT") is not None


def revert_commands(merge_sha):
    if not re.fullmatch(r"[0-9a-f]{40}", merge_sha):
        raise SystemExit("revert needs the goal's full 40-character merge commit SHA")
    b = f"revert/{merge_sha[:12]}"
    return (f"git fetch origin main && git switch -c {b} origin/main && git revert -m 1 --no-edit {merge_sha}"
            f" && git push origin {b}   # then open the pull request {b} -> main; never reset main")


def main(argv, repo=ROOT):
    opts = dict(zip(argv[2::2], argv[3::2])) if len(argv) > 2 else {}
    base = opts.pop("--base", "origin/main")
    if argv[:1] == ["check"] and len(argv) >= 2 and set(opts) == {"--head"}:
        errors, n = check(repo, argv[1], opts["--head"], base)
        head_on_main = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                                       opts["--head"], base]).returncode == 0
        print(f"examined {n} goal-authored commits on {opts['--head'][:12]} against {base}")
        if n == 0 and not errors:
            if head_on_main:
                print("no goal-authored commits: the head is on main (a sync); passes")
            else:
                errors.append("examined no commits and the head is not on main")
        for e in errors:
            print("FAIL:", e)
        return 1 if errors else 0
    if argv[:1] == ["halted"] and len(argv) >= 2 and not opts:
        stop = halted(repo, argv[1], base)
        print(f"goals/{argv[1]}/HALT {'is' if stop else 'is not'} on {base}")
        return 0 if stop else 1
    if argv[:1] == ["revert"] and len(argv) == 2:
        print(revert_commands(argv[1]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
