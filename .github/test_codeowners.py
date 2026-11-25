"""GA-008: CODEOWNERS keeps the gate under Dorian's review and nothing else.

Fails if a gate path stops being owned, if a gate path no longer exists (a rename would
silently unown it), if a hooks file anywhere is unowned, or if a catch-all comes back.
Reports what it examined; examining nothing is a failure.
"""
import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "@dorianatmoxywolf"
GATE = [
    ".github/CODEOWNERS",
    ".github/workflows/tests.yml",
    ".github/test_codeowners.py",
    "plugins/gstack-execution/package.json",
    "plugins/gstack-execution/package-lock.json",
    "plugins/gstack-execution/scripts/agent_token.py",
    "plugins/gstack-execution/scripts/governance.py",
    "plugins/gstack-execution/scripts/run_all_tests.py",
    "plugins/gstack-execution/scripts/goal_envelope.py",
    "plugins/gstack-execution/scripts/goal_spend.py",
    "plugins/gstack-execution/scripts/goal_checks.py",
    "plugins/gstack-execution/scripts/goal_guard.py",
    "plugins/gstack-execution/scripts/goal_successor.py",
    "goals/README.md",
    "goal-runs/README.md",
]
UNOWNED = ["README.md", "DESIGN.md", "docs/evidence/gate-relaxed-2026-09-30.md"]


def rules(text):
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            pattern, *owners = line.split()
            out.append((pattern, owners))
    return out


def matches(pattern, path):
    # ponytail: the subset of CODEOWNERS syntax this file uses (anchored paths, dir/, one-segment *).
    p = pattern.lstrip("/")
    if p.startswith("**/") and p.endswith("/"):  # a directory with this name at any depth
        return p[3:-1] in path.split("/")[:-1]
    if p.endswith("/"):
        n = p.count("/")
        return path.count("/") >= n and fnmatch.fnmatchcase("/".join(path.split("/")[:n]) + "/", p)
    return fnmatch.fnmatchcase(path, p) and path.count("/") == p.count("/")


def owners(rs, path):
    hit = []
    for pattern, o in rs:  # last match wins, as on GitHub
        if matches(pattern, path):
            hit = o
    return hit


def check(rs, root):
    errors = []
    if any(p in ("*", "/*", "**", "/**") for p, _ in rs):
        errors.append("catch-all rule present: every change would need manual approval again")
    # Tracked files only: node_modules and other untracked trees aren't the repository.
    tracked = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True,
                             text=True, check=True).stdout.splitlines()
    hooks = [p for p in tracked if "hooks" in p.split("/")[:-1]]
    for path in GATE + hooks:
        if not (root / path).exists():
            errors.append(f"gate path missing (renamed?): {path}")
        if OWNER not in owners(rs, path):
            errors.append(f"gate path not owned by {OWNER}: {path}")
    for path in UNOWNED:
        if owners(rs, path):
            errors.append(f"non-gate path is owned, so it needs manual approval: {path}")
    # GO-011.9: a goal and its third successor stay his; the first two successors are held by goal_successor.py
    for path, owned in (("goals/x/GOAL.md", True), ("goals/x--s1/GOAL.md", False), ("goals/x--s2/tests/t.py", False),
                        ("goals/x--s3/GOAL.md", True), ("goals/x--s1x/GOAL.md", True)):
        if (OWNER in owners(rs, path)) != owned:
            errors.append(f"{path} should {'be' if owned else 'not be'} owned by {OWNER} (GO-011.9)")
    return errors, len(GATE) + len(hooks) + len(UNOWNED) + 5


def selftest():
    rs = rules("/.github/ @a\n/plugins/*/hooks/ @a\n**/hooks/ @b\n/x/y.py @a")
    assert owners(rs, ".github/workflows/tests.yml") == ["@a"]
    assert owners(rs, "plugins/p/hooks/h.json") == ["@b"]  # last match wins
    assert owners(rs, "plugins/p/q/hooks/h.json") == ["@b"]  # **/ reaches any depth
    assert owners(rs, "hooks/x.sh") == ["@b"]
    assert owners(rs, "plugins/p/hooks.md") == []  # a file named hooks isn't a hooks directory
    assert owners(rules("/plugins/*/hooks/ @a"), "plugins/p/q/hooks/h.json") == []  # one-segment *
    assert owners(rs, "x/y.py") == ["@a"] and owners(rs, "x/y.pyc") == []
    assert owners(rs, "README.md") == []


if __name__ == "__main__":
    selftest()
    errs, examined = check(rules((ROOT / ".github/CODEOWNERS").read_text()), ROOT)
    print(f"examined {examined} paths")
    if examined == 0:
        errs.append("examined nothing")
    # GA-013.2: CODEOWNERS is generated from the lane table's owned list; a hand edit fails here
    gen = subprocess.run([sys.executable, str(ROOT / "plugins/gstack-execution/scripts/codeowners.py"), "check",
                          "--repo", str(ROOT)], capture_output=True, text=True)
    print(gen.stdout.strip() or gen.stderr.strip())
    if gen.returncode:
        errs.append("CODEOWNERS differs from the lane table's owned list: " + gen.stderr.strip())
    for e in errs:
        print("FAIL:", e)
    sys.exit(1 if errs else 0)
