#!/usr/bin/env python3
"""GR-003: a closed review finding becomes a lesson, and a preflight loads only the lessons that still hold.

A lesson is one row in `review-lessons.md`, which uses the eight columns of mistake_ledger.py exactly
(that script validates it unchanged), plus a replay-case file named by the row's `target`.

  capture   --lessons FILE --cases DIR --finding FILE [--date YYYY-MM-DD]
            Keep a finding that closed with verified evidence (closure `verified` or `verified_false_alarm`).
            An unresolved objection and a consensus are refused and named. Writes the lesson file and one
            replay-case file in DIR, and nothing else.
  preflight --lessons FILE --cases DIR --root DIR --old DIR [--claims FILE] [--today YYYY-MM-DD]
            Load each lesson that is not stale, not retired, still matches its evidence sha256 values and
            is recorded verified; list each skipped lesson with its reason; run each loaded lesson's check
            first. Prints one JSON report to standard output and writes no file.

Finding file (JSON): id, class, what, caught_by, closure, evidence [{path, sha256}], check, revalidate_by,
retire_when, optional repeats. A replay case holds pattern_id, class, evidence, check, revalidate_by,
retire_when and disposition `verified`. `evidence`, `check` and `retire_when` name paths under --root:
  check        {"kind": "same_bytes", "path": P}       sha256 of P under --old and under --root
  retire_when  {"kind": "path_absent", "path": P}      or {"kind": "sha256_is", "path": P, "sha256": H}
`--claims` is a JSON list of {id, kind: "text_changed" | "behavior", path}. Equal hashes rebut only a
"text_changed" claim; a "behavior" claim goes to review whatever the bytes say.

Stdlib only. ponytail: checks compare files under two directory roots (two checked-out heads); a git
rev:path reader is the upgrade if lessons ever need a head that is not checked out.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parents[1] / "project-init" / "scripts" / "mistake_ledger.py"  # sibling plugin, as mistake_ledger's own VOCAB path
CLASSES = ("false_premise", "wording_defect", "behavior_gap")
KEEP = ("verified", "verified_false_alarm")
SHA = re.compile(r"[0-9a-f]{64}")
CASE_FIELDS = ("pattern_id", "class", "evidence", "check", "revalidate_by", "retire_when", "disposition")


class Refused(Exception):
    sys.dont_write_bytecode = True  # importing the ledger must not write a __pycache__ beside it


def ledger():
    sys.dont_write_bytecode = True  # importing the ledger must not write a __pycache__ beside it
    spec = importlib.util.spec_from_file_location("mistake_ledger", LEDGER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_of(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def day(s, what):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        raise Refused(f"{what} {s!r} is not an ISO date")


def rel(p):
    """A non-empty relative path that stays inside its root."""
    return isinstance(p, str) and bool(p) and not Path(p).is_absolute() and ".." not in Path(p).parts


def cell(s):
    return re.sub(r"\s+", " ", str(s).replace("|", "/")).strip()


def build_case(f):
    """The replay case for a finding; refuses a finding that is not a closed, verified, evidenced one."""
    closure = f.get("closure")
    if closure == "unresolved":
        raise Refused(f"{f.get('id')}: an unresolved objection is not a lesson")
    if closure == "consensus":
        raise Refused(f"{f.get('id')}: a consensus with no evidence is not a lesson")
    if closure not in KEEP:
        raise Refused(f"{f.get('id')}: closure {closure!r} is not one of {list(KEEP)}")
    case = {"pattern_id": f.get("id"), "class": f.get("class"), "evidence": f.get("evidence"), "check": f.get("check"),
            "revalidate_by": f.get("revalidate_by"), "retire_when": f.get("retire_when"), "disposition": "verified"}
    missing = [k for k in CASE_FIELDS if not case[k]]
    if missing:
        raise Refused(f"{f.get('id')}: replay case is missing {', '.join(missing)}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", str(case["pattern_id"])):
        raise Refused(f"pattern id {case['pattern_id']!r} must be letters, digits, '.', '_' or '-'")
    if case["class"] not in CLASSES:
        raise Refused(f"{case['pattern_id']}: class {case['class']!r} is not one of {list(CLASSES)}")
    if not isinstance(case["evidence"], list) or not all(
            isinstance(e, dict) and e.get("path") and SHA.fullmatch(str(e.get("sha256"))) for e in case["evidence"]):
        raise Refused(f"{case['pattern_id']}: evidence must be a list of {{path, sha256}} with a 64-hex sha256")
    day(case["revalidate_by"], "revalidate_by")
    pid = case["pattern_id"]
    chk, rule = case["check"], case["retire_when"]
    if not isinstance(chk, dict) or chk.get("kind") != "same_bytes" or not rel(chk.get("path")):
        raise Refused(f"{pid}: check must be {{\"kind\":\"same_bytes\",\"path\":<relative path>}}")
    if not isinstance(rule, dict) or not rel(rule.get("path")) or rule.get("kind") not in ("path_absent", "sha256_is") or (
            rule["kind"] == "sha256_is" and not SHA.fullmatch(str(rule.get("sha256")))):
        raise Refused(f"{pid}: retire_when must be path_absent or sha256_is with a relative path (sha256_is also a 64-hex sha256)")
    if not all(rel(e["path"]) for e in case["evidence"]):
        raise Refused(f"{pid}: evidence paths must be relative and stay inside the tree")
    return case


def capture(lessons, cases, finding, today=None):
    L = ledger()
    f = json.loads(Path(finding).read_text())
    case = build_case(f)
    for k in ("what", "caught_by"):
        if not f.get(k):
            raise Refused(f"{case['pattern_id']}: finding has no {k}")
    lessons, cases = Path(lessons), Path(cases)
    text = lessons.read_text() if lessons.exists() else L.HEADER
    target = f"{cases.name}/{case['pattern_id']}.json"
    row = {"id": case["pattern_id"], "date": today or date.today().isoformat(), "what": cell(f["what"]),
           "caught_by": f["caught_by"], "evidence": cell(", ".join(e["sha256"][:12] for e in case["evidence"])),
           "disposition": "evaluation_case", "target": target, "repeats": cell(f.get("repeats", ""))}
    new = text.rstrip("\n") + "\n| " + " | ".join(row[c] for c in L.COLUMNS) + " |\n"
    failures = L.validate(L.parse(new), L.vocab_ids("caught_by"), L.vocab_ids("mistake_disposition"))
    if failures:
        raise Refused("mistake_ledger.py would refuse the row: " + "; ".join(failures))
    cases.mkdir(parents=True, exist_ok=True)
    (cases / f"{case['pattern_id']}.json").write_text(json.dumps(case, indent=2, sort_keys=True) + "\n")
    lessons.write_text(new)
    return case["pattern_id"], target


def retired(rule, root):
    p = Path(root) / rule["path"]
    if rule.get("kind") == "path_absent":
        return not p.exists()
    if rule.get("kind") == "sha256_is":
        return sha_of(p) == rule.get("sha256")
    raise Refused(f"unknown retire_when kind {rule.get('kind')!r}")


def preflight(lessons, cases, root, old=None, claims=None, today=None):
    L = ledger()
    today = day(today, "--today") if today else date.today()
    if not old:
        raise Refused("preflight needs --old: a same_bytes check and a text_changed claim compare two heads")
    rows = [r for r in L.parse(Path(lessons).read_text()) if r.get("disposition") == "evaluation_case"]
    loaded, skipped, pinned = [], [], {}
    for r in rows:
        try:
            case = json.loads((Path(cases).parent / r["target"]).read_text())
            reason = None
            if case.get("disposition") != "verified":
                reason = "unverified"
            elif day(case["revalidate_by"], "revalidate_by") < today:
                reason = "stale"
            elif retired(case["retire_when"], root):
                reason = "retired"
            elif any(sha_of(Path(root) / e["path"]) != e["sha256"] for e in case["evidence"]):
                reason = "evidence_changed"
        except (OSError, ValueError, KeyError, TypeError, AttributeError, Refused) as e:
            case, reason = None, f"unreadable: {e}"
        if reason:
            skipped.append({"id": r["id"], "reason": reason})
            continue
        c = case["check"]
        a, b = sha_of(Path(old) / c["path"]), sha_of(Path(root) / c["path"])
        if a is None or b is None:
            skipped.append({"id": r["id"], "reason": f"check_unhashable: {c['path']} is absent in {'--old' if a is None else '--root'}"})
            continue
        result = {"kind": "same_bytes", "path": c["path"], "old_sha256": a, "new_sha256": b, "equal": a == b}
        loaded.append({"id": r["id"], "class": case["class"], "check": result})
        pinned.update({e["path"]: e["sha256"] for e in case["evidence"]})
    out = []
    for cl in json.loads(Path(claims).read_text()) if claims else []:
        a, b = sha_of(Path(old) / cl["path"]), sha_of(Path(root) / cl["path"])
        if cl["kind"] == "text_changed" and a is not None and a == b:
            out.append({"id": cl["id"], "status": "rebutted", "why": "equal sha256 at both heads", "sha256": a})
        elif cl["kind"] == "text_changed":
            out.append({"id": cl["id"], "status": "to_review", "old_sha256": a, "new_sha256": b})
        else:
            out.append({"id": cl["id"], "status": "to_review",
                        "why": "a behavior claim; equal bytes do not rebut it, review decides"})
    return {"loaded": loaded, "skipped": skipped, "pinned_evidence": pinned, "claims": out}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    for a in ("--lessons", "--cases", "--finding"):
        c.add_argument(a, required=True)
    c.add_argument("--date")
    p = sub.add_parser("preflight")
    for a in ("--lessons", "--cases", "--root"):
        p.add_argument(a, required=True)
    p.add_argument("--old", required=True); p.add_argument("--claims"); p.add_argument("--today")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "capture":
            i, t = capture(a.lessons, a.cases, a.finding, a.date)
            print(f"review_lessons: kept {i}; target {t}")
        else:
            print(json.dumps(preflight(a.lessons, a.cases, a.root, a.old, a.claims, a.today), indent=2, sort_keys=True))
    except Refused as e:
        print(f"review_lessons refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
