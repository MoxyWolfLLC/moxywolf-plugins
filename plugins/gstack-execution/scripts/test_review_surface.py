#!/usr/bin/env python3
"""XE-007: the reviewer gets the change and its callers, not the tree."""
import subprocess, tempfile
from pathlib import Path
import peer_review as pr


def repo(t):
    r = Path(t) / "r"; r.mkdir()
    for c in (["git","init","-q"],["git","config","user.email","t@t"],["git","config","user.name","t"]):
        subprocess.run(c, cwd=r, check=True, capture_output=True)
    (r/"widget.py").write_text("def make():\n    return 1\n")
    (r/"caller.py").write_text("import widget\nprint(widget.make())\n")
    (r/"unrelated.py").write_text("x = 1\n")
    for i in range(80):                                   # a crowd, to exercise the cap
        (r/f"noise{i}.py").write_text("y = 2\n")
    subprocess.run(["git","add","-A"], cwd=r, check=True, capture_output=True)
    subprocess.run(["git","commit","-qm","base"], cwd=r, check=True, capture_output=True)
    base = subprocess.run(["git","rev-parse","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
    (r/"widget.py").write_text("def make():\n    return 2\n")
    subprocess.run(["git","commit","-qam","change"], cwd=r, check=True, capture_output=True)
    head = subprocess.run(["git","rev-parse","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
    return [{"path": str(r), "base": base, "head": head}]


def test_the_surface_carries_the_diff_and_the_changed_file():
    with tempfile.TemporaryDirectory() as t:
        repos = repo(t); root = Path(t)/"root"; root.mkdir()
        surf, st = pr.build_surface(repos, root)
        assert (surf/"CHANGE.diff").exists() and "return 2" in (surf/"CHANGE.diff").read_text()
        assert list(surf.rglob("changed/**/widget.py")), "the changed file must be present"
        assert st["changed"] == 1, st


def test_a_caller_of_the_changed_file_comes_with_it():
    """The whole reason this is not just 'ship the changed files': a regression in an untouched
    caller is where the substantive blockers come from."""
    with tempfile.TemporaryDirectory() as t:
        repos = repo(t); root = Path(t)/"root"; root.mkdir()
        surf, st = pr.build_surface(repos, root)
        assert list(surf.rglob("callers/**/caller.py")), "a file referencing widget must be carried"
        assert st["callers"] >= 1, st


def test_the_tree_is_not_shipped():
    with tempfile.TemporaryDirectory() as t:
        repos = repo(t); root = Path(t)/"root"; root.mkdir()
        surf, st = pr.build_surface(repos, root)
        assert not list(surf.rglob("**/noise7.py")), "unrelated files must not be carried"
        assert not list(surf.rglob("**/unrelated.py")), "unrelated files must not be carried"


def test_the_cap_bounds_the_surface_and_reports_what_it_withheld():
    """A bound that silently drops files is the failure this objective exists to remove.
    The many callers must exist in the BASE commit -- adding them alongside the change would make
    them changed files, not callers, which is what the first version of this test got wrong."""
    with tempfile.TemporaryDirectory() as t:
        r = Path(t) / "r"; r.mkdir()
        for c in (["git","init","-q"],["git","config","user.email","t@t"],["git","config","user.name","t"]):
            subprocess.run(c, cwd=r, check=True, capture_output=True)
        (r/"widget.py").write_text("def make():\n    return 1\n")
        for i in range(80):
            (r/f"user{i}.py").write_text("import widget\n")       # callers, present before the change
        subprocess.run(["git","add","-A"], cwd=r, check=True, capture_output=True)
        subprocess.run(["git","commit","-qm","base"], cwd=r, check=True, capture_output=True)
        base = subprocess.run(["git","rev-parse","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
        (r/"widget.py").write_text("def make():\n    return 2\n")  # only the one file changes
        subprocess.run(["git","commit","-qam","change"], cwd=r, check=True, capture_output=True)
        head = subprocess.run(["git","rev-parse","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
        repos = [{"path": str(r), "base": base, "head": head}]

        root = Path(t)/"root"; root.mkdir()
        surf, st = pr.build_surface(repos, root, cap=5)
        assert st["changed"] == 1, st
        assert st["callers"] == 5, st
        assert st["callers_withheld"] == 75, st
        assert "withheld by the 5-file cap: 75" in (surf/"SURFACE.md").read_text()


def test_the_surface_tells_the_reviewer_its_own_limits():
    with tempfile.TemporaryDirectory() as t:
        repos = repo(t); root = Path(t)/"root"; root.mkdir()
        surf, _ = pr.build_surface(repos, root)
        md = (surf/"SURFACE.md").read_text()
        assert "repository tree is NOT here" in md
        assert "do not guess" in md and "separate" in md, "must tell the reviewer how to report a gap"


def test_a_disproof_round_with_no_new_commits_still_carries_the_files_under_review():
    """A blocker disproved rather than fixed advances no commits, so the diff is empty. A surface
    derived only from the diff would hand the reviewer nothing to verify against."""
    with tempfile.TemporaryDirectory() as t:
        repos = repo(t)
        repos[0]["base"] = repos[0]["head"]          # nothing changed between base and head
        root = Path(t)/"root"; root.mkdir()
        surf, st = pr.build_surface(repos, root,
                                    prior_findings=[{"file": "widget.py", "line": 1}])
        assert st["changed"] == 1, st
        assert list(surf.rglob("changed/**/widget.py")), "the file the finding names must be present"
        assert st["from_prior_findings"] == 1, st


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
