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


def _mini(t, name, extra=""):
    r = Path(t) / name; r.mkdir(parents=True)
    for c in (["git","init","-q"],["git","config","user.email","t@t"],["git","config","user.name","t"]):
        subprocess.run(c, cwd=r, check=True, capture_output=True)
    (r/"utils.py").write_text(f"VALUE = '{name}'\n")
    (r/"uses.py").write_text("import utils\n" + extra)
    subprocess.run(["git","add","-A"], cwd=r, check=True, capture_output=True)
    subprocess.run(["git","commit","-qm","base"], cwd=r, check=True, capture_output=True)
    base = subprocess.run(["git","rev-parse","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
    (r/"utils.py").write_text(f"VALUE = '{name}-changed'\n")
    subprocess.run(["git","commit","-qam","change"], cwd=r, check=True, capture_output=True)
    head = subprocess.run(["git","rev-parse","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
    return {"path": str(r), "base": base, "head": head}


def test_two_repositories_sharing_a_basename_do_not_collide():
    """F1 and F2 from review 20260917-213250. A bare relative path is not unique across
    repositories: one repo's utils.py masked the other's in the caller scan, and both wrote to the
    same surface directory, so a finding bound to the wrong repository."""
    with tempfile.TemporaryDirectory() as t:
        repos = [_mini(t, "a/proj"), _mini(t, "b/proj")]
        assert Path(repos[0]["path"]).name == Path(repos[1]["path"]).name == "proj"
        root = Path(t)/"root"; root.mkdir()
        surf, st = pr.build_surface(repos, root)
        assert st["changed"] == 2, f"both repos' changed files must survive: {st}"
        assert (surf/"changed"/"0-proj"/"utils.py").exists()
        assert (surf/"changed"/"1-proj"/"utils.py").exists()
        assert (surf/"changed"/"0-proj"/"utils.py").read_text() != (surf/"changed"/"1-proj"/"utils.py").read_text()
        assert st["callers"] == 2, f"each repo's caller must be found, not masked: {st}"

        # and a surface-relative finding must bind to the repository it names
        for i, repo in enumerate(repos):
            got = pr.bind_subjects([{"id": "F1", "file": f"changed/{i}-proj/utils.py", "line": 1}], repos)["F1"]
            assert got["bound"], got
            assert got["repo"] == repo["path"], f"bound to the wrong repository: {got['repo']}"


def test_the_round_no_longer_copies_the_whole_tree_to_disk():
    """F3: snapshot() shipped the tree to disk every round while the item is about not shipping
    the tree."""
    import inspect
    src = inspect.getsource(pr.cmd_round)
    assert "build_surface(" in src
    # snapshot() itself must STAY: task_graph's proof nodes execute code in a disposable checkout,
    # which is a different need from handing a reviewer something to read. Deleting it as dead code
    # broke them, because that check grepped the tests and not the callers.
    assert hasattr(pr, "snapshot"), "snapshot() has a non-review caller and must not be deleted"
    assert "snapshot(packet" not in src, "cmd_round must not build a full worktree any more"


def test_a_symlink_escaping_the_repository_is_refused():
    """snapshot() refused these; the surface copies with read_bytes(), which follows them. Dropping
    the snapshot silently dropped the control."""
    with tempfile.TemporaryDirectory() as t:
        outside = Path(t)/"secret.txt"; outside.write_text("not yours\n")
        repos = repo(t); r = Path(repos[0]["path"])
        (r/"widget.py").unlink(); (r/"widget.py").symlink_to(outside)
        subprocess.run(["git","add","-A"], cwd=r, check=True, capture_output=True)
        subprocess.run(["git","commit","-qm","symlink"], cwd=r, check=True, capture_output=True)
        repos[0]["head"] = subprocess.run(["git","rev-parse","HEAD"],cwd=r,capture_output=True,text=True).stdout.strip()
        root = Path(t)/"root"; root.mkdir()
        try:
            pr.build_surface(repos, root)
            raise AssertionError("a symlink escaping the repository must be refused")
        except pr.ReviewError as e:
            assert e.outcome == "data_use_denied", e.outcome


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
