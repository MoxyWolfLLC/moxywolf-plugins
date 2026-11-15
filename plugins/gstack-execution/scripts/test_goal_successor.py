"""GO-011.9: goal_successor.py check, run against real git ranges in a throwaway repository."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRIEF = ("## Serves\nFourth objective\n\n## Outcome\nShip the thing.\n\n## Non-goals\n- never touch z.py\n\n"
         "## Allowed paths\n- a.py\n\n## Spend cap\n$5\n\n## Stop conditions\n- HALT on main\n")
NEXT = BRIEF.replace("Ship the thing.\n", "Ship the thing.\n\nSucceeds g: the holdout failed; the plan now says why.\n")


def repo():
    d = Path(tempfile.mkdtemp(prefix="succ-"))
    g = lambda *a: subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True).stdout.strip()
    g("init", "-q", "-b", "main"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (d / "goals/g").mkdir(parents=True); (d / "goals/g/GOAL.md").write_text(BRIEF)
    g("add", "-A"); g("commit", "-qm", "goal g")
    return d, g, g("rev-parse", "HEAD")


def run(d, base, head):
    r = subprocess.run([sys.executable, str(HERE / "goal_successor.py"), "check", "--base", base, "--head", head],
                       cwd=d, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def commit(d, g, files, msg="c"):
    for name, text in files.items():
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)
    g("add", "-A"); g("commit", "-qm", msg)
    return g("rev-parse", "HEAD")


def test_a_successor_that_keeps_the_brief_passes():
    d, g, base = repo()
    head = commit(d, g, {"goals/g--s1/GOAL.md": NEXT, "goals/g--s1/PLAN.md": "1. new plan\n"})
    rc, out = run(d, base, head)
    assert rc == 0 and "examined 1 successor" in out, out


def test_a_range_without_successors_passes_and_says_so():
    d, g, base = repo()
    head = commit(d, g, {"a.py": "x = 1\n"})
    rc, out = run(d, base, head)
    assert rc == 0 and "examined 0 successor" in out, out


def test_a_successor_that_changes_a_kept_section_is_refused():
    d, g, base = repo()
    for old, new, says in (("- never touch z.py", "- never touch y.py", "Non-goals"),
                           ("- a.py", "- a.py\n- b.py", "Allowed paths"),
                           ("$5", "$50", "Spend cap"),
                           ("- HALT on main", "- HALT anywhere", "Stop conditions")):
        g("checkout", "-q", "-B", "w", base)
        head = commit(d, g, {"goals/g--s1/GOAL.md": NEXT.replace(old, new)})
        rc, out = run(d, base, head)
        assert rc == 1 and says in out, (says, out)


def test_an_outcome_that_isnt_the_predecessors_plus_one_succeeds_paragraph_is_refused():
    d, g, base = repo()
    head = commit(d, g, {"goals/g--s1/GOAL.md": NEXT.replace("Ship the thing.", "Ship more things.")})
    rc, out = run(d, base, head)
    assert rc == 1 and "word for word" in out, out


def test_a_successor_folder_never_changes_and_touches_nothing_else():
    d, g, base = repo()
    s1 = commit(d, g, {"goals/g--s1/GOAL.md": NEXT})
    edited = commit(d, g, {"goals/g--s1/PLAN.md": "1. sneaked in later\n"})
    rc, out = run(d, s1, edited)
    assert rc == 1 and "only ever added" in out, out
    g("checkout", "-q", "-B", "x", base)
    head = commit(d, g, {"goals/g--s1/GOAL.md": NEXT, "a.py": "x = 2\n"})
    rc, out = run(d, base, head)
    assert rc == 1 and "outside the folder" in out, out


def test_the_second_successor_compares_with_the_first_and_a_third_matches_nothing():
    d, g, base = repo()
    s1 = commit(d, g, {"goals/g--s1/GOAL.md": NEXT})
    s2_text = NEXT.replace("Succeeds g: the holdout failed; the plan now says why.\n",
                           "Succeeds g: the holdout failed; the plan now says why.\n\nSucceeds g--s1: the review blocked.\n")
    # the Outcome must start with --s1's Outcome, which already carries its Succeeds paragraph
    s2 = commit(d, g, {"goals/g--s2/GOAL.md": s2_text})
    rc, out = run(d, s1, s2)
    assert rc == 0, out
    s3 = commit(d, g, {"goals/g--s3/GOAL.md": s2_text})
    rc, out = run(d, s2, s3)
    assert rc == 0 and "examined 0 successor" in out, out   # --s3 is owned: Dorian's review holds it, not this check


def test_a_successor_without_its_predecessor_on_the_base_is_refused():
    d, g, base = repo()
    head = commit(d, g, {"goals/h--s1/GOAL.md": NEXT})
    rc, out = run(d, base, head)
    assert rc == 1 and "isn't on the base" in out, out


def test_an_unowned_name_that_isnt_a_successor_id_is_refused_not_skipped():   # review 20261115-080201 F1
    d, g, base = repo()
    for name in ("G--s1", "g--s1--s1", "g---s2"):
        g("checkout", "-q", "-B", "w", base)
        head = commit(d, g, {f"goals/{name}/GOAL.md": NEXT})
        rc, out = run(d, base, head)
        assert rc == 1 and "not a successor id" in out, (name, out)


def test_a_successor_cant_add_or_change_a_section_the_brief_doesnt_let_move():   # review F2
    d, g, base = repo()
    for text in (NEXT + "## Release companion\nmarketplace\n", NEXT.replace("## Spend cap", "## Required checkouts\n- x\n\n## Spend cap")):
        g("checkout", "-q", "-B", "w", base)
        head = commit(d, g, {"goals/g--s1/GOAL.md": text})
        rc, out = run(d, base, head)
        assert rc == 1 and "same order" in out, out

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
