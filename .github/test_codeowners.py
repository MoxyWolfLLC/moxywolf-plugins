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
    "plugins/gstack-execution/scripts/peer_review.py",
    "plugins/gstack-execution/scripts/governance.py",
    "plugins/gstack-execution/scripts/packet_coverage.mjs",
    "plugins/gstack-execution/scripts/repo_gates.py",
    "plugins/gstack-execution/scripts/run_all_tests.py",
    "plugins/gstack-execution/scripts/version_bump.py",
    "plugins/gstack-execution/scripts/vocab_check.py",
    "plugins/gstack-execution/scripts/goal_brief.py",
    "plugins/gstack-execution/scripts/goal_envelope.py",
    "plugins/gstack-execution/scripts/goal_spend.py",
    "plugins/gstack-execution/scripts/goal_run.py",
    "plugins/gstack-execution/scripts/goal_checks.py",
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
    return errors, len(GATE) + len(hooks) + len(UNOWNED)


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
    for e in errs:
        print("FAIL:", e)
    sys.exit(1 if errs else 0)
