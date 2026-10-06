#!/usr/bin/env python3
"""GO-010: goal mode in any repository, with no onboarding.

A repository that hasn't been set up for goal mode (no goal workflows, gate CODEOWNERS or rulesets)
still runs a goal. The checks GitHub runs in CI for an onboarded repository run here instead, on the
Release Owner's Mac, in the same containers, with the verdict scripts from THIS moxywolf-plugins
checkout and never from the repository under test. Dorian's approvals of the goal pull request and of
the final pull request are the gates; GitHub enforces nothing extra in such a repository.

  goal_local.py check <repo-dir> <goal-id> <head> [--holdout <file>] [--base <ref>] [--goal-dir <dir>]
      every goal test, then (with --holdout) the holdout, against <head> of <repo-dir>, plus the
      envelope over <base>..<head>. The goal folder is read from <base> (default origin/main), where
      the approved goal PR put it, or from --goal-dir before that PR merges. Prints one JSON object and
      exits 0 only when every goal test, the holdout when given, and the envelope passed; 1 otherwise.
  goal_local.py baseline <repo-dir> <goal-id> --goal-dir <dir>
      the goal tests against <repo-dir>'s origin/main before any work: every invariant must pass and
      every outcome test must fail, or the tests can't show the goal happened. Exit 0 when that holds.
  goal_local.py brief <repo-dir> <goal-id>
      goal_brief.py check on <repo-dir>/goals/<goal-id>/, with that repository's DESIGN.md and CODEOWNERS.
  Exit 2 on bad arguments.

Run it from a moxywolf-plugins checkout. Stdlib plus Docker.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_brief as gb  # noqa: E402
import goal_checks as gc  # noqa: E402
import goal_envelope as ge  # noqa: E402

PLUGINS = Path(__file__).resolve().parents[3]
MEMORY = "4g"   # ponytail: a monorepo typecheck needs more than goal-tests' 1g; raise it here if one OOMs


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def manifests(cand):
    """The files that say what a pnpm workspace installs: every tracked package.json, the lockfile,
    the workspace file and .npmrc. Nothing else reaches the networked install container."""
    names = git(cand, "ls-files", "-z").split("\0")
    keep = [n for n in names if n and (n.endswith("/package.json") or n in
            ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", ".npmrc"))]
    for n in keep:
        if Path(cand, n).is_symlink():
            raise SystemExit(f"refused: {n} in the candidate is a symlink; the install takes regular files only")
    return keep


def pnpm_deps(cand, run=subprocess.run):
    """A pnpm workspace's dependencies, installed hoisted (one flat node_modules, like npm's) from its
    manifests only, scripts off. Workspace packages link to each other through node_modules; those links
    are re-pointed at /tmp/candidate, where goal_checks.writable puts the candidate's copy in the sandbox."""
    deps = Path(tempfile.mkdtemp(prefix="goal-deps-"))
    for n in manifests(cand):
        Path(deps, n).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(cand, n), Path(deps, n), follow_symlinks=False)
    for d in [deps, *[p for p in deps.rglob("*") if p.is_dir()]]:
        os.chmod(d, 0o777)                 # the container runs as uid 65534
    r = run(["docker", "run", "--rm", "--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL",
             "--security-opt", "no-new-privileges", "--user", "65534:65534", "--pids-limit", "512",
             "--memory", MEMORY, "-e", "HOME=/tmp", "-e", "COREPACK_HOME=/tmp/corepack", "-w", "/deps",
             "-v", f"{deps.resolve()}:/deps", gc.IMAGE,
             "corepack", "pnpm", "install", "--frozen-lockfile", "--ignore-scripts",
             "--config.node-linker=hoisted", "--store-dir", "/tmp/store"],
            capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise SystemExit(f"pnpm install failed in the install container: {(r.stderr or r.stdout)[-1500:]}")
    nm = (deps / "node_modules").resolve()
    for link in [p for p in nm.rglob("*") if p.is_symlink()]:
        target = (link.parent / os.readlink(link)).resolve()
        if target.is_relative_to(deps.resolve()) and not target.is_relative_to(nm):
            link.unlink()
            link.symlink_to(Path("/tmp/candidate") / target.relative_to(deps.resolve()))
    return deps


def deps_for(cand):
    lock = Path(cand, "pnpm-lock.yaml")
    if lock.is_symlink():             # review F5: a link, dangling or not, never picks the installer
        raise SystemExit("refused: pnpm-lock.yaml in the candidate is a symlink; the install takes regular files only")
    if lock.is_file():
        return pnpm_deps(cand)
    return gc.install_deps(cand)


def with_memory(cmd):
    i = cmd.index("--memory")
    return cmd[:i + 1] + [MEMORY] + cmd[i + 2:]


CODEOWNERS_AT = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")   # GitHub's own precedence


def codeowners_text(read):
    """The first CODEOWNERS file GitHub would use (review F1), via read(path) -> text or None."""
    return next((t for t in (read(p) for p in CODEOWNERS_AT) if t), "")


def co_rules(text):
    """[(regex, owners)] in file order. Full CODEOWNERS pattern syntax (review F2): * and ** anywhere,
    ?, a pattern with no inner slash matches at any depth, a leading / anchors it, a trailing / means
    everything under that folder, and a file or folder pattern also covers what's inside it."""
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        pat, *owners = line.split()
        anchored = pat.startswith("/") or "/" in pat.strip("/")
        body, folder = pat.strip("/"), pat.endswith("/")
        rx, i = "", 0
        while i < len(body):
            if body.startswith("**/", i):
                rx, i = rx + "(?:.*/)?", i + 3
            elif body.startswith("**", i):
                rx, i = rx + ".*", i + 2
            elif body[i] == "*":
                rx, i = rx + "[^/]*", i + 1
            elif body[i] == "?":
                rx, i = rx + "[^/]", i + 1
            else:
                rx, i = rx + re.escape(body[i]), i + 1
        rx = ("" if anchored else "(?:.*/)?") + rx + ("/.*" if folder else "(?:/.*)?")
        out.append((re.compile("^" + rx + "$"), owners))
    return out


def co_owners(rules, path):
    """The owners of path: the last matching rule wins, and a rule with no owners unowns it."""
    found = []
    for rx, owners in rules:
        if rx.match(path):
            found = owners
    return found


GATED = (".github/", "goals/", "goal-runs/")   # always the gate in local mode, whatever CODEOWNERS says
LOCAL_CODEOWNERS = "".join(f"/{g} @dorianatmoxywolf\n" for g in GATED)


def envelope(repo, gid, head, base, brief_text):
    """Files the goal changed outside its Allowed paths, or on the gate: .github/, goals/ and goal-runs/
    always, plus any path the repository's own CODEOWNERS assigns an owner. One rule for every
    repository (review F2, F7, F8): no attempt to judge whether a CODEOWNERS file already guards the
    gate, so no partial CODEOWNERS can switch the fixed gate off. Local mode has no finalize commit (the
    holdout runs from the Mac and is never committed), so goal_envelope's finalize exception has nothing
    to apply to; its marketplace rule is kept below."""
    rs = co_rules(codeowners_text(lambda p: ge.at(repo, base, p)))
    errors = []
    allowed = [g.strip("`") for g in ge.bullet_lines("Allowed paths", ge.sections(brief_text).get("Allowed paths", ""), errors)]
    if not allowed:
        return errors + ["the brief lists no Allowed paths"], 0
    commits = ge.goal_commits(repo, base, head)
    if any(ge.MARKETPLACE in files for _, files in commits):
        top = lambda ref: (json.loads(ge.at(repo, ref, ge.MARKETPLACE) or "{}") or {}).get("version")
        fork = git(repo, "merge-base", base, head).strip()
        if top(head) != top(fork):
            errors.append(f"the goal changes {ge.MARKETPLACE}'s top-level version ({top(fork)} -> {top(head)}); it moves "
                          f"only in the release bump after the goal merges (GO-004.1)")
    for sha, files in commits:
        for f in files:
            if f.startswith(GATED) or co_owners(rs, f):
                errors.append(f"{sha[:12]} changes {f}, a gate path")
            elif not any(ge.path_in(g, f) for g in allowed):
                errors.append(f"{sha[:12]} changes {f}, outside Allowed paths")
    return errors, len(commits)


def check(repo, gid, head, holdout_file=None, base="origin/main", run=subprocess.run, goal_dir=None):
    """Never raises for an operational failure (review F4): it lands in the JSON as `error`, not passed."""
    try:
        return _check(repo, gid, head, holdout_file, base, run, goal_dir)
    except (SystemExit, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError) as e:
        detail = getattr(e, "stderr", None) or str(e)
        return {"goal": gid, "head": head, "base": base, "tests": {}, "holdout": None, "envelope": None,
                "error": (detail if isinstance(detail, str) else detail.decode(errors="replace"))[-2000:], "passed": False}


def _check(repo, gid, head, holdout_file, base, run, goal_dir):
    out = {"goal": gid, "head": head, "base": base, "tests": {}, "holdout": None, "envelope": None}
    trusted = Path(tempfile.mkdtemp(prefix="goal-trusted-"))
    cand = Path(tempfile.mkdtemp(prefix="goal-cand-"))
    try:
        git(PLUGINS, "worktree", "add", "--detach", str(trusted), "HEAD")
        git(repo, "worktree", "add", "--detach", str(cand), head)
        goal = trusted / "goals" / gid           # the approved folder, from the repository's base
        goal.mkdir(parents=True, exist_ok=True)
        if goal_dir:
            shutil.copytree(goal_dir, goal, dirs_exist_ok=True)
        else:
            archive = subprocess.run(["git", "-C", str(repo), "archive", f"{base}:goals/{gid}"],
                                     capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(goal)], input=archive, check=True)
        if not (goal / "GOAL.md").is_file():
            raise SystemExit(f"goals/{gid}/GOAL.md is not on {base}: approve and merge the goal PR first")
        for d in (trusted, cand):
            os.chmod(d, 0o755)
        deps = deps_for(cand)
        r = run(with_memory(gc.sandbox_cmd(trusted, cand, gid, deps)), capture_output=True, text=True, timeout=3600)
        try:
            out["tests"] = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            out["tests_error"] = (r.stderr or r.stdout)[-2000:]
        errors, n = envelope(repo, gid, head, base, (goal / "GOAL.md").read_text())
        out["envelope"] = {"commits": n, "errors": errors}
        if holdout_file:
            source = Path(holdout_file).expanduser().read_text()
            want = (goal / "holdout.sha256").read_text().strip()
            if want not in {hashlib.sha256(s.encode()).hexdigest() for s in (source, source + "\n", source.rstrip("\n"))}:
                out["holdout"] = {"result": "refused", "detail": "the holdout file doesn't match holdout.sha256"}
            else:
                main_tree, cand_tree = gc.sanitized(trusted), gc.sanitized(cand)
                h = run(with_memory(gc.holdout_cmd(main_tree, cand_tree, deps)), input=source,
                        capture_output=True, text=True, timeout=3600)
                try:
                    out["holdout"] = json.loads(h.stdout.strip().splitlines()[-1])
                except (ValueError, IndexError):
                    out["holdout"] = {"result": "did_not_report", "detail": (h.stderr or h.stdout)[-2000:]}
    finally:
        for d, owner in ((trusted, PLUGINS), (cand, repo)):
            subprocess.run(["git", "-C", str(owner), "worktree", "remove", "--force", str(d)], capture_output=True)
    ok = (bool(out["tests"]) and all(v.get("result") == "passed" for v in out["tests"].values())
          and not (out["envelope"] or {"errors": ["envelope not run"]})["errors"]
          and (holdout_file is None or (out["holdout"] or {}).get("result") == "passed"))
    out["passed"] = ok
    return out


def baseline(repo, gid, goal_dir):
    git(repo, "fetch", "-q", "origin", "main")
    head = git(repo, "rev-parse", "origin/main").strip()
    out = check(repo, gid, head, goal_dir=goal_dir)
    errors = [] if out["tests"] else ["examined no goal tests" + (": " + out.get("tests_error", "") if out.get("tests_error") else "")]
    for t, v in out["tests"].items():
        if v["kind"] == "outcome" and v["result"] != "failed":   # review F1: not_run shows nothing either
            errors.append(f"outcome test {t} is {v['result']} on main, not failed; it can't show the goal happened")
        if v["kind"] == "invariant" and v["result"] != "passed":
            errors.append(f"invariant test {t} is {v['result']} on main; it must hold before and throughout")
    return {"head": head, "tests": out["tests"], "errors": errors}


def main(argv):
    opts = dict(zip(argv[3::2], argv[4::2])) if argv[:1] != ["check"] else dict(zip(argv[4::2], argv[5::2]))
    if argv[:1] == ["brief"] and len(argv) == 3:
        repo = Path(argv[1]).resolve()
        read = lambda p: Path(repo, p).read_text() if Path(repo, p).is_file() else None
        # review F3: no CODEOWNERS means local mode's fixed gate stands in for it
        errors, examined = gb.check(repo / "goals" / argv[2], read("DESIGN.md"), codeowners_text(read) or LOCAL_CODEOWNERS)
        print(f"examined {examined} sections and files in goals/{argv[2]}")
        for e in errors + ([] if examined else ["examined nothing"]):
            print("FAIL:", e)
        return 1 if errors or not examined else 0
    if argv[:1] == ["baseline"] and len(argv) == 5 and set(opts) == {"--goal-dir"}:
        out = baseline(Path(argv[1]).resolve(), argv[2], opts["--goal-dir"])
        print(json.dumps(out, indent=2))
        return 1 if out["errors"] else 0
    if argv[:1] == ["check"] and len(argv) >= 4 and not set(opts) - {"--holdout", "--base", "--goal-dir"}:
        out = check(Path(argv[1]).resolve(), argv[2], argv[3], opts.get("--holdout"), opts.get("--base", "origin/main"),
                    goal_dir=opts.get("--goal-dir"))
        print(json.dumps(out, indent=2))
        return 0 if out["passed"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
