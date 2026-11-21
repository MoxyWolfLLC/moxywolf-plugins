#!/usr/bin/env python3
"""GR-003: review_lessons.py capture and preflight. Stdlib, offline, no paid call.
Runs the scripts as subprocesses on temporary folders with synthetic lessons, the way a session runs them."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LESSONS = HERE / "review_lessons.py"
LEDGER = HERE.parents[1] / "project-init" / "scripts" / "mistake_ledger.py"
TODAY = "2026-11-20"
FINDINGS = Path(tempfile.mkdtemp())


def sh(b):
    return hashlib.sha256(b).hexdigest()


def run(script, *args):
    r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def snap(d):
    return {str(p.relative_to(d)): sh(p.read_bytes()) for p in sorted(Path(d).rglob("*")) if p.is_file()}


def scratch():
    """A scratch tree: a lesson file location, a cases folder, two head roots, and files a lesson must never touch."""
    d = Path(tempfile.mkdtemp())
    for name, text in {"old/view.txt": "same view\n", "new/view.txt": "same view\n", "new/evidence.txt": "evidence\n",
                       "skills/some-skill.md": "a skill\n", "council_cases.py": "# store\n", "holdout.py": "# holdout\n",
                       "gate.json": "{}\n", "preflight.json": "{}\n"}.items():
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)
    return d


def finding(d, fid="L-1", **kw):
    f = {"id": fid, "class": "false_premise", "what": "a finding said the view text changed; its bytes were equal",
         "caught_by": "reviewer", "closure": "verified",
         "evidence": [{"path": "evidence.txt", "sha256": sh(b"evidence\n")}],
         "check": {"kind": "same_bytes", "path": "view.txt"}, "revalidate_by": "2027-01-01",
         "retire_when": {"kind": "sha256_is", "path": "view.txt", "sha256": sh(b"superseded view\n")}}
    f.update(kw)
    f = {k: v for k, v in f.items() if v is not None}
    p = FINDINGS / f"{d.name}-{fid}.json"  # outside the scratch tree, so a write check sees only what the scripts wrote
    p.write_text(json.dumps(f))
    return p


def capture(d, fid="L-1", **kw):
    return run(LESSONS, "capture", "--lessons", d / "lessons" / "review-lessons.md", "--cases", d / "lessons" / "cases",
               "--finding", finding(d, fid, **kw), "--date", TODAY)


def preflight(d, claims=None, today=TODAY):
    a = ["preflight", "--lessons", d / "lessons" / "review-lessons.md", "--cases", d / "lessons" / "cases",
         "--root", d / "new", "--old", d / "old", "--today", today]
    if claims is not None:
        (FINDINGS / "claims.json").write_text(json.dumps(claims))
        a += ["--claims", FINDINGS / "claims.json"]
    rc, out, err = run(LESSONS, *a)
    assert rc == 0, err
    return json.loads(out)


def lesson_file(d):
    return d / "lessons" / "review-lessons.md"


def case_file(d, fid="L-1"):
    return d / "lessons" / "cases" / f"{fid}.json"


def test_a_captured_file_is_valid_for_mistake_ledger_unchanged():
    d = scratch()
    rc, out, err = capture(d)
    assert rc == 0, err
    text = lesson_file(d).read_text()
    assert text.splitlines()[0] == "| id | date | what | caught_by | evidence | disposition | target | repeats |"
    assert "| evaluation_case | cases/L-1.json |" in text
    rc, out, _ = run(LEDGER, lesson_file(d))
    assert rc == 0 and "examined 1 row(s), 0 failure(s)" in out, out


def test_a_repeat_carries_repeats_and_a_repeat_marked_one_off_fails():
    d = scratch()
    assert capture(d)[0] == 0
    assert capture(d, "L-2", repeats="L-1")[0] == 0
    rows = lesson_file(d).read_text().splitlines()
    assert rows[-1].rstrip(" |").endswith("| L-1"), rows[-1]
    assert run(LEDGER, lesson_file(d))[0] == 0
    bad = d / "bad.md"
    bad.write_text(lesson_file(d).read_text().replace("| evaluation_case | cases/L-2.json | L-1 |", "| one_off | cases/L-2.json | L-1 |"))
    rc, out, _ = run(LEDGER, bad)
    assert rc == 1 and "cannot be one_off" in out, out


def test_a_repeat_of_an_id_not_in_the_ledger_is_refused_by_the_ledger_rules():
    d = scratch()
    rc, _, err = capture(d, repeats="L-9")
    assert rc == 1 and "repeats L-9, which is not in the ledger" in err, err
    assert not lesson_file(d).exists() and not case_file(d).exists()


def test_a_closed_verified_finding_and_a_verified_false_alarm_are_kept():
    d = scratch()
    assert capture(d, "L-1", closure="verified")[0] == 0
    assert capture(d, "L-2", closure="verified_false_alarm")[0] == 0
    assert json.loads(case_file(d, "L-2").read_text())["disposition"] == "verified"
    assert lesson_file(d).read_text().count("evaluation_case") == 2


def test_an_unresolved_objection_and_a_consensus_with_no_evidence_are_refused_and_named():
    for closure, said in (("unresolved", "unresolved objection"), ("consensus", "consensus with no evidence")):
        d = scratch()
        before = snap(d)
        rc, _, err = capture(d, closure=closure)
        assert rc == 1 and said in err, err
        assert snap(d) == before


def test_a_replay_case_missing_a_field_is_refused():
    for field in ("class", "evidence", "check", "revalidate_by", "retire_when"):
        d = scratch()
        before = snap(d)
        rc, _, err = capture(d, **{field: None})
        assert rc == 1 and field in err, (field, err)
        assert snap(d) == before, field


def test_a_stale_retired_evidence_changed_or_unverified_lesson_is_skipped_with_its_reason():
    d = scratch()
    for fid, kw in (("L-ok", {}), ("L-stale", {"revalidate_by": "2026-11-19"}),
                    ("L-retired", {"retire_when": {"kind": "path_absent", "path": "never-there.txt"}}),
                    ("L-moved", {"evidence": [{"path": "evidence.txt", "sha256": sh(b"other\n")}]}),
                    ("L-unver", {})):
        assert capture(d, fid, **kw)[0] == 0, fid
    c = json.loads(case_file(d, "L-unver").read_text())
    case_file(d, "L-unver").write_text(json.dumps(dict(c, disposition="unverified")))
    rep = preflight(d)
    skipped = {s["id"]: s["reason"] for s in rep["skipped"]}
    assert skipped == {"L-stale": "stale", "L-retired": "retired", "L-moved": "evidence_changed", "L-unver": "unverified"}, skipped
    assert [l["id"] for l in rep["loaded"]] == ["L-ok"]


def test_a_seeded_repeat_of_a_false_premise_with_equal_sha256_is_caught():
    d = scratch()
    assert capture(d)[0] == 0
    rep = preflight(d, [{"id": "F-1", "kind": "text_changed", "path": "view.txt"}])
    assert rep["loaded"][0]["check"]["equal"] is True, rep
    assert rep["claims"] == [{"id": "F-1", "status": "rebutted", "why": "equal sha256 at both heads",
                              "sha256": sh(b"same view\n")}], rep["claims"]
    assert rep["pinned_evidence"] == {"evidence.txt": sh(b"evidence\n")}


def test_two_look_alikes_pass_to_review_one_with_a_real_change_one_with_identical_bytes():
    d = scratch()
    (d / "new" / "real.txt").write_text("changed view\n")
    (d / "old" / "real.txt").write_text("original view\n")
    assert capture(d)[0] == 0
    rep = preflight(d, [{"id": "F-real", "kind": "text_changed", "path": "real.txt"},
                        {"id": "F-called", "kind": "behavior", "path": "view.txt"}])
    by = {c["id"]: c for c in rep["claims"]}
    assert by["F-real"]["status"] == "to_review" and by["F-real"]["old_sha256"] != by["F-real"]["new_sha256"], by
    assert by["F-called"]["status"] == "to_review" and "behavior" in by["F-called"]["why"], by


def test_capture_writes_only_the_lesson_file_and_its_cases_folder_and_preflight_writes_nothing():
    d = scratch()
    before = snap(d)
    assert capture(d)[0] == 0
    changed = {k for k, v in snap(d).items() if before.get(k) != v}
    assert changed == {"lessons/review-lessons.md", "lessons/cases/L-1.json"}, changed
    untouched = {k for k in before if k.startswith("skills/") or k in ("council_cases.py", "holdout.py", "gate.json", "preflight.json")}
    assert all(snap(d)[k] == before[k] for k in untouched)
    mid = snap(d)
    rc, out, _ = run(LESSONS, "preflight", "--lessons", lesson_file(d), "--cases", d / "lessons" / "cases",
                     "--root", d / "new", "--old", d / "old", "--today", TODAY)
    assert rc == 0 and json.loads(out)["loaded"], out
    assert snap(d) == mid


def test_a_check_or_retire_rule_that_could_not_run_is_refused_at_capture():
    bad = [{"check": {"kind": "unsupported", "path": "view.txt"}}, {"check": {"kind": "same_bytes"}},
           {"check": {"kind": "same_bytes", "path": "../view.txt"}},
           {"retire_when": {"kind": "sha256_is", "path": "view.txt"}},
           {"retire_when": {"kind": "path_absent"}}, {"retire_when": {"kind": "nope", "path": "view.txt"}},
           {"evidence": [{"path": "/etc/passwd", "sha256": sh(b"x")}]}]
    for kw in bad:
        d = scratch()
        before = snap(d)
        rc, _, err = capture(d, **kw)
        assert rc == 1 and err.strip(), (kw, err)
        assert snap(d) == before, kw


def test_preflight_without_old_is_refused_and_an_absent_checked_file_is_never_reported_equal():
    d = scratch()
    assert capture(d)[0] == 0
    args = ["preflight", "--lessons", lesson_file(d), "--cases", d / "lessons" / "cases", "--root", d / "new", "--today", TODAY]
    rc, out, err = run(LESSONS, *args)
    assert rc != 0 and not out.strip(), (rc, out, err)
    (d / "old" / "view.txt").unlink()
    (d / "new" / "view.txt").unlink()
    rep = preflight(d, [{"id": "F-gone", "kind": "text_changed", "path": "view.txt"}])
    assert rep["loaded"] == [] and rep["skipped"][0]["reason"].startswith("check_unhashable"), rep
    assert rep["claims"][0]["status"] == "to_review", rep["claims"]


def test_neither_command_writes_bytecode_beside_the_ledger_it_imports():
    root = Path(tempfile.mkdtemp())
    for rel in ("plugins/gstack-execution/scripts/review_lessons.py", "plugins/project-init/scripts/mistake_ledger.py",
                "plugins/gstack-execution/skills/gstack-execution/references/vocabulary.json"):
        src = HERE.parents[1] / Path(rel).relative_to("plugins")
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(src.read_bytes())
    d = scratch()
    env = {k: v for k, v in __import__("os").environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    script = root / "plugins/gstack-execution/scripts/review_lessons.py"
    for a in (["capture", "--lessons", lesson_file(d), "--cases", d / "lessons" / "cases", "--finding", finding(d), "--date", TODAY],
              ["preflight", "--lessons", lesson_file(d), "--cases", d / "lessons" / "cases", "--root", d / "new",
               "--old", d / "old", "--today", TODAY]):
        r = subprocess.run([sys.executable, str(script), *map(str, a)], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
    assert not list(root.rglob("__pycache__")) and not list(root.rglob("*.pyc"))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
