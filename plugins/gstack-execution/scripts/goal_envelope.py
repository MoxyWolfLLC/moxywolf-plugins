#!/usr/bin/env python3
"""GO-004: a goal run stays inside its envelope, and only a person can stop or undo it.

  goal_envelope.py check <id> --head <sha> [--base <ref>]   GO-004.1: every file a goal-authored
                        commit changes is inside the brief's Allowed paths and outside CODEOWNERS
  goal_envelope.py halted <id> [--base <ref>]               GO-004.3: exit 0 only when main was
                        read and has no goals/<id>/HALT (continue); 1 when it has one, 3 when main
                        can't be read, and a crash's 1: every exit but 0 stops
  goal_envelope.py revert <merge sha> [--repo owner/name]   GO-004.4: the commands that open the
                        revert pull request of a goal's merge commit

The brief and CODEOWNERS are read from main (default origin/main), never from the branch under
check. A goal-authored commit is one on the head that isn't on main, so commits a sync brings in
from main aren't the goal's changes. A merge commit's changes are those that differ from every
parent (a resolution) plus any change a parent brought that the merge didn't keep (a discarded
main change), so neither hides in a merge. Allowed paths are globs; a changed path is always
literal. The one CODEOWNERS file a goal may write is its run record, goal-runs/<id>/RESULT.md,
and only in a commit that changes nothing else (GO-003.7).
"""
import json
import re
import shlex
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal_brief import ROOT, bullet_lines, sections  # noqa: E402
sys.path.insert(0, str(ROOT / ".github"))
from test_codeowners import owners, rules  # noqa: E402

GOAL_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def at(repo, ref, path):
    """The file's text at ref, or None when ref has no such path. A ref that can't be read is an
    error, never an absence: a stop control that can't be read must not read as 'no stop'."""
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                            capture_output=True, text=True).stdout.strip()
    if not commit:
        raise SystemExit(f"cannot read {ref}; fetch main first")
    if not git(repo, "ls-tree", "--name-only", commit, "--", path).strip():
        return None
    return git(repo, "show", f"{commit}:{path}")


def path_in(glob, path):
    """Does the literal path match the glob? Only the glob's segments are patterns; '**' spans
    any number of segments."""
    def go(g, p):
        if not g:
            return not p
        if g[0] == "**":
            return go(g[1:], p) or (bool(p) and go(g, p[1:]))
        return bool(p) and fnmatchcase(p[0], g[0]) and go(g[1:], p[1:])
    return go(glob.strip("/").split("/"), path.split("/"))


def merge_files(repo, sha, parents):
    """Files a merge commit changes on its own: a resolution that differs from every parent, and a
    change one parent brought since the merge base that the merge didn't keep."""
    files = set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--cc", sha).split("\n"))
    mb = git(repo, "merge-base", "--octopus", *parents).strip()
    for p in parents:
        brought = set(git(repo, "diff", "--name-only", mb, p).split("\n"))
        files |= brought & set(git(repo, "diff", "--name-only", p, sha).split("\n"))
    return sorted(f for f in files if f)


def goal_commits(repo, base, head):
    """[(sha, [files])] for each commit on head that isn't on base, merges as dense combined diffs."""
    out = []
    for line in git(repo, "rev-list", "--reverse", "--parents", f"{base}..{head}").splitlines():
        sha, *parents = line.split()
        if len(parents) > 1:
            out.append((sha, merge_files(repo, sha, parents)))
        else:
            files = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha).split("\n")
            out.append((sha, [f for f in files if f]))
    return out


MARKETPLACE = ".claude-plugin/marketplace.json"


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
    if any(MARKETPLACE in files for _, files in commits):
        top = lambda ref: (json.loads(at(repo, ref, MARKETPLACE) or "{}") or {}).get("version")
        fork = git(repo, "merge-base", base, head).strip()
        if top(head) != top(fork):        # main moved since the fork is main's change, not the goal's
            errors.append(f"the goal changes {MARKETPLACE}'s top-level version ({top(fork)} -> {top(head)}); it moves "
                          f"only in the release bump after the goal merges, since main moves the same line (GO-004.1)")
    for sha, files in commits:
        if record in files and set(files) <= {record, f"goal-runs/{goal_id}/holdout.py"}:
            continue                                       # the finalize commit (GO-003.7, GO-002.8)
        for f in files:
            if owners(rs, f):
                errors.append(f"{sha[:12]} changes {f}, a CODEOWNERS path")
            elif not any(path_in(g, f) for g in allowed):
                errors.append(f"{sha[:12]} changes {f}, outside Allowed paths")
    return errors, len(commits)


def halted(repo, goal_id, base="origin/main"):
    return at(repo, base, f"goals/{goal_id}/HALT") is not None


def revert_commands(merge_sha, repo_name="MoxyWolfLLC/moxywolf-plugins"):
    """One shell line, run from the repository root, that opens the revert pull request into main
    as the agent. Never a reset of main."""
    if not re.fullmatch(r"[0-9a-f]{40}", merge_sha):
        raise SystemExit("revert needs the goal's full 40-character merge commit SHA")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo_name):
        raise SystemExit(f"--repo must be owner/name, got: {repo_name}")
    b, tok = f"revert/{merge_sha[:12]}", "python3 plugins/gstack-execution/scripts/agent_token.py"
    pr = json.dumps({"title": f"Revert goal merge {merge_sha[:12]}", "head": b, "base": "main",
                     "body": f"Reverts goal merge commit {merge_sha} through the gated path (GO-004.4)."})
    return (f"git fetch origin main && git switch -c {b} origin/main && git revert -m 1 --no-edit {merge_sha}"
            f" && {tok} exec --repo {repo_name} -- git push origin {b}"
            f" && {tok} api POST /repos/{repo_name}/pulls --repo {repo_name} --data {shlex.quote(pr)}")


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
        try:
            stop = halted(repo, argv[1], base)
        except SystemExit as e:
            print(f"STOP: {e}")
            return 3
        print(f"goals/{argv[1]}/HALT {'is' if stop else 'is not'} on {base}")
        return 1 if stop else 0
    if argv[:1] == ["revert"] and len(argv) >= 2 and set(opts) <= {"--repo"}:
        print(revert_commands(argv[1], opts.get("--repo", "MoxyWolfLLC/moxywolf-plugins")))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
