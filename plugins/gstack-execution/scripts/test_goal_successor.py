"""GO-011.9: goal_successor.py check, run against real git ranges in a throwaway repository."""
import json
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

def test_text_before_the_first_section_or_a_second_outcome_paragraph_is_refused():   # review 20261115-085458 F1, F2
    d, g, base = repo()
    for text, says in (("Also build y.py.\n" + NEXT, "before its first section"),
                       (NEXT.replace("says why.\n", "says why.\n \nAlso deliver another feature.\n"), "one paragraph only"),
                       (NEXT.replace("- never touch z.py", "- never touch z.py "), "Non-goals")):
        g("checkout", "-q", "-B", "w", base)
        head = commit(d, g, {"goals/g--s1/GOAL.md": text})
        rc, out = run(d, base, head)
        assert rc == 1 and says in out, (says, out)

def test_a_carriage_return_in_a_kept_section_is_refused_through_git():   # review 20261115-093723 F1
    d, g, base = repo()
    for text in (NEXT.replace("- never touch z.py\n", "- never touch z.py\r\n"), NEXT.replace("- a.py\n", "- a.py\r")):
        g("checkout", "-q", "-B", "w", base)
        (d / "goals/g--s1").mkdir(parents=True, exist_ok=True)
        (d / "goals/g--s1/GOAL.md").write_bytes(text.encode())
        g("add", "-A"); g("commit", "-qm", "c")
        rc, out = run(d, base, g("rev-parse", "HEAD"))
        assert rc == 1 and "line break" in out, out

DEPS = ('{"version": 1, "max_workers": 3, "items": {"1": {"id": "a", "writes": ["a.py"]}, '
        '"2": {"id": "b", "writes": ["b.py"], "start_after": [{"id": "a", "because": "b imports a"}]}}, "order": []}\n')


def deps_case(pred_deps, succ_deps, plan=None):
    d, g, base0 = repo()
    base = commit(d, g, {"goals/g/DEPS.json": pred_deps}) if pred_deps is not None else base0
    files = {"goals/g--s1/GOAL.md": NEXT}
    if succ_deps is not None:
        files["goals/g--s1/DEPS.json"] = succ_deps
        keys = sorted(json.loads(succ_deps)["items"], key=int)   # by default its revised PLAN.md matches its DEPS.json
        files["goals/g--s1/PLAN.md"] = plan if plan is not None else "".join(f"{k}. item {k}\n" for k in keys)
    return run(d, base, commit(d, g, files))


def test_a_successor_deps_copied_unchanged_is_accepted():   # GO-023.8
    rc, out = deps_case(DEPS, DEPS)
    assert rc == 0, out


def test_a_successor_deps_that_changes_max_workers_is_refused():   # GO-023.8
    rc, out = deps_case(DEPS, DEPS.replace('"max_workers": 3', '"max_workers": 30'))
    assert rc == 1 and "byte for byte" in out, out
    added = DEPS.replace('"max_workers": 3', '"max_workers": 30').replace('}}, "order"', '}, "3": {"id": "c", "writes": ["c.py"]}}, "order"')
    rc, out = deps_case(DEPS, added)                        # adding an item doesn't open the rest to change
    assert rc == 1 and "`max_workers` differs" in out, out


def test_a_successor_deps_that_adds_an_items_entry_is_accepted():   # GO-023.8
    added = DEPS.replace('}}, "order": []', '}, "3": {"id": "c", "writes": ["c.py"], "start_after": [{"id": "b", "because": "c reads b"}]}}, '
                         '"order": [["a", "c"]]')
    rc, out = deps_case(DEPS, added)
    assert rc == 0, out
    rc, out = deps_case(DEPS, added.replace('"b.py"]', '"b.py", "z.py"]'))   # a kept item's entry still can't move
    assert rc == 1 and "entry `b` differs" in out, out


def test_a_successor_deps_without_one_on_the_predecessor_is_refused():   # GO-023.8
    rc, out = deps_case(None, DEPS)
    assert rc == 1 and "has none" in out, out
    rc, out = deps_case(None, None)
    assert rc == 0, out
    rc, out = deps_case(DEPS, None)                         # dropping the predecessor's plan is refused too
    assert rc == 1 and "has no DEPS.json" in out, out


def test_a_second_successor_copies_the_first_not_the_root():   # GO-023.8 as amended: immediate predecessor
    d, g, _ = repo()
    root = commit(d, g, {"goals/g/DEPS.json": DEPS})
    s1_deps = DEPS.replace('}}, "order"', '}, "3": {"id": "c", "writes": ["c.py"]}}, "order"')
    s1 = commit(d, g, {"goals/g--s1/GOAL.md": NEXT, "goals/g--s1/PLAN.md": "1. a\n2. b\n3. c\n", "goals/g--s1/DEPS.json": s1_deps})
    s2_text = NEXT.replace("says why.\n", "says why.\n\nSucceeds g--s1: the review blocked.\n")
    s2 = commit(d, g, {"goals/g--s2/GOAL.md": s2_text, "goals/g--s2/PLAN.md": "1. a\n2. b\n3. c\n", "goals/g--s2/DEPS.json": s1_deps})
    rc, out = run(d, s1, s2)
    assert rc == 0, out
    g("checkout", "-q", "-B", "w", s1)
    s2 = commit(d, g, {"goals/g--s2/GOAL.md": s2_text, "goals/g--s2/DEPS.json": DEPS.replace("3", "5")})   # the root's, edited
    rc, out = run(d, s1, s2)
    assert rc == 1 and "g--s1" in out, out


DEPS3 = ('{"version": 1, "items": {"1": {"id": "a", "writes": ["a.py"]}, "2": {"id": "b", "writes": ["b.py"]}, '
         '"3": {"id": "c", "writes": ["c.py"], "start_after": [{"id": "a", "because": "c imports a"}, '
         '{"id": "b", "because": "c reads b"}, {"id": "e", "because": "c wraps e"}]}, '
         '"4": {"id": "e", "writes": ["e.py"]}}, "order": []}\n')
A_, B_, E_ = ('{"id": "a", "because": "c imports a"}', '{"id": "b", "because": "c reads b"}', '{"id": "e", "because": "c wraps e"}')


def without_b(start_after):   # the successor's revised PLAN.md removes item b; c keeps its key
    return (DEPS3.replace('"2": {"id": "b", "writes": ["b.py"]}, ', '').replace('"3":', '"2":').replace('"4":', '"3":')
            .replace(f"[{A_}, {B_}, {E_}]", start_after))


def plus(deps, *ids):   # add items to a successor's plan, numbered after c and e
    extra = "".join(f', "{4 + n}": {{"id": "{i}", "writes": ["{i}.py"]}}' for n, i in enumerate(ids))
    return deps.replace('}}, "order"', '}' + extra + '}, "order"')


D_, F_ = '{"id": "d", "because": "d replaces b"}', '{"id": "f", "because": "unrelated"}'


def test_a_removed_prerequisite_may_be_dropped_or_replaced_once():   # GO-023.8, spec review C1 (2026-11-20)
    rc, out = deps_case(DEPS3, without_b(f"[{A_}, {E_}]"))
    assert rc == 0, out                                     # dropped
    rc, out = deps_case(DEPS3, plus(without_b(f"[{A_}, {D_}, {E_}]"), "d"))
    assert rc == 0, out                                     # replaced in its place, with a because


def test_a_dangling_prerequisite_is_refused_at_approval():   # GO-023.8, spec review C1
    rc, out = deps_case(DEPS3, without_b(f"[{A_}, {B_}, {E_}]"))
    assert rc == 1 and "missing prerequisite b" in out, out  # kept unchanged: refused at approval, not when it starts
    added = DEPS.replace('}}, "order"', '}, "3": {"id": "c", "writes": ["c.py"], "start_after": [{"id": "z", "because": "x"}]}}, "order"')
    rc, out = deps_case(DEPS, added)                        # an added item naming no item of the plan
    assert rc == 1 and "missing prerequisite z" in out, out


def test_a_replacement_needs_a_because_and_a_remaining_new_target():   # GO-023.8, spec review C1
    for bad in ('"d"', '{"id": "d", "because": " "}', '{"id": "d"}', '{"id": "zz", "because": "gone"}',
                '{"id": "c", "because": "itself"}', '{"id": "e", "because": "already a prerequisite"}'):
        rc, out = deps_case(DEPS3, plus(without_b(f"[{A_}, {bad}, {E_}]"), "d"))
        assert rc == 1 and "removed item `b`" in out, (bad, out)


def test_removing_a_prerequisite_doesnt_open_the_rest_of_the_entry():   # GO-023.8, spec review C1
    rc, out = deps_case(DEPS3, plus(without_b(f"[{A_}, {D_}, {F_}, {E_}]"), "d", "f"))
    assert rc == 1, out                                     # two new edges for one removed edge
    rc, out = deps_case(DEPS3, plus(without_b(f"[{A_}, {E_}, {F_}]"), "f"))
    assert rc == 1 and "doesn't authorize" in out, out      # an unrelated edge added
    rc, out = deps_case(DEPS3, without_b(f"[{A_}]"))
    assert rc == 1 and "edge to `e`" in out, out            # a surviving edge dropped
    rc, out = deps_case(DEPS3, without_b(f"[{E_}, {A_}]"))
    assert rc == 1 and "reorders" in out, out               # surviving edges reordered
    rc, out = deps_case(DEPS3, without_b(f'[{A_}, {{"id": "e", "because": "reworded"}}]'))
    assert rc == 1 and "'e'" in out, out                    # a surviving edge's because changed


def test_an_item_kept_in_the_plan_but_dropped_from_deps_is_refused():   # GO-023.8, 2026-11-20
    rc, out = deps_case(DEPS3, without_b(f"[{A_}, {E_}]"), plan="1. a\n2. b\n3. c\n4. e\n")
    assert rc == 1 and "don't match PLAN.md" in out, out    # b is still in the revised PLAN.md
    rc, out = deps_case(DEPS3, without_b(f"[{A_}, {E_}]"), plan="1. a\n2. c\n3. e\n")
    assert rc == 0, out                                     # the revised PLAN.md really removes b
    rc, out = deps_case(DEPS3, without_b(f"[{A_}, {E_}]"), plan="")
    assert rc == 1 and "don't match PLAN.md" in out, out    # a DEPS.json with no PLAN.md items


DEPS3_I = DEPS3.replace('"writes": ["c.py"], ', '"writes": ["c.py"], "integrate_after": ["a", "b"], ')


def test_integrate_after_to_a_removed_item_is_drop_only():   # GO-023.8, 2026-11-20
    succ = lambda ia: without_b(f"[{A_}, {E_}]").replace('"writes": ["c.py"], ', f'"writes": ["c.py"], "integrate_after": {ia}, ')
    rc, out = deps_case(DEPS3_I, succ('["a"]'), plan="1. a\n2. c\n3. e\n")
    assert rc == 0, out                                     # the edge to removed b dropped
    rc, out = deps_case(DEPS3_I, plus(succ('["a", "d"]'), "d"), plan="1. a\n2. c\n3. e\n4. d\n")
    assert rc == 1, out                                     # replaced: refused, integrate_after is drop-only
    rc, out = deps_case(DEPS3_I, succ('[]'), plan="1. a\n2. c\n3. e\n")
    assert rc == 1 and "edge to `a`" in out, out            # an edge to a surviving item dropped
    rc, out = deps_case(DEPS3_I, succ('["a"]'), plan="1. a\n2. b\n3. c\n4. e\n")
    assert rc == 1 and "don't match PLAN.md" in out, out    # b still in the revised PLAN.md: not removed


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
